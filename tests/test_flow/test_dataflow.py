"""Phase 3.3 fixed-point data-flow and dead-code tests."""

from c_analyzer import analyze_source
from c_analyzer.ast import FunctionDecl
from c_analyzer.flow import analyze_dataflow, build_cfg, render_dataflow
from c_analyzer.semantic import SymbolKind


def analyze_function(source: str, name: str = "test"):
    analysis = analyze_source(source, "flow.c")
    function = next(
        item
        for item in analysis.parser.ast.declarations
        if isinstance(item, FunctionDecl) and item.name.text == name
    )
    symbol = analysis.semantic.model.symbol_of(function.name)
    assert symbol is not None
    cfg = build_cfg(function, symbol.id)
    return analysis, function, analyze_dataflow(
        function,
        analysis.semantic.model,
        cfg,
    )


def local_symbol(analysis, name: str):
    return next(
        symbol
        for symbol in analysis.semantic.model.symbols
        if symbol.name == name
        and symbol.kind in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}
    )


def return_block(result):
    return next(
        block
        for block in result.cfg.blocks
        if any(type(node).__name__ == "ReturnStmt" for node in block.nodes)
    )


def test_parameter_and_globals_start_definitely_assigned() -> None:
    analysis, _, result = analyze_function(
        "int global_value; int test(int input) { return input + global_value; }"
    )
    parameter = local_symbol(analysis, "input")
    global_value = local_symbol(analysis, "global_value")

    assert {
        parameter.id,
        global_value.id,
    } <= result.definitely_assigned_in[result.cfg.entry_block]


def test_parameters_from_another_function_do_not_leak_into_state() -> None:
    analysis, _, result = analyze_function(
        "int other(int foreign) { return foreign; } "
        "int test(int own) { return own; }"
    )
    foreign = local_symbol(analysis, "foreign")
    own = local_symbol(analysis, "own")

    assert own.id in result.definitely_assigned_in[result.cfg.entry_block]
    assert foreign.id not in result.definitely_assigned_in[result.cfg.entry_block]


def test_read_before_assignment_is_reported_once_in_flow_result() -> None:
    _, _, result = analyze_function(
        "int test(void) { int value; int copy = value; return copy; }"
    )
    warnings = [
        item
        for item in result.diagnostics
        if "value" in item.message and "before initialization" in item.message
    ]

    assert len(warnings) == 1


def test_assignment_in_only_one_branch_is_not_definite_after_if() -> None:
    analysis, _, result = analyze_function(
        "int test(int condition) { int value; "
        "if (condition) value = 1; return value; }"
    )
    value = local_symbol(analysis, "value")

    assert value.id not in result.definitely_assigned_in[
        return_block(result).id
    ]


def test_assignment_in_both_branches_is_definite_after_if() -> None:
    analysis, _, result = analyze_function(
        "int test(int condition) { int value; "
        "if (condition) value = 1; else value = 2; return value; }"
    )
    value = local_symbol(analysis, "value")

    assert value.id in result.definitely_assigned_in[return_block(result).id]


def test_loop_assignment_is_not_assumed_when_loop_may_run_zero_times() -> None:
    analysis, _, result = analyze_function(
        "int test(int condition) { int value; "
        "while (condition) value = 1; return value; }"
    )
    value = local_symbol(analysis, "value")

    assert value.id not in result.definitely_assigned_in[
        return_block(result).id
    ]


def test_liveness_linear_flow_tracks_read_variable() -> None:
    analysis, _, result = analyze_function(
        "int test(void) { int value = 1; return value; }"
    )
    value = local_symbol(analysis, "value")
    assignment_block = next(
        block
        for block in result.cfg.blocks
        if any(type(node).__name__ == "VarDecl" for node in block.nodes)
    )

    assert value.id in result.live_out[assignment_block.id]


def test_liveness_converges_for_branch_and_loop() -> None:
    _, _, result = analyze_function(
        "int test(int n) { int sum = 0; while (n) { "
        "if (n > 2) sum += n; n--; } return sum; }"
    )

    assert result.liveness_iterations > 0
    assert result.liveness_iterations < 500
    assert any(result.live_in.values())


def test_dead_assignment_and_overwrite_before_read_are_reported() -> None:
    _, _, result = analyze_function(
        "int test(void) { int value; value = 1; value = 2; return value; }"
    )

    findings = result.dead_code.dead_assignments
    assert len(findings) == 1
    assert findings[0].span.start.line == 1


def test_increment_is_read_write_not_a_dead_assignment() -> None:
    _, _, result = analyze_function(
        "int test(void) { int value = 1; value++; return value; }"
    )

    assert result.dead_code.dead_assignments == ()


def test_dead_assignment_with_call_rhs_warns_to_preserve_side_effects() -> None:
    _, _, result = analyze_function(
        "int side(void) { return 1; } "
        "int test(void) { int value; value = side(); return 0; }"
    )

    assert any(
        "side effects" in finding.message
        for finding in result.dead_code.dead_assignments
    )


def test_unreachable_statement_after_return_is_preserved() -> None:
    _, _, result = analyze_function(
        "int test(void) { return 1; int value = 2; }"
    )

    assert result.dead_code.unreachable_blocks
    assert result.dead_code.post_jump_statements


def test_unreachable_statement_after_break_and_continue() -> None:
    _, _, after_break = analyze_function(
        "int test(int x) { while (x) { break; x = 1; } return x; }"
    )
    _, _, after_continue = analyze_function(
        "int test(int x) { while (x) { continue; x = 1; } return x; }"
    )

    assert after_break.dead_code.post_jump_statements
    assert after_continue.dead_code.post_jump_statements


def test_non_void_fallthrough_reports_missing_return() -> None:
    _, _, result = analyze_function(
        "int test(int x) { if (x) return 1; }"
    )

    assert len(result.dead_code.missing_returns) == 1


def test_void_function_is_exempt_from_missing_return() -> None:
    _, _, result = analyze_function("void test(void) { int x = 1; }")

    assert result.dead_code.missing_returns == ()


def test_phase2_unused_diagnostic_is_not_duplicated_in_combined_view() -> None:
    _, _, result = analyze_function(
        "int test(void) { int unused = 1; return 0; }"
    )
    matching = [
        item
        for item in result.diagnostics
        if "unused variable 'unused'" in item.message
    ]

    assert len(matching) == 1


def test_analysis_is_deterministic_across_repeated_runs() -> None:
    source = "int test(int x) { while (x) x--; return x; }"
    _, _, first = analyze_function(source)
    _, _, second = analyze_function(source)

    assert first.definitely_assigned_in == second.definitely_assigned_in
    assert first.live_out == second.live_out
    assert first.dead_code == second.dead_code
    assert render_dataflow(first) == render_dataflow(second)
