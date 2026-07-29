"""Project-aware go-to-definition, references, and hover."""

from __future__ import annotations

from c_analyzer.project.model import (
    DefinitionResult,
    ProjectAnalysis,
    ProjectHover,
    ProjectReference,
    ProjectSymbol,
    normalize_project_path,
)
from c_analyzer.semantic import position_from_line_column


def symbol_at(
    project: ProjectAnalysis,
    file: str,
    line: int,
    column: int,
) -> ProjectSymbol | None:
    path = normalize_project_path(file)
    project_file = project.file(path)
    if project_file is None:
        raise ValueError(f"file is not part of project: {path}")
    position = position_from_line_column(
        project_file.source,
        path,
        line,
        column,
    )
    local_symbol = _local_symbol_at(
        project_file.analysis.semantic.model.symbols,
        position.offset,
    )
    if local_symbol is None and position.offset > 0:
        local_symbol = _local_symbol_at(
            project_file.analysis.semantic.model.symbols,
            position.offset - 1,
        )
    if local_symbol is None:
        return None
    project_id = project.local_to_project.get((path, local_symbol.id))
    return project.symbol(project_id) if project_id is not None else None


def goto_definition(
    project: ProjectAnalysis,
    file: str,
    line: int,
    column: int,
) -> DefinitionResult | None:
    symbol = symbol_at(project, file, line, column)
    if symbol is None:
        return None
    return DefinitionResult(
        symbol_id=symbol.id,
        symbol=symbol.name,
        kind=symbol.kind.value,
        type=str(symbol.type),
        definition=symbol.definition,
        declarations=tuple(symbol.declarations),
        is_builtin=symbol.is_builtin,
    )


def find_references(
    project: ProjectAnalysis,
    file: str,
    line: int,
    column: int,
    *,
    include_declarations: bool = True,
) -> tuple[ProjectReference, ...]:
    symbol = symbol_at(project, file, line, column)
    if symbol is None:
        return ()
    results = list(symbol.references)
    if include_declarations:
        results.extend(
            ProjectReference(
                symbol_id=symbol.id,
                location=location,
                access_kind=None,
                is_definition=(
                    symbol.definition is not None and location == symbol.definition
                ),
            )
            for location in symbol.declarations
        )
    return tuple(
        sorted(
            results,
            key=lambda item: (
                item.location.file,
                item.location.offset,
                item.is_definition,
                item.access_kind.value if item.access_kind is not None else "",
            ),
        )
    )


def hover_project(
    project: ProjectAnalysis,
    file: str,
    line: int,
    column: int,
) -> ProjectHover | None:
    symbol = symbol_at(project, file, line, column)
    if symbol is None:
        return None
    return ProjectHover(
        name=symbol.name,
        kind=symbol.kind.value,
        type=str(symbol.type),
        signature=symbol.signature,
        scope=symbol.scope_id,
        definition=symbol.definition,
        declarations=tuple(symbol.declarations),
        documentation=symbol.documentation,
        is_builtin=symbol.is_builtin,
    )


def _local_symbol_at(symbols, offset: int):
    for symbol in symbols:
        if (
            symbol.definition_span is not None
            and symbol.definition_span.start.offset
            <= offset
            < symbol.definition_span.end.offset
        ):
            return symbol
        for reference in symbol.references:
            if reference.span.start.offset <= offset < reference.span.end.offset:
                return symbol
    return None

