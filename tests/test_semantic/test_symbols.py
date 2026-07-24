"""Tests for Phase 2.1 scope and symbol-table construction."""

from c_analyzer import SourcePosition
from c_analyzer.lexer import tokenize
from c_analyzer.parser import parse
from c_analyzer.semantic import (
    FunctionType,
    PointerType,
    ScopeKind,
    SymbolKind,
    SymbolNamespace,
    build_symbol_table,
)


def build(source: str):
    tokens = tokenize(source, "symbols.c").tokens
    program = parse(tokens).ast
    return build_symbol_table(program)


SOURCE = """
struct Point { int x; int y; };
int global = 1;
int add(int value) {
    int result = value;
    {
        int global = result;
        result = global;
    }
    return result;
}
"""


def test_builds_global_function_block_and_struct_scopes() -> None:
    result = build(SOURCE)
    kinds = [scope.kind for scope in result.scopes]

    assert kinds.count(ScopeKind.GLOBAL) == 1
    assert kinds.count(ScopeKind.FUNCTION) == 1
    assert kinds.count(ScopeKind.BLOCK) == 2
    assert kinds.count(ScopeKind.STRUCT) == 1


def test_scope_parent_child_relationships_are_bidirectional() -> None:
    result = build(SOURCE)

    for scope in result.scopes[1:]:
        assert scope.parent is not None
        assert scope in scope.parent.children


def test_lookup_walks_from_inner_scope_to_outer_scope() -> None:
    result = build(SOURCE)
    function_scope = next(
        scope for scope in result.scopes if scope.kind is ScopeKind.FUNCTION
    )
    body_scope = function_scope.children[0]

    assert body_scope.lookup("value").kind is SymbolKind.PARAMETER
    assert body_scope.lookup("add").kind is SymbolKind.FUNCTION


def test_inner_declaration_shadows_outer_declaration_in_lookup() -> None:
    result = build(SOURCE)
    blocks = [scope for scope in result.scopes if scope.kind is ScopeKind.BLOCK]
    outer, inner = blocks

    assert outer.lookup("global").scope_id == result.global_scope.id
    assert inner.lookup("global").scope_id == inner.id


def test_struct_tags_use_a_separate_namespace() -> None:
    result = build("struct Item { int value; }; int Item;")
    ordinary = result.global_scope.lookup_local("Item")
    tag = result.global_scope.lookup_local("Item", SymbolNamespace.TAG)

    assert ordinary is not None and ordinary.kind is SymbolKind.VARIABLE
    assert tag is not None and tag.kind is SymbolKind.STRUCT
    assert ordinary.id != tag.id


def test_fields_are_only_in_the_struct_field_namespace() -> None:
    result = build("struct Item { int value; };")
    struct_scope = next(
        scope for scope in result.scopes if scope.kind is ScopeKind.STRUCT
    )

    assert struct_scope.lookup_local("value") is None
    field = struct_scope.lookup_local("value", SymbolNamespace.FIELD)
    assert field is not None and field.kind is SymbolKind.FIELD
    assert result.global_scope.lookup("value") is None


def test_builtin_registry_has_explicit_signatures_without_fake_spans() -> None:
    result = build("int main(void) { return 0; }")
    printf = result.global_scope.lookup("printf")
    puts = result.global_scope.lookup("puts")

    assert printf is not None and printf.kind is SymbolKind.BUILTIN_FUNCTION
    assert puts is not None and puts.kind is SymbolKind.BUILTIN_FUNCTION
    assert isinstance(printf.type, FunctionType) and printf.type.variadic
    assert isinstance(puts.type.parameter_types[0], PointerType)
    assert printf.definition_span is None
    assert puts.definition_span is None


def test_compatible_builtin_prototype_reuses_builtin_symbol() -> None:
    result = build("int puts(char *text);")
    puts = result.global_scope.lookup("puts")

    assert not result.diagnostics
    assert puts is not None and puts.kind is SymbolKind.BUILTIN_FUNCTION
    prototype_binding = next(
        symbol
        for symbol in result.definition_bindings.values()
        if symbol.name == "puts"
    )
    assert prototype_binding.id == puts.id


def test_conflicting_builtin_prototype_is_diagnosed() -> None:
    result = build("int puts(int text);")

    assert any("conflicting declaration" in item.message for item in result.diagnostics)


def test_scope_tree_and_ids_are_deterministic_across_analyses() -> None:
    first = build(SOURCE)
    second = build(SOURCE)

    assert first.render() == second.render()
    assert [scope.id for scope in first.scopes] == [scope.id for scope in second.scopes]
    assert [symbol.id for symbol in first.symbols] == [
        symbol.id for symbol in second.symbols
    ]


def test_scope_at_returns_the_innermost_scope() -> None:
    result = build(SOURCE)
    offset = SOURCE.index("result = global")
    prefix = SOURCE[:offset]
    position = SourcePosition(
        file="symbols.c",
        line=prefix.count("\n") + 1,
        column=offset - prefix.rfind("\n"),
        offset=offset,
    )
    scope = result.scope_at(position)

    assert scope.kind is ScopeKind.BLOCK
    assert scope.lookup_local("global") is not None


def test_each_build_is_isolated_from_previous_mutation() -> None:
    first = build(SOURCE)
    first.global_scope.symbols[SymbolNamespace.ORDINARY].pop("printf")
    second = build(SOURCE)

    assert second.global_scope.lookup("printf") is not None

