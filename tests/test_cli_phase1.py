"""End-to-end tests for Phase 1 CLI commands."""

from pathlib import Path
import subprocess
import sys


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "c_analyzer", *arguments],
        capture_output=True,
        check=False,
        text=True,
    )


def write_source(tmp_path: Path, text: str) -> Path:
    source_file = tmp_path / "sample.c"
    source_file.write_text(text, encoding="utf-8")
    return source_file


def test_tokens_command_prints_kind_lexeme_and_location(tmp_path: Path) -> None:
    source_file = write_source(tmp_path, "int x = 1;")

    result = run_cli("tokens", str(source_file))

    assert result.returncode == 0
    assert "KW_INT" in result.stdout
    assert "'int'" in result.stdout
    assert "1:1" in result.stdout
    assert "EOF" in result.stdout


def test_ast_command_prints_deterministic_tree(tmp_path: Path) -> None:
    source_file = write_source(tmp_path, "int x = 1 + 2 * 3;")

    result = run_cli("ast", str(source_file))

    assert result.returncode == 0
    assert "Program" in result.stdout
    assert "VarDecl" in result.stdout
    assert "BinaryExpr" in result.stdout


def test_check_command_uses_exit_status_for_diagnostics(tmp_path: Path) -> None:
    valid_file = write_source(tmp_path, "int x = 1;")
    valid = run_cli("check", str(valid_file))
    valid_file.write_text("int x = ; @", encoding="utf-8")
    invalid = run_cli("check", str(valid_file))

    assert valid.returncode == 0
    assert valid.stdout.strip() == "No diagnostics."
    assert invalid.returncode == 1
    assert "error:" in invalid.stdout


def test_html_highlight_writes_output_file(tmp_path: Path) -> None:
    source_file = write_source(tmp_path, "int x = 1;")
    output_file = tmp_path / "output.html"

    result = run_cli(
        "highlight",
        str(source_file),
        "--format",
        "html",
        "--output",
        str(output_file),
    )

    assert result.returncode == 0
    assert output_file.exists()
    assert "<!doctype html>" in output_file.read_text(encoding="utf-8")


def test_ansi_highlight_prints_colored_source(tmp_path: Path) -> None:
    source_file = write_source(tmp_path, "int x = 1;")

    result = run_cli("highlight", str(source_file), "--format", "ansi")

    assert result.returncode == 0
    assert "\x1b[" in result.stdout


def test_missing_file_is_reported_without_traceback(tmp_path: Path) -> None:
    missing = tmp_path / "missing.c"

    result = run_cli("check", str(missing))

    assert result.returncode == 2
    assert "cannot read" in result.stderr
    assert "Traceback" not in result.stderr

