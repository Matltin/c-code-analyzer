"""Phase 3.5 safe rename preview and atomic apply tests."""

from pathlib import Path

import pytest

from c_analyzer.project import analyze_project
from c_analyzer.refactor import atomic_apply, plan_rename


def position(source: str, needle: str, occurrence: int = 0) -> tuple[int, int]:
    offsets: list[int] = []
    start = 0
    while True:
        offset = source.find(needle, start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + 1
    offset = offsets[occurrence]
    prefix = source[:offset]
    return prefix.count("\n") + 1, offset - prefix.rfind("\n")


def rename(files, file, needle, new_name, occurrence=0):
    project = analyze_project(files)
    line, column = position(files[file], needle, occurrence)
    return plan_rename(project, file, line, column, new_name)


def test_rename_variable_changes_definition_and_only_its_references() -> None:
    source = """\
int main(void) {
    int value = 1;
    int value_extra = value;
    return value_extra;
}
"""
    result = rename({"main.c": source}, "main.c", "value", "number")

    assert result.ok
    assert "int number = 1;" in result.sources["main.c"]
    assert "value_extra = number" in result.sources["main.c"]
    assert "value_extra" in result.sources["main.c"]


def test_rename_parameter_updates_its_reads() -> None:
    source = "int twice(int input) { return input + input; }"
    result = rename({"p.c": source}, "p.c", "input", "value")

    assert result.ok
    assert result.sources["p.c"].count("value") == 3


def test_multifile_function_rename_changes_prototype_definition_and_call() -> None:
    files = {
        "main.c": "int add(int a, int b); int main(void) { return add(1, 2); }",
        "math.c": "int add(int a, int b) { return a + b; }",
    }
    result = rename(files, "main.c", "add", "sum")

    assert result.ok
    assert result.sources["main.c"].count("sum") == 2
    assert "int sum(" in result.sources["math.c"]


def test_struct_and_field_renames_follow_separate_namespaces() -> None:
    source = """\
struct Point { int x; };
int read(struct Point point) { return point.x; }
"""
    struct_result = rename({"s.c": source}, "s.c", "Point", "Coordinate")
    field_result = rename({"s.c": source}, "s.c", "x", "horizontal")

    assert struct_result.ok
    assert struct_result.sources["s.c"].count("Coordinate") == 2
    assert field_result.ok
    assert field_result.sources["s.c"].count("horizontal") == 2


def test_same_name_in_other_scope_is_not_renamed() -> None:
    source = """\
int value = 1;
int main(void) { int value = 2; return value; }
"""
    result = rename(
        {"scope.c": source},
        "scope.c",
        "value",
        "local_value",
        occurrence=1,
    )

    assert result.ok
    assert result.sources["scope.c"].startswith("int value = 1;")
    assert result.sources["scope.c"].count("local_value") == 2


def test_same_scope_conflict_and_capture_are_rejected() -> None:
    same_scope = "int main(void) { int first = 1; int second = 2; return first; }"
    capture = "int global = 1; int main(void) { int local = 2; return local; }"

    conflict = rename({"c.c": same_scope}, "c.c", "first", "second")
    shadow = rename({"c.c": capture}, "c.c", "local", "global")

    assert not conflict.ok
    assert "same namespace and scope" in conflict.errors[0]
    assert not shadow.ok
    assert any("capture or shadow" in error for error in shadow.errors)


def test_multifile_function_rename_rejects_capture_at_a_call_site() -> None:
    files = {
        "main.c": "int compute(void); int main(void) { "
        "int local = 1; return compute() + local; }",
        "lib.c": "int compute(void) { return 1; }",
    }
    result = rename(files, "lib.c", "compute", "local")

    assert not result.ok
    assert any("capture or shadow" in error for error in result.errors)


@pytest.mark.parametrize("new_name", ["", "2bad", "bad-name", "return"])
def test_invalid_or_keyword_names_are_rejected(new_name: str) -> None:
    source = "int value = 1;"
    result = rename({"bad.c": source}, "bad.c", "value", new_name)

    assert not result.ok
    assert result.edits == ()


def test_builtin_cannot_be_renamed() -> None:
    source = 'int main(void) { puts("ok"); return 0; }'
    result = rename({"builtin.c": source}, "builtin.c", "puts", "write_line")

    assert not result.ok
    assert "built-in" in result.errors[0]


def test_comments_strings_and_substrings_are_unchanged() -> None:
    source = """\
int value = 1;
int value_more = 2;
// value must stay in this comment
int main(void) { puts("value"); return value + value_more; }
"""
    result = rename({"text.c": source}, "text.c", "value", "number")

    assert result.ok
    assert "// value must stay" in result.sources["text.c"]
    assert '"value"' in result.sources["text.c"]
    assert result.sources["text.c"].count("value_more") == 2


def test_preview_has_unified_diff_and_does_not_touch_disk(tmp_path: Path) -> None:
    source = "int value = 1;"
    path = tmp_path / "main.c"
    path.write_text(source, encoding="utf-8")
    result = rename({"main.c": source}, "main.c", "value", "number")

    assert result.ok
    assert "--- a/main.c" in result.diff
    assert "+++ b/main.c" in result.diff
    assert path.read_text(encoding="utf-8") == source


def test_atomic_apply_writes_all_changed_files(tmp_path: Path) -> None:
    files = {
        "main.c": "int add(int a, int b); int main(void) { return add(1, 2); }",
        "math.c": "int add(int a, int b) { return a + b; }",
    }
    for name, source in files.items():
        (tmp_path / name).write_text(source, encoding="utf-8")
    result = rename(files, "main.c", "add", "sum")

    atomic_apply(tmp_path, result)

    assert "sum" in (tmp_path / "main.c").read_text(encoding="utf-8")
    assert "sum" in (tmp_path / "math.c").read_text(encoding="utf-8")
    assert not list(tmp_path.glob(".rename-*"))


def test_staging_failure_leaves_all_original_files_untouched(
    tmp_path: Path,
) -> None:
    files = {
        "a.c": "int shared(void); int main(void) { return shared(); }",
        "b.c": "int shared(void) { return 1; }",
    }
    for name, source in files.items():
        (tmp_path / name).write_text(source, encoding="utf-8")
    result = rename(files, "a.c", "shared", "renamed")

    def fail_writer(target: Path, text: str) -> Path:
        raise OSError("injected staging failure")

    with pytest.raises(OSError, match="injected"):
        atomic_apply(tmp_path, result, write_temp=fail_writer)
    assert {
        path.name: path.read_text(encoding="utf-8")
        for path in tmp_path.glob("*.c")
    } == files


def test_mid_replace_failure_rolls_back_every_original(
    tmp_path: Path,
) -> None:
    files = {
        "a.c": "int shared(void); int main(void) { return shared(); }",
        "b.c": "int shared(void) { return 1; }",
    }
    for name, source in files.items():
        (tmp_path / name).write_text(source, encoding="utf-8")
    result = rename(files, "a.c", "shared", "renamed")
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        source.replace(target)

    with pytest.raises(OSError, match="injected"):
        atomic_apply(tmp_path, result, replace=fail_second)
    assert {
        path.name: path.read_text(encoding="utf-8")
        for path in tmp_path.glob("*.c")
    } == files


def test_renamed_sources_are_reanalyzed_before_success() -> None:
    source = "int main(void) { int value = 1; return value; }"
    result = rename({"main.c": source}, "main.c", "value", "number")

    assert result.ok
    project = analyze_project(result.sources)
    assert not project.has_errors
