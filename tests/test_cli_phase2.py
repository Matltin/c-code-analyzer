"""CLI tests for Phase 2 symbols, completion, hover, and positions."""

import json

from c_analyzer.cli import main


SOURCE = """\
struct Point { int x; int y; };
int add(int left, int right) { return left + right; }
int main(void) {
    struct Point point = {1, 2};
    int value = 3;
    return add(value, point.x);
}
"""


def test_symbols_command_prints_scope_tree(tmp_path, capsys) -> None:
    path = tmp_path / "symbols.c"
    path.write_text(SOURCE, encoding="utf-8")

    exit_code = main(["symbols", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "scope-0001 global" in captured.out
    assert "builtin_function printf" in captured.out
    assert "field x: int" in captured.out


def test_complete_command_supports_text_and_json(tmp_path, capsys) -> None:
    path = tmp_path / "complete.c"
    source = SOURCE.replace(
        "    return add(value, point.x);",
        "    point.\n    return add(value, point.x);",
    )
    path.write_text(source, encoding="utf-8")

    assert main(["complete", str(path), "6", "11"]) == 0
    assert "x" in capsys.readouterr().out
    assert main(["complete", str(path), "6", "11", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert [item["label"] for item in payload["items"]] == ["x", "y"]


def test_hover_command_supports_regular_and_builtin_symbols(
    tmp_path,
    capsys,
) -> None:
    path = tmp_path / "hover.c"
    source = SOURCE.replace(
        "    return add(value, point.x);",
        '    puts("hello");\n    return add(value, point.x);',
    )
    path.write_text(source, encoding="utf-8")

    assert main(["hover", str(path), "7", "12"]) == 0
    assert "name: add" in capsys.readouterr().out
    assert main(["hover", str(path), "6", "5", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["hover"]["name"] == "puts"
    assert payload["hover"]["definition"] == "built-in"


def test_invalid_position_has_exit_two_without_traceback(tmp_path, capsys) -> None:
    path = tmp_path / "position.c"
    path.write_text(SOURCE, encoding="utf-8")

    exit_code = main(["complete", str(path), "999", "1"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "invalid position" in captured.err
    assert "Traceback" not in captured.err

