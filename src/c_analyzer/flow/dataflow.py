"""CFG-backed definite assignment, liveness, and dead-code reporting."""

from __future__ import annotations

from dataclasses import dataclass

from c_analyzer.ast import FunctionDecl, VarDecl
from c_analyzer.core import Diagnostic, DiagnosticPhase, Severity, SourceSpan
from c_analyzer.flow.cfg import ControlFlowGraph, EdgeKind
from c_analyzer.flow.worklist import (
    WorklistResult,
    intersect_states,
    solve_backward,
    solve_forward,
    union_states,
)
from c_analyzer.semantic import (
    AccessKind,
    FunctionType,
    SemanticModel,
    Symbol,
    SymbolKind,
    VOID,
)


@dataclass(frozen=True, slots=True)
class CodeFinding:
    category: str
    message: str
    span: SourceSpan
    symbol_id: str | None = None


@dataclass(frozen=True, slots=True)
class DeadCodeReport:
    unreachable_blocks: tuple[str, ...] = ()
    post_jump_statements: tuple[CodeFinding, ...] = ()
    unused_variables: tuple[CodeFinding, ...] = ()
    dead_assignments: tuple[CodeFinding, ...] = ()
    missing_returns: tuple[CodeFinding, ...] = ()
    dead_functions: tuple[CodeFinding, ...] = ()

    @property
    def findings(self) -> tuple[CodeFinding, ...]:
        return (
            *self.post_jump_statements,
            *self.unused_variables,
            *self.dead_assignments,
            *self.missing_returns,
            *self.dead_functions,
        )


@dataclass(frozen=True, slots=True)
class DataFlowResult:
    cfg: ControlFlowGraph
    definitely_assigned_in: dict[str, frozenset[str]]
    definitely_assigned_out: dict[str, frozenset[str]]
    live_in: dict[str, frozenset[str]]
    live_out: dict[str, frozenset[str]]
    definite_assignment_iterations: int
    liveness_iterations: int
    diagnostics: tuple[Diagnostic, ...]
    dead_code: DeadCodeReport


@dataclass(frozen=True, slots=True)
class _Facts:
    uses: frozenset[str]
    definitions: frozenset[str]


def analyze_dataflow(
    function: FunctionDecl,
    model: SemanticModel,
    cfg: ControlFlowGraph,
) -> DataFlowResult:
    """Run deterministic intraprocedural analyses for one function."""
    symbols = _function_symbols(function, model)
    symbol_by_id = {item.id: item for item in symbols}
    facts = {
        block.id: _facts_for_block(block.nodes, symbols)
        for block in cfg.blocks
    }
    function_symbol_ids = {symbol.id for symbol in symbols}
    initially_assigned = frozenset(
        symbol.id
        for symbol in model.symbols
        if (
            symbol.kind is SymbolKind.PARAMETER
            and symbol.id in function_symbol_ids
        )
        or (
            symbol.kind is SymbolKind.VARIABLE
            and symbol.scope_id == model.global_scope.id
        )
    )

    definite = solve_forward(
        cfg,
        entry_state=initially_assigned,
        bottom=frozenset(),
        transfer=lambda block_id, state: state | facts[block_id].definitions,
        meet=intersect_states,
    )
    live = solve_backward(
        cfg,
        exit_state=frozenset(),
        bottom=frozenset(),
        transfer=lambda block_id, state: (
            facts[block_id].uses
            | (state - facts[block_id].definitions)
        ),
        meet=union_states,
    )

    reachable = cfg.reachable_blocks()
    unreachable = tuple(
        block.id for block in cfg.blocks if block.id not in reachable
    )
    post_jump = tuple(
        CodeFinding(
            category="unreachable",
            message="statement is unreachable after a control-flow jump",
            span=node.span,
        )
        for block in cfg.blocks
        if block.id not in reachable
        for node in block.nodes
    )
    unused = tuple(
        CodeFinding(
            category="unused_variable",
            message=f"unused {symbol.kind.value} '{symbol.name}'",
            span=symbol.definition_span,
            symbol_id=symbol.id,
        )
        for symbol in symbols
        if symbol.definition_span is not None
        and symbol.kind in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}
        and not symbol.is_used
    )
    dead_assignments = _dead_assignments(cfg, symbols, live.out_state)
    missing_returns = _missing_return(function, model, cfg, reachable)
    report = DeadCodeReport(
        unreachable_blocks=unreachable,
        post_jump_statements=post_jump,
        unused_variables=unused,
        dead_assignments=dead_assignments,
        missing_returns=missing_returns,
    )
    diagnostics = _combined_diagnostics_without_duplicates(
        report,
        model.diagnostics,
    )
    return DataFlowResult(
        cfg=cfg,
        definitely_assigned_in=definite.in_state,
        definitely_assigned_out=definite.out_state,
        live_in=live.in_state,
        live_out=live.out_state,
        definite_assignment_iterations=definite.iterations,
        liveness_iterations=live.iterations,
        diagnostics=diagnostics,
        dead_code=report,
    )


def _function_symbols(
    function: FunctionDecl,
    model: SemanticModel,
) -> tuple[Symbol, ...]:
    return tuple(
        symbol
        for symbol in model.symbols
        if symbol.definition_span is not None
        and (
            (
                symbol.kind is SymbolKind.PARAMETER
                and function.span.start.offset
                <= symbol.definition_span.start.offset
                <= function.span.end.offset
            )
            or (
                symbol.kind is SymbolKind.VARIABLE
                and function.span.start.offset
                <= symbol.definition_span.start.offset
                <= function.span.end.offset
            )
        )
    )


