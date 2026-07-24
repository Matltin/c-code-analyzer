"""Structural checks for the documented EBNF grammar."""

from pathlib import Path


GRAMMAR = Path("grammar/c_subset.ebnf")


def test_grammar_contains_required_nonterminals() -> None:
    text = GRAMMAR.read_text(encoding="utf-8")
    required = {
        "translation_unit",
        "function_definition",
        "function_prototype",
        "struct_definition",
        "variable_declaration",
        "initializer_list",
        "if_statement",
        "while_statement",
        "for_statement",
        "assignment_expression",
        "logical_or_expression",
        "logical_and_expression",
        "equality_expression",
        "relational_expression",
        "additive_expression",
        "multiplicative_expression",
        "unary_expression",
        "postfix_expression",
        "primary_expression",
    }

    for nonterminal in required:
        assert f"{nonterminal}" in text


def test_grammar_documents_right_associative_assignment() -> None:
    text = GRAMMAR.read_text(encoding="utf-8")

    assert '"=" | "+=" | "-=" | "*=" | "/=" | "%="' in text
    assert "assignment_operator, assignment_expression" in text


def test_grammar_excludes_out_of_scope_features() -> None:
    text = GRAMMAR.read_text(encoding="utf-8")

    for forbidden in ["switch_statement", "goto_statement", "union_definition"]:
        assert forbidden not in text

