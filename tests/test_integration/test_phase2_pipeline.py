"""End-to-end Phase 2 integration and recovery tests."""

from c_analyzer import DiagnosticPhase, analyze_source
from c_analyzer.ast import FunctionDecl
from c_analyzer.semantic import complete, hover


def test_end_to_end_valid_source_reaches_semantic_completion_and_hover() -> None:
    source = """
int add(int left, int right) { return left + right; }
int main(void) {
    int value = 2;
    return add(value, 3);
}
"""
    result = analyze_source(source, "e2e.c")
    completion_offset = source.index("return add")
    prefix = source[:completion_offset]
    line = prefix.count("\n") + 1
    column = completion_offset - prefix.rfind("\n")
    hover_offset = source.index("add(value")
    hover_prefix = source[:hover_offset]
    hover_line = hover_prefix.count("\n") + 1
    hover_column = hover_offset - hover_prefix.rfind("\n")

    assert not result.has_errors
    assert result.lexer.tokens
    assert result.parser.ast.declarations
    assert result.semantic.model.symbols
    assert result.semantic.model.type_of(
        result.parser.ast.declarations[1].body.items[1].value
    ).name == "int"
    assert any(item.label == "value" for item in complete(result, line, column))
    assert hover(result, hover_line, hover_column).name == "add"


def test_lexer_error_still_produces_parser_ast_and_semantic_model() -> None:
    result = analyze_source(
        "int main(void) { @; int good = 1; return good; }",
        "lexer_error.c",
    )

    assert any(item.phase is DiagnosticPhase.LEXER for item in result.diagnostics)
    assert result.parser.ast is not None
    assert any(symbol.name == "good" for symbol in result.semantic.model.symbols)


def test_parser_error_still_analyzes_later_valid_statement() -> None:
    result = analyze_source(
        "int main(void) { int broken = ; int good = 1; return good; }",
        "parser_error.c",
    )

    assert any(item.phase is DiagnosticPhase.PARSER for item in result.diagnostics)
    good = next(symbol for symbol in result.semantic.model.symbols if symbol.name == "good")
    assert good.is_used


def test_multiple_semantic_errors_are_collected_without_crash() -> None:
    result = analyze_source(
        """
int takes(int value) { return value; }
int main(void) {
    int *pointer;
    pointer = 1;
    takes("bad");
    missing = 3;
    return "bad";
}
""",
        "semantic_errors.c",
    )
    semantic_errors = [
        item
        for item in result.diagnostics
        if item.phase is DiagnosticPhase.SEMANTIC
        and item.severity.value == "error"
    ]

    assert len(semantic_errors) >= 4


def test_partial_ast_keeps_function_and_semantic_analysis_safe() -> None:
    result = analyze_source(
        "int first(void) { int value = ; return value; ",
        "partial.c",
    )

    assert isinstance(result.parser.ast.declarations[0], FunctionDecl)
    assert result.semantic.model is not None
    assert result.diagnostics


def test_completion_survives_incomplete_code_near_cursor() -> None:
    source = """
struct Point { int field; };
int main(void) { struct Point point = {1}; point.
"""
    result = analyze_source(source, "incomplete.c")
    line = source.count("\n") + 1
    column = len(source.rsplit("\n", 1)[-1]) + 1

    assert [item.label for item in complete(result, line, column)] == ["field"]


def test_pipeline_outputs_are_deterministic_across_runs() -> None:
    source = "int main(void) { int value; return value; }"
    first = analyze_source(source, "repeat.c")
    second = analyze_source(source, "repeat.c")

    assert [item.to_dict() for item in first.diagnostics] == [
        item.to_dict() for item in second.diagnostics
    ]
    assert first.semantic.model.render_symbols() == second.semantic.model.render_symbols()


def test_analysis_state_does_not_leak_between_different_files() -> None:
    first = analyze_source("int only_first;", "first.c")
    second = analyze_source("int only_second;", "second.c")

    first_names = {item.name for item in first.semantic.model.symbols}
    second_names = {item.name for item in second.semantic.model.symbols}
    assert "only_first" in first_names and "only_first" not in second_names
    assert "only_second" in second_names and "only_second" not in first_names

