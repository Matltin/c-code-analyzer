"""Build a call graph from the shared multi-file project index."""

from __future__ import annotations

from c_analyzer.ast import FunctionDecl
from c_analyzer.callgraph.model import CallGraph, CallGraphEdge, CallGraphNode
from c_analyzer.project import ProjectAnalysis
from c_analyzer.semantic import AccessKind, SymbolKind


def build_call_graph(project: ProjectAnalysis) -> CallGraph:
    functions = [
        symbol
        for symbol in project.symbols
        if symbol.kind in {
            SymbolKind.FUNCTION,
            SymbolKind.BUILTIN_FUNCTION,
        }
    ]
    nodes = tuple(
        CallGraphNode(
            symbol_id=symbol.id,
            name=symbol.name,
            kind=(
                "builtin"
                if symbol.is_builtin
                else "defined"
                if symbol.definition is not None
                else "external"
            ),
            definition=symbol.definition,
        )
        for symbol in functions
    )
    grouped: dict[tuple[str, str], list] = {}
    for callee in functions:
        for reference in callee.references:
            if reference.access_kind is not AccessKind.CALL:
                continue
            caller = _containing_function(project, reference.location)
            if caller is None:
                continue
            grouped.setdefault((caller, callee.id), []).append(
                reference.location
            )
    edges = tuple(
        CallGraphEdge(
            caller_symbol_id=caller,
            callee_symbol_id=callee,
            call_sites=tuple(
                sorted(
                    locations,
                    key=lambda item: (item.file, item.offset),
                )
            ),
        )
        for (caller, callee), locations in sorted(grouped.items())
    )
    return CallGraph(nodes=nodes, edges=edges)


def _containing_function(project: ProjectAnalysis, location) -> str | None:
    file = project.file(location.file)
    if file is None:
        return None
    candidates = [
        declaration
        for declaration in file.analysis.parser.ast.declarations
        if isinstance(declaration, FunctionDecl)
        and declaration.span.start.offset
        <= location.offset
        < declaration.span.end.offset
    ]
    if not candidates:
        return None
    declaration = candidates[0]
    local = file.analysis.semantic.model.symbol_of(declaration.name)
    if local is None:
        return None
    return project.local_to_project.get((file.path, local.id))

