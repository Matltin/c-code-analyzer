"""Phase 3.2 control-flow graph construction and validation tests."""

import json

from c_analyzer import analyze_source
from c_analyzer.ast import FunctionDecl, print_ast
from c_analyzer.flow import (
    BasicBlock,
    CFGEdge,
    ControlFlowGraph,
    EdgeKind,
    build_cfg,
    cfg_to_dot,
    cfg_to_json,
    cfg_to_text,
    validate_cfg,
)


def make_cfg(source: str):
    result = analyze_source(source, "cfg.c")
    function = next(
        item
        for item in result.parser.ast.declarations
        if isinstance(item, FunctionDecl)
    )
    symbol = result.semantic.model.symbol_of(function.name)
    assert symbol is not None
    return result, function, build_cfg(function, symbol.id)


def test_empty_function_connects_entry_directly_to_exit() -> None:
    _, _, cfg = make_cfg("void empty(void) {}")

    assert len(cfg.blocks) == 2
    assert cfg.edges == (
        CFGEdge(cfg.entry_block, cfg.exit_block, EdgeKind.FALLTHROUGH),
    )
    assert validate_cfg(cfg) == ()


def test_linear_statements_share_a_basic_block() -> None:
    _, _, cfg = make_cfg(
        "int main(void) { int x = 1; x = x + 1; return x; }"
    )

    linear = [
        block
        for block in cfg.blocks
        if [type(node).__name__ for node in block.nodes]
        == ["VarDecl", "ExprStmt"]
    ]
    assert len(linear) == 1
    assert validate_cfg(cfg) == ()


def test_if_without_else_has_true_and_false_edges() -> None:
    _, _, cfg = make_cfg(
        "int choose(int x) { if (x) return 1; return 0; }"
    )

    kinds = {edge.kind for edge in cfg.edges}
    assert EdgeKind.TRUE_BRANCH in kinds
    assert EdgeKind.FALSE_BRANCH in kinds
    assert sum(edge.kind is EdgeKind.RETURN for edge in cfg.edges) == 2


def test_if_else_builds_two_return_paths() -> None:
    _, _, cfg = make_cfg(
        "int choose(int x) { if (x) { return 1; } else { return 2; } }"
    )

    assert sum(edge.kind is EdgeKind.RETURN for edge in cfg.edges) == 2
    assert validate_cfg(cfg) == ()


def test_while_loop_has_branch_exit_and_loop_back_edge() -> None:
    _, _, cfg = make_cfg(
        "int loop(int x) { while (x) { x = x - 1; } return x; }"
    )

    kinds = {edge.kind for edge in cfg.edges}
    assert {
        EdgeKind.TRUE_BRANCH,
        EdgeKind.FALSE_BRANCH,
        EdgeKind.LOOP_BACK,
    } <= kinds


def test_for_loop_has_initializer_update_and_loop_back() -> None:
    _, _, cfg = make_cfg(
        "int loop(void) { int n = 0; "
        "for (int i = 0; i < 3; i++) { n += i; } return n; }"
    )

    assert EdgeKind.LOOP_BACK in {edge.kind for edge in cfg.edges}
    assert validate_cfg(cfg) == ()


def test_nested_loop_break_and_continue_use_explicit_edge_kinds() -> None:
    _, _, cfg = make_cfg(
        "int scan(int x) { while (x) { "
        "if (x == 2) break; if (x == 3) { x--; continue; } x--; "
        "} return x; }"
    )

    kinds = {edge.kind for edge in cfg.edges}
    assert EdgeKind.BREAK in kinds
    assert EdgeKind.CONTINUE in kinds
    assert validate_cfg(cfg) == ()


def test_return_terminates_flow_but_preserves_unreachable_statement() -> None:
    _, _, cfg = make_cfg(
        "int stop(void) { return 1; int unreachable = 2; }"
    )

    unreachable = set(block.id for block in cfg.blocks) - set(
        cfg.reachable_blocks()
    )
    assert any(
        type(node).__name__ == "VarDecl"
        for block in cfg.blocks
        if block.id in unreachable
        for node in block.nodes
    )


def test_multiple_returns_connect_to_the_single_exit_block() -> None:
    _, _, cfg = make_cfg(
        "int pick(int x) { if (x) return x; return 0; }"
    )

    return_edges = [
        edge for edge in cfg.edges if edge.kind is EdgeKind.RETURN
    ]
    assert len(return_edges) == 2
    assert {edge.target for edge in return_edges} == {cfg.exit_block}


def test_predecessors_and_successors_are_symmetric() -> None:
    _, _, cfg = make_cfg(
        "int main(void) { int x = 0; while (x < 2) x++; return x; }"
    )

    for edge in cfg.edges:
        assert edge.target in cfg.block(edge.source).successors
        assert edge.source in cfg.block(edge.target).predecessors


def test_cfg_outputs_are_deterministic_and_machine_readable() -> None:
    source = "int main(void) { int x = 1; if (x) x++; return x; }"
    _, _, first = make_cfg(source)
    _, _, second = make_cfg(source)

    assert cfg_to_text(first) == cfg_to_text(second)
    assert cfg_to_json(first) == cfg_to_json(second)
    assert json.loads(cfg_to_json(first))["entry_block"] == first.entry_block
    dot = cfg_to_dot(first)
    assert dot.startswith("digraph cfg {")
    assert "true_branch" in dot


def test_validator_reports_unknown_and_asymmetric_neighbors_safely() -> None:
    _, _, good = make_cfg("void empty(void) {}")
    entry = good.block(good.entry_block)
    broken_entry = BasicBlock(
        id=entry.id,
        nodes=list(entry.nodes),
        span=entry.span,
        successors=["missing-block"],
    )
    broken = ControlFlowGraph(
        function_symbol_id=good.function_symbol_id,
        entry_block=good.entry_block,
        exit_block=good.exit_block,
        blocks=(broken_entry, good.block(good.exit_block)),
        edges=(CFGEdge(good.entry_block, "missing-block", EdgeKind.FALLTHROUGH),),
    )

    errors = validate_cfg(broken)
    assert any("unknown block" in error for error in errors)


def test_cfg_construction_does_not_mutate_ast_or_semantic_model() -> None:
    result, function, _ = make_cfg(
        "int main(void) { int x = 1; x++; return x; }"
    )
    ast_before = print_ast(result.parser.ast)
    symbols_before = result.semantic.model.render_symbols()
    symbol = result.semantic.model.symbol_of(function.name)
    assert symbol is not None

    build_cfg(function, symbol.id)

    assert print_ast(result.parser.ast) == ast_before
    assert result.semantic.model.render_symbols() == symbols_before

