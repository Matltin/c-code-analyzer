"""Deterministic multi-file project analysis and shared symbol indexing."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from c_analyzer import analyze_source
from c_analyzer.ast import FunctionDecl, FunctionPrototype, StructDecl, VarDecl
from c_analyzer.core import Diagnostic, DiagnosticPhase, Severity
from c_analyzer.semantic import Symbol, SymbolKind, SymbolNamespace
from c_analyzer.project.model import (
    ProjectAnalysis,
    ProjectFile,
    ProjectLocation,
    ProjectReference,
    ProjectSymbol,
    normalize_project_path,
)


class ProjectAnalyzer:
    """Analyze an isolated mapping of relative paths to C source text."""

    def __init__(self, files: Mapping[str, str], *, root: str = ".") -> None:
        normalized: dict[str, str] = {}
        for path, source in files.items():
            normalized_path = normalize_project_path(path)
            if normalized_path in normalized:
                raise ValueError(f"duplicate normalized project path: {normalized_path}")
            normalized[normalized_path] = source
        self._sources = normalized
        self._root = root
        self._next_symbol = 1
        self._symbols: list[ProjectSymbol] = []
        self._by_id: dict[str, ProjectSymbol] = {}
        self._global_keys: dict[tuple[SymbolNamespace, str], ProjectSymbol] = {}
        self._local_to_project: dict[tuple[str, str], str] = {}
        self._diagnostics: list[Diagnostic] = []

    def analyze(self) -> ProjectAnalysis:
        project_files = tuple(
            ProjectFile(
                path=path,
                source=self._sources[path],
                analysis=analyze_source(self._sources[path], path),
            )
            for path in sorted(self._sources)
        )
        for file in project_files:
            self._diagnostics.extend(file.analysis.diagnostics)

        self._collect_builtins(project_files)
        for file in project_files:
            self._collect_global_declarations(file)
        for file in project_files:
            self._collect_remaining_symbols(file)
        for file in project_files:
            self._collect_references(file)

        diagnostics = tuple(
            sorted(
                _deduplicate(self._diagnostics),
                key=lambda item: (
                    item.file,
                    item.span.start.offset,
                    item.phase.value,
                    item.severity.value,
                    item.message,
                ),
            )
        )
        for symbol in self._symbols:
            symbol.declarations.sort(key=_location_key)
            symbol.references.sort(
                key=lambda item: _location_key(item.location)
            )
        return ProjectAnalysis(
            root=self._root,
            files=project_files,
            symbols=tuple(self._symbols),
            diagnostics=diagnostics,
            local_to_project=dict(self._local_to_project),
        )

    def _collect_builtins(self, files: tuple[ProjectFile, ...]) -> None:
        if not files:
            return
        first_model = files[0].analysis.semantic.model
        for symbol in first_model.global_scope.symbols[
            SymbolNamespace.ORDINARY
        ].values():
            if symbol.kind is not SymbolKind.BUILTIN_FUNCTION:
                continue
            project_symbol = self._new_symbol(
                name=symbol.name,
                kind=symbol.kind,
                type_=symbol.type,
                namespace=SymbolNamespace.ORDINARY,
                definition=None,
                signature=symbol.signature,
                scope_id="global",
                is_builtin=True,
            )
            self._global_keys[(SymbolNamespace.ORDINARY, symbol.name)] = project_symbol
        for file in files:
            for symbol in file.analysis.semantic.model.symbols:
                if symbol.kind is SymbolKind.BUILTIN_FUNCTION:
                    project = self._global_keys[
                        (SymbolNamespace.ORDINARY, symbol.name)
                    ]
                    self._local_to_project[(file.path, symbol.id)] = project.id

    def _collect_global_declarations(self, file: ProjectFile) -> None:
        model = file.analysis.semantic.model
        for declaration in file.analysis.parser.ast.declarations:
            if isinstance(declaration, (FunctionDecl, FunctionPrototype)):
                symbol = model.symbol_of(declaration.name)
                if symbol is not None:
                    self._merge_function(file, declaration, symbol)
            elif isinstance(declaration, VarDecl):
                symbol = model.symbol_of(declaration.name)
                if symbol is not None:
                    self._merge_global_value(
                        file,
                        declaration,
                        symbol,
                        SymbolNamespace.ORDINARY,
                    )
            elif isinstance(declaration, StructDecl):
                symbol = model.symbol_of(declaration.name)
                if symbol is not None:
                    self._merge_global_value(
                        file,
                        declaration,
                        symbol,
                        SymbolNamespace.TAG,
                    )

    def _merge_function(
        self,
        file: ProjectFile,
        declaration: FunctionDecl | FunctionPrototype,
        symbol: Symbol,
    ) -> None:
        key = (SymbolNamespace.ORDINARY, symbol.name)
        location = _location(file.path, declaration.name.span)
        existing = self._global_keys.get(key)
        documentation = _documentation_before(file, declaration.span.start.offset)
        if existing is None:
            existing = self._new_symbol(
                name=symbol.name,
                kind=SymbolKind.FUNCTION,
                type_=symbol.type,
                namespace=SymbolNamespace.ORDINARY,
                definition=location if isinstance(declaration, FunctionDecl) else None,
                signature=symbol.signature,
                scope_id="global",
                documentation=documentation,
            )
            self._global_keys[key] = existing
        else:
            if existing.is_builtin:
                if existing.type != symbol.type:
                    self._project_error(
                        declaration.name.span,
                        f"conflicting declaration for built-in '{symbol.name}'",
                    )
            elif existing.kind is not SymbolKind.FUNCTION or existing.type != symbol.type:
                self._project_error(
                    declaration.name.span,
                    f"conflicting project declaration for function '{symbol.name}'",
                )
            elif isinstance(declaration, FunctionDecl):
                if existing.definition is not None:
                    self._project_error(
                        declaration.name.span,
                        f"duplicate project function definition '{symbol.name}'",
                    )
                else:
                    existing.definition = location
                    if documentation is not None:
                        existing.documentation = documentation
        existing.declarations.append(location)
        self._local_to_project[(file.path, symbol.id)] = existing.id

    def _merge_global_value(
        self,
        file: ProjectFile,
        declaration: VarDecl | StructDecl,
        symbol: Symbol,
        namespace: SymbolNamespace,
    ) -> None:
        key = (namespace, symbol.name)
        location = _location(file.path, declaration.name.span)
        existing = self._global_keys.get(key)
        if existing is None:
            existing = self._new_symbol(
                name=symbol.name,
                kind=symbol.kind,
                type_=symbol.type,
                namespace=namespace,
                definition=location,
                signature=symbol.signature,
                scope_id="global",
                documentation=_documentation_before(
                    file,
                    declaration.span.start.offset,
                ),
            )
            self._global_keys[key] = existing
            existing.declarations.append(location)
        else:
            self._project_error(
                declaration.name.span,
                f"duplicate project declaration '{symbol.name}'",
            )
        self._local_to_project[(file.path, symbol.id)] = existing.id

    def _collect_remaining_symbols(self, file: ProjectFile) -> None:
        model = file.analysis.semantic.model
        for symbol in model.symbols:
            key = (file.path, symbol.id)
            if key in self._local_to_project:
                continue
            namespace = _namespace_for_symbol(symbol, model)
            definition = (
                _location(file.path, symbol.definition_span)
                if symbol.definition_span is not None
                else None
            )
            project = self._new_symbol(
                name=symbol.name,
                kind=symbol.kind,
                type_=symbol.type,
                namespace=namespace,
                definition=definition,
                signature=symbol.signature,
                scope_id=f"{file.path}:{symbol.scope_id}",
            )
            if definition is not None:
                project.declarations.append(definition)
            self._local_to_project[key] = project.id

    def _collect_references(self, file: ProjectFile) -> None:
        for symbol in file.analysis.semantic.model.symbols:
            project_id = self._local_to_project.get((file.path, symbol.id))
            if project_id is None:
                continue
            project = self._by_id[project_id]
            for reference in symbol.references:
                project.references.append(
                    ProjectReference(
                        symbol_id=project.id,
                        location=_location(file.path, reference.span),
                        access_kind=reference.access_kind,
                    )
                )

    def _new_symbol(
        self,
        *,
        name: str,
        kind: SymbolKind,
        type_,
        namespace: SymbolNamespace,
        definition: ProjectLocation | None,
        signature: str | None,
        scope_id: str | None,
        is_builtin: bool = False,
        documentation: str | None = None,
    ) -> ProjectSymbol:
        symbol = ProjectSymbol(
            id=f"project-sym-{self._next_symbol:04d}",
            name=name,
            kind=kind,
            type=type_,
            namespace=namespace,
            definition=definition,
            signature=signature,
            scope_id=scope_id,
            is_builtin=is_builtin,
            documentation=documentation,
        )
        self._next_symbol += 1
        self._symbols.append(symbol)
        self._by_id[symbol.id] = symbol
        return symbol

    def _project_error(self, span, message: str) -> None:
        self._diagnostics.append(
            Diagnostic(
                phase=DiagnosticPhase.ANALYSIS,
                severity=Severity.ERROR,
                message=message,
                span=span,
            )
        )


def _namespace_for_symbol(symbol: Symbol, model) -> SymbolNamespace:
    if symbol.kind is SymbolKind.STRUCT:
        return SymbolNamespace.TAG
    if symbol.kind is SymbolKind.FIELD:
        return SymbolNamespace.FIELD
    return SymbolNamespace.ORDINARY


def _location(path: str, span) -> ProjectLocation:
    return ProjectLocation(
        file=path,
        offset=span.start.offset,
        line=span.start.line,
        column=span.start.column,
        length=span.length,
    )


def _location_key(location: ProjectLocation) -> tuple[str, int, int]:
    return (location.file, location.offset, location.length)


def _deduplicate(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    unique: dict[tuple[object, ...], Diagnostic] = {}
    for item in diagnostics:
        key = (
            item.phase,
            item.severity,
            item.message,
            item.file,
            item.span.start.offset,
            item.span.end.offset,
        )
        unique.setdefault(key, item)
    return list(unique.values())


def _documentation_before(file: ProjectFile, declaration_offset: int) -> str | None:
    candidates = [
        token
        for token in file.analysis.lexer.tokens
        if token.kind.value in {"line_comment", "block_comment"}
        and token.span.end.offset <= declaration_offset
        and declaration_offset - token.span.end.offset >= 0
    ]
    if not candidates:
        return None
    token = candidates[-1]
    if file.source[token.span.end.offset : declaration_offset].strip():
        return None
    if token.span.end.line + 1 < file.analysis.lexer.tokens[0].span.start.line:
        return None
    if token.span.end.line + 1 < _line_at(file.source, declaration_offset):
        return None
    text = token.lexeme
    if text.startswith("//"):
        return text[2:].lstrip("/").strip()
    if text.startswith("/*") and text.endswith("*/"):
        body = text[2:-2]
        return " ".join(
            line.strip().lstrip("*").strip()
            for line in body.splitlines()
            if line.strip().lstrip("*").strip()
        )
    return text.strip()


def _line_at(source: str, offset: int) -> int:
    return source[:offset].count("\n") + 1


def analyze_project(
    files: Mapping[str, str],
    *,
    root: str = ".",
) -> ProjectAnalysis:
    return ProjectAnalyzer(files, root=root).analyze()


def load_project_directory(directory: Path) -> ProjectAnalysis:
    root = directory.resolve()
    sources = {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.c"))
        if path.is_file()
    }
    return analyze_project(sources, root=str(directory))
