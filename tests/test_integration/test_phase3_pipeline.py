"""End-to-end Phase 3 project pipeline and resilience tests."""

from c_analyzer.ast import FunctionDecl
from c_analyzer.callgraph import build_call_graph, callgraph_to_text
from c_analyzer.flow import analyze_dataflow, build_cfg, cfg_to_text
from c_analyzer.project import analyze_project, goto_definition
from c_analyzer.refactor import plan_rename


FILES = {
    "main.c": """\
int add(int left, int right);
int main(void) {
    int total = add(1, 2);
    return total;
}
""",
    "lib/add.c": """\
int add(int left, int right) {
    return left + right;
}
""",
}


def position(source: str, text: str, occurrence: int = 0) -> tuple[int, int]:
    offset = -1
    start = 0
    for _ in range(occurrence + 1):
        offset = source.index(text, start)
        start = offset + 1
    prefix = source[:offset]
    return prefix.count("\n") + 1, offset - prefix.rfind("\n")


def test_full_project_to_rename_and_reanalysis_pipeline() -> None:
    project = analyze_project(FILES, root="demo")
    main_file = project.file("main.c")
    assert main_file is not None
    function = next(
        item
        for item in main_file.analysis.parser.ast.declarations
        if isinstance(item, FunctionDecl)
    )
    local = main_file.analysis.semantic.model.symbol_of(function.name)
    assert local is not None
    cfg = build_cfg(
        function,
        project.local_to_project[("main.c", local.id)],
    )
    flow = analyze_dataflow(function, main_file.analysis.semantic.model, cfg)
    graph = build_call_graph(project)
    call_line, call_column = position(FILES["main.c"], "add", 1)
    definition = goto_definition(
        project,
        "main.c",
        call_line,
        call_column,
    )
    rename_line, rename_column = position(FILES["main.c"], "total")
    rename = plan_rename(
        project,
        "main.c",
        rename_line,
        rename_column,
        "result",
    )

    assert definition is not None
    assert definition.definition.file == "lib/add.c"
    assert cfg.reachable_blocks()
    assert flow.liveness_iterations > 0
    assert tuple(node.name for node in graph.direct_callees("main")) == ("add",)
    assert rename.ok and "result" in rename.sources["main.c"]
    assert not analyze_project(rename.sources).has_errors


def test_valid_project_has_no_error_diagnostics() -> None:
    assert not analyze_project(FILES).has_errors


def test_syntax_semantic_and_multiple_errors_are_controlled() -> None:
    syntax = analyze_project({"syntax.c": "int main( { return 0; }"})
    semantic = analyze_project(
        {"semantic.c": "int main(void) { return missing; }"}
    )
    multiple = analyze_project(
        {
            "a.c": "int duplicate(void) { return missing; }",
            "b.c": "int duplicate(void) { return 0; } @",
        }
    )

    assert syntax.has_errors
    assert semantic.has_errors
    assert multiple.has_errors
    assert len(multiple.diagnostics) >= 3


def test_repeated_analysis_has_no_state_leak_and_stable_outputs() -> None:
    first = analyze_project(FILES)
    analyze_project({"other.c": "int other(void) { return 0; }"})
    second = analyze_project(dict(reversed(tuple(FILES.items()))))
    first_graph = build_call_graph(first)
    second_graph = build_call_graph(second)

    assert first.render_index() == second.render_index()
    assert callgraph_to_text(first_graph) == callgraph_to_text(second_graph)
    assert [symbol.id for symbol in first.symbols] == [
        symbol.id for symbol in second.symbols
    ]


def test_cfg_output_is_stable_across_independent_projects() -> None:
    outputs = []
    for _ in range(2):
        project = analyze_project(FILES)
        file = project.file("main.c")
        function = next(
            item
            for item in file.analysis.parser.ast.declarations
            if isinstance(item, FunctionDecl)
        )
        local = file.analysis.semantic.model.symbol_of(function.name)
        outputs.append(
            cfg_to_text(
                build_cfg(
                    function,
                    project.local_to_project[("main.c", local.id)],
                )
            )
        )
    assert outputs[0] == outputs[1]


def test_windows_style_mapping_paths_are_normalized_for_ubuntu_output() -> None:
    project = analyze_project(
        {
            "src\\main.c": "int main(void) { return 0; }",
            "./lib\\helper.c": "int helper(void) { return 0; }",
        }
    )

    assert [file.path for file in project.files] == [
        "lib/helper.c",
        "src/main.c",
    ]

