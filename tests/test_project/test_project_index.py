"""Phase 3.1 multi-file project indexing and navigation tests."""

from c_analyzer import analyze_source
from c_analyzer.project import (
    analyze_project,
    find_references,
    goto_definition,
    hover_project,
)
from c_analyzer.semantic import AccessKind


FILES = {
    "main.c": """\
int add(int left, int right);
int main(void) {
    int value = add(1, 2);
    return value;
}
""",
    "math/add.c": """\
// Adds two integer values.
int add(int left, int right) {
    return left + right;
}
""",
}


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


def test_project_files_are_normalized_and_sorted_deterministically() -> None:
    project = analyze_project(
        {
            "./z.c": "int z;",
            "folder\\a.c": "int a;",
        },
        root="demo",
    )

    assert [file.path for file in project.files] == ["folder/a.c", "z.c"]
    assert project.root == "demo"


def test_prototype_definition_and_cross_file_call_share_project_symbol() -> None:
    project = analyze_project(FILES)
    add_symbols = [
        symbol
        for symbol in project.symbols
        if symbol.name == "add" and symbol.kind.value == "function"
    ]

    assert len(add_symbols) == 1
    add = add_symbols[0]
    assert add.definition is not None
    assert add.definition.file == "math/add.c"
    assert {item.file for item in add.declarations} == {"main.c", "math/add.c"}
    assert any(
        item.location.file == "main.c" and item.access_kind is AccessKind.CALL
        for item in add.references
    )


def test_duplicate_function_definition_across_files_is_reported() -> None:
    project = analyze_project(
        {
            "a.c": "int duplicate(void) { return 1; }",
            "b.c": "int duplicate(void) { return 2; }",
        }
    )

    assert any(
        "duplicate project function definition 'duplicate'" in item.message
        for item in project.diagnostics
    )


def test_conflicting_cross_file_function_declaration_is_reported() -> None:
    project = analyze_project(
        {
            "a.c": "int convert(int value);",
            "b.c": "double convert(int value) { return value; }",
        }
    )

    assert any(
        "conflicting project declaration for function 'convert'" in item.message
        for item in project.diagnostics
    )


def test_goto_definition_for_local_variable_uses_exact_symbol() -> None:
    source = FILES["main.c"]
    project = analyze_project(FILES)
    line, column = position(source, "value", occurrence=1)
    result = goto_definition(project, "main.c", line, column)

    assert result is not None
    assert result.symbol == "value"
    assert result.kind == "variable"
    assert result.definition is not None
    assert result.definition.file == "main.c"
    assert result.definition.line == 3


def test_goto_definition_prefers_cross_file_function_definition() -> None:
    source = FILES["main.c"]
    project = analyze_project(FILES)
    line, column = position(source, "add", occurrence=1)
    result = goto_definition(project, "main.c", line, column)

    assert result is not None
    assert result.symbol == "add"
    assert result.definition is not None
    assert result.definition.file == "math/add.c"
    assert len(result.declarations) == 2


def test_struct_field_navigation_finds_field_definition() -> None:
    source = """\
struct Point { int x; };
int read(struct Point point) { return point.x; }
"""
    project = analyze_project({"structs.c": source})
    line, column = position(source, "x", occurrence=1)
    result = goto_definition(project, "structs.c", line, column)

    assert result is not None
    assert result.kind == "field"
    assert result.definition is not None
    assert result.definition.line == 1


def test_find_references_separates_definitions_and_access_kinds() -> None:
    source = """\
int main(void) {
    int value = 1;
    value = value + 1;
    value++;
    return value;
}
"""
    project = analyze_project({"refs.c": source})
    line, column = position(source, "value", occurrence=0)
    references = find_references(project, "refs.c", line, column)

    assert any(item.is_definition for item in references)
    accesses = {
        item.access_kind for item in references if item.access_kind is not None
    }
    assert {
        AccessKind.READ,
        AccessKind.WRITE,
        AccessKind.READ_WRITE,
    } <= accesses
    assert list(references) == sorted(
        references,
        key=lambda item: (
            item.location.file,
            item.location.offset,
            item.is_definition,
            item.access_kind.value if item.access_kind is not None else "",
        ),
    )


def test_same_name_in_different_scopes_has_distinct_project_ids() -> None:
    source = """\
int value = 1;
int main(void) {
    int value = 2;
    return value;
}
"""
    project = analyze_project({"scopes.c": source})
    values = [symbol for symbol in project.symbols if symbol.name == "value"]

    assert len(values) == 2
    assert values[0].id != values[1].id
    assert values[0].scope_id != values[1].scope_id


def test_comments_and_strings_do_not_create_references() -> None:
    source = """\
int value = 1;
int main(void) {
    // value is mentioned here
    puts("value");
    return value;
}
"""
    project = analyze_project({"comments.c": source})
    line, column = position(source, "value", occurrence=0)
    references = find_references(project, "comments.c", line, column)

    assert len([item for item in references if not item.is_definition]) == 1
    assert references[-1].location.line == 5


def test_project_hover_includes_definition_declarations_and_documentation() -> None:
    project = analyze_project(FILES)
    line, column = position(FILES["main.c"], "add", occurrence=1)
    result = hover_project(project, "main.c", line, column)

    assert result is not None
    assert result.definition is not None
    assert result.definition.file == "math/add.c"
    assert len(result.declarations) == 2
    assert result.signature == "int add(int, int)"
    assert result.documentation == "Adds two integer values."


def test_builtin_has_no_fake_definition_but_can_have_source_declaration() -> None:
    source = 'int puts(char *text); int main(void) { return puts("ok"); }'
    project = analyze_project({"builtin.c": source})
    line, column = position(source, "puts", occurrence=1)
    result = goto_definition(project, "builtin.c", line, column)

    assert result is not None and result.is_builtin
    assert result.definition is None
    assert len(result.declarations) == 1


def test_single_file_api_remains_available() -> None:
    result = analyze_source("int main(void) { return 0; }", "single.c")

    assert not result.has_errors
    assert result.semantic.model.global_scope is not None


def test_two_project_analyses_do_not_share_state() -> None:
    first = analyze_project({"first.c": "int only_first;"})
    second = analyze_project({"second.c": "int only_second;"})

    first_names = {item.name for item in first.symbols}
    second_names = {item.name for item in second.symbols}
    assert "only_first" in first_names and "only_first" not in second_names
    assert "only_second" in second_names and "only_second" not in first_names
    assert first.symbols[0] is not second.symbols[0]


def test_project_index_output_is_deterministic_across_runs() -> None:
    first = analyze_project(FILES)
    second = analyze_project(FILES)

    assert first.render_index() == second.render_index()
    assert [item.id for item in first.symbols] == [item.id for item in second.symbols]

