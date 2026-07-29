"""Scope-aware, offset-based rename planning and atomic application."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import difflib
import os
from pathlib import Path
import re
import tempfile

from c_analyzer.lexer import KEYWORDS
from c_analyzer.project import (
    ProjectAnalysis,
    ProjectLocation,
    analyze_project,
    symbol_at,
)
from c_analyzer.semantic import SymbolKind

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class TextEdit:
    file: str
    start_offset: int
    end_offset: int
    replacement: str


@dataclass(frozen=True, slots=True)
class RenameResult:
    ok: bool
    symbol_id: str | None
    old_name: str | None
    new_name: str
    edits: tuple[TextEdit, ...]
    sources: dict[str, str]
    diff: str
    errors: tuple[str, ...]


def plan_rename(
    project: ProjectAnalysis,
    file: str,
    line: int,
    column: int,
    new_name: str,
) -> RenameResult:
    """Return a pure rename preview; no filesystem writes occur."""
    errors = _validate_identifier(new_name)
    try:
        symbol = symbol_at(project, file, line, column)
    except ValueError as error:
        return _failure(new_name, str(error))
    if symbol is None:
        return _failure(new_name, "no symbol at the requested position")
    if symbol.is_builtin:
        return _failure(new_name, "built-in functions cannot be renamed")
    if new_name == symbol.name:
        return _failure(new_name, "new name is identical to the current name")
    errors.extend(_conflicts(project, symbol, new_name))
    if errors:
        return RenameResult(
            ok=False,
            symbol_id=symbol.id,
            old_name=symbol.name,
            new_name=new_name,
            edits=(),
            sources={item.path: item.source for item in project.files},
            diff="",
            errors=tuple(dict.fromkeys(errors)),
        )

    locations = {
        (location.file, location.offset, location.length): location
        for location in (
            *symbol.declarations,
            *(reference.location for reference in symbol.references),
        )
    }
    edits = tuple(
        TextEdit(
            file=location.file,
            start_offset=location.offset,
            end_offset=location.offset + location.length,
            replacement=new_name,
        )
        for location in sorted(
            locations.values(),
            key=lambda item: (item.file, item.offset),
        )
    )
    old_sources = {item.path: item.source for item in project.files}
    new_sources = _apply_edits(old_sources, edits)
    reanalyzed = analyze_project(new_sources, root=project.root)
    old_errors = {
        (item.file, item.phase, item.severity, item.message)
        for item in project.diagnostics
        if item.severity.value == "error"
    }
    new_errors = {
        (item.file, item.phase, item.severity, item.message)
        for item in reanalyzed.diagnostics
        if item.severity.value == "error"
    }
    if not new_errors.issubset(old_errors):
        return RenameResult(
            ok=False,
            symbol_id=symbol.id,
            old_name=symbol.name,
            new_name=new_name,
            edits=(),
            sources=old_sources,
            diff="",
            errors=("rename would introduce a new semantic or syntax error",),
        )
    return RenameResult(
        ok=True,
        symbol_id=symbol.id,
        old_name=symbol.name,
        new_name=new_name,
        edits=edits,
        sources=new_sources,
        diff=_unified_diff(old_sources, new_sources),
        errors=(),
    )


def atomic_apply(
    project_root: Path,
    result: RenameResult,
    *,
    write_temp: Callable[[Path, str], Path] | None = None,
    replace: Callable[[Path, Path], None] = os.replace,
) -> None:
    """Apply a successful plan through staged files with rollback on failure."""
    if not result.ok:
        raise ValueError("cannot apply an unsuccessful rename plan")
    root = project_root.resolve()
    changed = sorted({edit.file for edit in result.edits})
    staged: dict[str, Path] = {}
    backups: dict[str, Path] = {}
    replaced: list[str] = []
    try:
        for relative in changed:
            target = _safe_target(root, relative)
            staged[relative] = (
                write_temp(target, result.sources[relative])
                if write_temp is not None
                else _stage_text(target, result.sources[relative], ".rename-")
            )
            backups[relative] = _stage_text(
                target,
                target.read_text(encoding="utf-8"),
                ".rename-backup-",
            )
        for relative in changed:
            target = _safe_target(root, relative)
            replace(staged[relative], target)
            replaced.append(relative)
    except Exception:
        for relative in reversed(replaced):
            target = _safe_target(root, relative)
            backup = backups.get(relative)
            if backup is not None and backup.exists():
                os.replace(backup, target)
        raise
    finally:
        for path in (*staged.values(), *backups.values()):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def _validate_identifier(new_name: str) -> list[str]:
    errors: list[str] = []
    if not new_name:
        errors.append("new name must not be empty")
    elif not _IDENTIFIER.fullmatch(new_name):
        errors.append("new name is not a valid C identifier")
    if new_name in KEYWORDS:
        errors.append("new name must not be a C keyword")
    return errors


def _conflicts(project, target, new_name: str) -> list[str]:
    conflicts = []
    for other in project.symbols:
        if other.id == target.id or other.name != new_name:
            continue
        if other.namespace is not target.namespace:
            continue
        same_scope = other.scope_id == target.scope_id
        target_is_global = target.scope_id == "global"
        other_is_global = other.scope_id == "global"
        same_file = bool(_symbol_files(other) & _symbol_files(target))
        if same_scope or (target_is_global and other_is_global):
            conflicts.append(
                f"name '{new_name}' already exists in the same namespace and scope"
            )
        elif (
            target.namespace.value == "ordinary"
            and same_file
            and not (target_is_global and other_is_global)
        ):
            conflicts.append(
                f"name '{new_name}' could capture or shadow another local symbol"
            )
    return conflicts


def _symbol_files(symbol) -> set[str]:
    files = {location.file for location in symbol.declarations}
    files.update(reference.location.file for reference in symbol.references)
    if symbol.definition is not None:
        files.add(symbol.definition.file)
    return files


def _apply_edits(
    sources: dict[str, str],
    edits: tuple[TextEdit, ...],
) -> dict[str, str]:
    updated = dict(sources)
    by_file: dict[str, list[TextEdit]] = {}
    for edit in edits:
        by_file.setdefault(edit.file, []).append(edit)
    for file, file_edits in by_file.items():
        source = updated[file]
        for edit in sorted(
            file_edits,
            key=lambda item: item.start_offset,
            reverse=True,
        ):
            source = (
                source[: edit.start_offset]
                + edit.replacement
                + source[edit.end_offset :]
            )
        updated[file] = source
    return updated


def _unified_diff(old: dict[str, str], new: dict[str, str]) -> str:
    lines: list[str] = []
    for file in sorted(old):
        if old[file] == new[file]:
            continue
        lines.extend(
            difflib.unified_diff(
                old[file].splitlines(keepends=True),
                new[file].splitlines(keepends=True),
                fromfile=f"a/{file}",
                tofile=f"b/{file}",
            )
        )
    return "".join(lines)


def _safe_target(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"path escapes project root: {relative}")
    return target


def _stage_text(target: Path, text: str, prefix: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(
        prefix=prefix,
        dir=target.parent,
        text=True,
    )
    path = Path(raw_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def _failure(new_name: str, error: str) -> RenameResult:
    return RenameResult(
        ok=False,
        symbol_id=None,
        old_name=None,
        new_name=new_name,
        edits=(),
        sources={},
        diff="",
        errors=(error,),
    )
