"""Phase 3 CLI and injectable REPL integration tests."""

from io import StringIO
import json
from pathlib import Path

from c_analyzer.cli import main
from c_analyzer.repl import run_repl


def make_project(root: Path) -> None:
    (root / "main.c").write_text(
        "int helper(int value);\n"
        "int main(void) { int result = helper(2); return result; }\n",
        encoding="utf-8",
    )
    (root / "helper.c").write_text(
        "int helper(int value) { return value + 1; }\n"
        "int unused(void) { return 0; }\n",
        encoding="utf-8",
    )


def test_project_check_and_json(tmp_path: Path, capsys) -> None:
    make_project(tmp_path)

    assert main(["project-check", str(tmp_path)]) == 0
    assert "file: main.c" in capsys.readouterr().out
    assert main(["project-check", str(tmp_path), "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)["files"]) == 2


def test_navigation_commands_and_json(tmp_path: Path, capsys) -> None:
    make_project(tmp_path)
    main_file = tmp_path / "main.c"

    assert main(
        [
            "goto-def",
            str(main_file),
            "2",
            "31",
            "--project",
            str(tmp_path),
            "--json",
        ]
    ) == 0
    assert (
        json.loads(capsys.readouterr().out)["definition"]["definition"]["file"]
        == "helper.c"
    )
    assert main(
        [
            "find-refs",
            str(main_file),
            "2",
            "31",
            "--project",
            str(tmp_path),
            "--json",
        ]
    ) == 0
    assert len(json.loads(capsys.readouterr().out)["references"]) == 3


def test_cfg_callgraph_and_dead_code_commands(tmp_path: Path, capsys) -> None:
    make_project(tmp_path)
    main_file = tmp_path / "main.c"

    assert main(
        [
            "show-cfg",
            str(main_file),
            "main",
            "--project",
            str(tmp_path),
            "--format",
            "json",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["entry_block"]
    assert main(
        [
            "callgraph",
            str(tmp_path),
            "--entry",
            "main",
            "--format",
            "json",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["entry_found"] is True
    assert main(["dead-code", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["dead_functions"][0]["name"] == "unused"


def test_rename_is_dry_run_then_applies_only_with_flag(
    tmp_path: Path,
    capsys,
) -> None:
    make_project(tmp_path)
    main_file = tmp_path / "main.c"
    original = main_file.read_text(encoding="utf-8")
    command = [
        "rename",
        str(main_file),
        "2",
        "22",
        "answer",
        "--project",
        str(tmp_path),
    ]

    assert main(command) == 0
    assert "Preview only" in capsys.readouterr().out
    assert main_file.read_text(encoding="utf-8") == original
    assert main([*command, "--apply"]) == 0
    assert "Applied atomically" in capsys.readouterr().out
    assert "answer" in main_file.read_text(encoding="utf-8")


def test_invalid_project_command_has_no_traceback(tmp_path: Path, capsys) -> None:
    exit_code = main(["project-check", str(tmp_path / "missing")])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


def test_repl_help_commands_invalid_input_exit_and_eof(
    tmp_path: Path,
) -> None:
    make_project(tmp_path)
    input_stream = StringIO(
        "help\n"
        "project-check\n"
        "goto-def main.c 2 31\n"
        "find-refs main.c 2 31\n"
        "show-cfg main.c main\n"
        "callgraph\n"
        "dead-code\n"
        "rename main.c 2 22 answer\n"
        "unknown\n"
        "exit\n"
    )
    output = StringIO()

    assert run_repl(
        tmp_path,
        input_stream=input_stream,
        output_stream=output,
    ) == 0
    text = output.getvalue()
    assert "Commands:" in text
    assert "definition: helper.c" in text
    assert "CFG" in text
    assert "Call graph" in text
    assert "Preview only" in text
    assert "unknown or invalid" in text
    assert "Traceback" not in text

    eof_output = StringIO()
    assert run_repl(
        tmp_path,
        input_stream=StringIO(""),
        output_stream=eof_output,
    ) == 0
