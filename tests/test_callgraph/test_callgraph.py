"""Phase 3.4 project call-graph query and output tests."""

import json

from c_analyzer.callgraph import (
    build_call_graph,
    callgraph_to_dot,
    callgraph_to_json,
    callgraph_to_text,
)
from c_analyzer.project import analyze_project


def graph(files):
    return build_call_graph(analyze_project(files))


def names(nodes):
    return tuple(node.name for node in nodes)


def test_direct_callee_and_caller_queries() -> None:
    result = graph(
        {"main.c": "int helper(void) { return 1; } "
         "int main(void) { return helper(); }"}
    )

    assert names(result.direct_callees("main")) == ("helper",)
    assert names(result.direct_callers("helper")) == ("main",)


def test_cross_file_call_uses_shared_project_symbol() -> None:
    result = graph(
        {
            "main.c": "int add(int a, int b); "
            "int main(void) { return add(1, 2); }",
            "math.c": "int add(int a, int b) { return a + b; }",
        }
    )

    assert names(result.direct_callees("main")) == ("add",)
    assert result.direct_callees("main")[0].kind == "defined"


def test_transitive_reachability_and_reverse_reachability() -> None:
    result = graph(
        {"all.c": "int c(void) { return 0; } "
         "int b(void) { return c(); } "
         "int a(void) { return b(); } "
         "int main(void) { return a(); }"}
    )

    assert set(names(result.reachable_callees("main"))) == {"a", "b", "c"}
    assert set(names(result.reaching_callers("c"))) == {"main", "a", "b"}


def test_direct_recursion_is_an_scc() -> None:
    result = graph(
        {"recursive.c": "int down(int n) { "
         "if (n) return down(n - 1); return 0; }"}
    )
    down = result.symbol_id("down")

    assert down is not None
    assert (down,) in result.recursive_components()


def test_mutual_recursion_forms_one_component() -> None:
    result = graph(
        {"mutual.c": "int odd(int n); "
         "int even(int n) { if (n) return odd(n - 1); return 1; } "
         "int odd(int n) { if (n) return even(n - 1); return 0; }"}
    )
    even = result.symbol_id("even")
    odd = result.symbol_id("odd")

    assert even is not None and odd is not None
    assert tuple(sorted((even, odd))) in result.recursive_components()


def test_dead_function_is_unreachable_from_main() -> None:
    result = graph(
        {"dead.c": "int unused(void) { return 0; } "
         "int main(void) { return 0; }"}
    )

    assert names(result.dead_functions()) == ("unused",)


def test_builtin_call_is_a_separate_non_dead_node() -> None:
    result = graph(
        {"builtin.c": 'int main(void) { puts("hello"); return 0; }'}
    )
    puts = result.direct_callees("main")[0]

    assert puts.name == "puts"
    assert puts.kind == "builtin"
    assert puts not in result.dead_functions()


def test_prototype_without_definition_is_external() -> None:
    result = graph(
        {"external.c": "int remote(int x); "
         "int main(void) { return remote(1); }"}
    )

    remote = result.direct_callees("main")[0]
    assert remote.name == "remote"
    assert remote.kind == "external"


def test_custom_entry_controls_dead_function_query() -> None:
    result = graph(
        {"custom.c": "int helper(void) { return 0; } "
         "int start(void) { return helper(); } "
         "int main(void) { return 0; }"}
    )

    assert "helper" not in names(result.dead_functions("start"))
    assert "main" in names(result.dead_functions("start"))


def test_missing_entry_has_controlled_empty_result() -> None:
    result = graph({"library.c": "int helper(void) { return 0; }"})
    payload = result.to_dict(entry="missing")

    assert payload["entry_found"] is False
    assert result.dead_functions("missing") == ()


def test_duplicate_call_sites_are_grouped_on_one_edge() -> None:
    result = graph(
        {"calls.c": "int f(void) { return 1; } "
         "int main(void) { int x = f(); return x + f(); }"}
    )

    edge = next(
        edge
        for edge in result.edges
        if result.node(edge.callee_symbol_id).name == "f"
    )
    assert len(edge.call_sites) == 2


def test_ordering_and_outputs_are_stable_and_valid() -> None:
    files = {
        "z.c": "int z(void) { return 0; }",
        "a.c": "int z(void); int main(void) { return z(); }",
    }
    first = graph(files)
    second = graph(dict(reversed(tuple(files.items()))))

    assert first == second
    assert callgraph_to_text(first) == callgraph_to_text(second)
    assert json.loads(callgraph_to_json(first))["entry_found"] is True
    dot = callgraph_to_dot(first)
    assert dot.startswith("digraph callgraph {")
    assert "->" in dot

