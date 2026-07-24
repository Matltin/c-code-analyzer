"""Tests for the shared diagnostic pipeline and JSON output."""

import json

from c_analyzer import (
    Diagnostic,
    DiagnosticPhase,
    Severity,
    SourcePosition,
    SourceSpan,
    analyze_source,
    diagnostics_to_json,
    sort_diagnostics,
)
from c_analyzer.cli import main


def span(offset: int, length: int = 1) -> SourceSpan:
    start = SourcePosition(
        file="diagnostics.c",
        line=1,
        column=offset + 1,
        offset=offset,
    )
    end = SourcePosition(
        file="diagnostics.c",
        line=1,
        column=offset + length + 1,
        offset=offset + length,
    )
    return SourceSpan(start=start, end=end)


def diagnostic(offset: int, message: str = "problem") -> Diagnostic:
    return Diagnostic(
        phase=DiagnosticPhase.SEMANTIC,
        severity=Severity.ERROR,
        message=message,
        span=span(offset),
    )


def test_diagnostic_exposes_all_machine_readable_fields_and_length() -> None:
    item = diagnostic(3, "undefined symbol")
    payload = item.to_dict()

    assert payload == {
        "phase": "semantic",
        "severity": "error",
        "message": "undefined symbol",
        "file": "diagnostics.c",
        "line": 1,
        "column": 4,
        "length": 1,
    }


def test_sorting_is_deterministic_and_exact_duplicates_are_removed() -> None:
    later = diagnostic(8, "later")
    earlier = diagnostic(2, "earlier")

    first = sort_diagnostics([later, earlier, later])
    second = sort_diagnostics([later, earlier, later])

    assert first == second == (earlier, later)


def test_pipeline_collects_multiple_phases_without_crashing() -> None:
    result = analyze_source(
        "int main(void) { @; missing = ; return 0; }",
        "multi_phase.c",
    )
    phases = {item.phase for item in result.diagnostics}

    assert DiagnosticPhase.LEXER in phases
    assert DiagnosticPhase.PARSER in phases
    assert DiagnosticPhase.SEMANTIC in phases
    assert result.has_errors


def test_json_is_valid_unicode_safe_and_has_counts() -> None:
    item = Diagnostic(
        phase=DiagnosticPhase.SEMANTIC,
        severity=Severity.WARNING,
        message="هشدار آزمایشی",
        span=span(0, 2),
    )
    text = diagnostics_to_json([item])
    payload = json.loads(text)

    assert "هشدار آزمایشی" in text
    assert payload["diagnostics"][0]["length"] == 2
    assert payload["error_count"] == 0
    assert payload["warning_count"] == 1


def test_cli_json_output_is_machine_readable(tmp_path, capsys) -> None:
    source = tmp_path / "error.c"
    source.write_text(
        'int main(void) { int *pointer; pointer = "wrong"; return 0; }',
        encoding="utf-8",
    )

    exit_code = main(["check", str(source), "--json"])
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 1
    assert payload["error_count"] >= 1
    assert {
        "phase",
        "severity",
        "message",
        "file",
        "line",
        "column",
        "length",
    } <= payload["diagnostics"][0].keys()


def test_cli_exit_zero_for_source_without_diagnostics(tmp_path, capsys) -> None:
    source = tmp_path / "valid.c"
    source.write_text("int main(void) { return 0; }", encoding="utf-8")

    assert main(["check", str(source)]) == 0
    assert capsys.readouterr().out.strip() == "No diagnostics."


def test_warning_and_info_without_error_keep_success_exit_code(
    tmp_path,
    capsys,
) -> None:
    source = tmp_path / "warnings.c"
    source.write_text(
        "int main(void) { int unused = 2.5; return 0; }",
        encoding="utf-8",
    )

    exit_code = main(["check", str(source)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "warning" in output
    assert "info" in output


def test_partial_ast_pipeline_has_no_raw_traceback(tmp_path, capsys) -> None:
    source = tmp_path / "partial.c"
    source.write_text(
        "int main(void) { int value = ; return missing; ",
        encoding="utf-8",
    )

    exit_code = main(["check", str(source)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


def test_analysis_order_is_stable_across_repeated_runs() -> None:
    source = "int main(void) { missing = ; int unused; return 0; }"

    first = analyze_source(source, "stable.c")
    second = analyze_source(source, "stable.c")

    assert [item.to_dict() for item in first.diagnostics] == [
        item.to_dict() for item in second.diagnostics
    ]