def _facts_for_block(nodes, symbols: tuple[Symbol, ...]) -> _Facts:
    uses: set[str] = set()
    definitions: set[str] = set()
    for node in nodes:
        for symbol in symbols:
            if (
                isinstance(node, VarDecl)
                and symbol.definition_span == node.name.span
                and node.initializer is not None
            ):
                definitions.add(symbol.id)
            for reference in symbol.references:
                if not _contains(node.span, reference.span):
                    continue
                if reference.access_kind in {
                    AccessKind.READ,
                    AccessKind.READ_WRITE,
                    AccessKind.CALL,
                    AccessKind.MEMBER_ACCESS,
                }:
                    uses.add(symbol.id)
                if reference.access_kind in {
                    AccessKind.WRITE,
                    AccessKind.READ_WRITE,
                }:
                    definitions.add(symbol.id)
    return _Facts(frozenset(uses), frozenset(definitions))


def _dead_assignments(
    cfg: ControlFlowGraph,
    symbols: tuple[Symbol, ...],
    live_out: dict[str, frozenset[str]],
) -> tuple[CodeFinding, ...]:
    findings: list[CodeFinding] = []
    reachable = cfg.reachable_blocks()
    for block in cfg.blocks:
        if block.id not in reachable:
            continue
        live = set(live_out[block.id])
        references = sorted(
            (
                (reference.span.start.offset, symbol, reference)
                for symbol in symbols
                for reference in symbol.references
                if any(_contains(node.span, reference.span) for node in block.nodes)
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        for _, symbol, reference in references:
            if reference.access_kind is AccessKind.READ_WRITE:
                live.add(symbol.id)
            elif reference.access_kind is AccessKind.READ:
                live.add(symbol.id)
            elif reference.access_kind is AccessKind.WRITE:
                if symbol.id not in live:
                    findings.append(
                        CodeFinding(
                            category="dead_assignment",
                            message=(
                                f"value assigned to '{symbol.name}' is never read; "
                                "RHS side effects, if any, must be preserved"
                            ),
                            span=reference.span,
                            symbol_id=symbol.id,
                        )
                    )
                live.discard(symbol.id)
    return tuple(
        sorted(
            findings,
            key=lambda item: (
                item.span.start.file,
                item.span.start.offset,
                item.message,
            ),
        )
    )


def _missing_return(
    function: FunctionDecl,
    model: SemanticModel,
    cfg: ControlFlowGraph,
    reachable: frozenset[str],
) -> tuple[CodeFinding, ...]:
    symbol = model.symbol_of(function.name)
    if (
        symbol is None
        or not isinstance(symbol.type, FunctionType)
        or symbol.type.return_type == VOID
    ):
        return ()
    has_fallthrough = any(
        edge.target == cfg.exit_block
        and edge.source in reachable
        and edge.kind is not EdgeKind.RETURN
        for edge in cfg.edges
    )
    if not has_fallthrough:
        return ()
    return (
        CodeFinding(
            category="missing_return",
            message=f"non-void function '{symbol.name}' may reach exit without return",
            span=function.name.span,
            symbol_id=symbol.id,
        ),
    )


def _combined_diagnostics_without_duplicates(
    report: DeadCodeReport,
    existing: tuple[Diagnostic, ...],
) -> tuple[Diagnostic, ...]:
    existing_keys = {
        (item.span.start.offset, item.message) for item in existing
    }
    diagnostics: list[Diagnostic] = list(existing)
    for finding in report.findings:
        key = (finding.span.start.offset, finding.message)
        if key in existing_keys:
            continue
        severity = (
            Severity.INFO
            if finding.category == "unused_variable"
            else Severity.WARNING
        )
        diagnostics.append(
            Diagnostic(
                phase=DiagnosticPhase.ANALYSIS,
                severity=severity,
                message=finding.message,
                span=finding.span,
            )
        )
    unique: dict[tuple[object, ...], Diagnostic] = {}
    for diagnostic in diagnostics:
        unique.setdefault(
            (
                diagnostic.phase,
                diagnostic.severity,
                diagnostic.message,
                diagnostic.file,
                diagnostic.span.start.offset,
                diagnostic.span.end.offset,
            ),
            diagnostic,
        )
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.file,
                item.span.start.offset,
                item.phase.value,
                item.severity.value,
                item.message,
            ),
        )
    )


def _contains(outer: SourceSpan, inner: SourceSpan) -> bool:
    return (
        outer.start.file == inner.start.file
        and outer.start.offset <= inner.start.offset
        and inner.end.offset <= outer.end.offset
    )


def render_dataflow(result: DataFlowResult) -> str:
    lines = [f"Data-flow {result.cfg.function_symbol_id}"]
    for block in result.cfg.blocks:
        lines.append(
            f"{block.id}: assigned_in={sorted(result.definitely_assigned_in[block.id])} "
            f"assigned_out={sorted(result.definitely_assigned_out[block.id])} "
            f"live_in={sorted(result.live_in[block.id])} "
            f"live_out={sorted(result.live_out[block.id])}"
        )
    return "\n".join(lines)


def render_dead_code(report: DeadCodeReport) -> str:
    lines = [
        f"unreachable_blocks: {len(report.unreachable_blocks)}",
        f"post_jump_statements: {len(report.post_jump_statements)}",
        f"unused_variables: {len(report.unused_variables)}",
        f"dead_assignments: {len(report.dead_assignments)}",
        f"missing_returns: {len(report.missing_returns)}",
        f"dead_functions: {len(report.dead_functions)}",
    ]
    for finding in report.findings:
        lines.append(
            f"{finding.span.start.file}:{finding.span.start.line}:"
            f"{finding.span.start.column}: {finding.category}: {finding.message}"
        )
    return "\n".join(lines)
