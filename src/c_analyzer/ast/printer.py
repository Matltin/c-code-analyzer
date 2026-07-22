"""Deterministic, reflection-based AST printer."""

from dataclasses import fields
from enum import Enum

from c_analyzer.ast.nodes import ASTNode


class ASTPrinter:
    """Render AST structure without semantic or source-position noise."""

    _HIDDEN_FIELDS = {"span", "inferred_type", "symbol_id"}

    def print(self, node: ASTNode) -> str:
        lines: list[str] = []
        self._append_node(node, lines, 0)
        return "\n".join(lines)

    def _append_node(
        self,
        node: ASTNode,
        lines: list[str],
        indent: int,
    ) -> None:
        prefix = "  " * indent
        lines.append(f"{prefix}{type(node).__name__}")
        for item in fields(node):
            if item.name in self._HIDDEN_FIELDS:
                continue
            value = getattr(node, item.name)
            self._append_value(item.name, value, lines, indent + 1)

    def _append_value(
        self,
        label: str,
        value: object,
        lines: list[str],
        indent: int,
    ) -> None:
        prefix = "  " * indent
        if isinstance(value, ASTNode):
            lines.append(f"{prefix}{label}:")
            self._append_node(value, lines, indent + 1)
        elif isinstance(value, list):
            lines.append(f"{prefix}{label}:")
            if not value:
                lines.append(f"{prefix}  []")
            for index, child in enumerate(value):
                lines.append(f"{prefix}  [{index}]:")
                if isinstance(child, ASTNode):
                    self._append_node(child, lines, indent + 2)
                else:
                    lines.append(f"{prefix}    {child!r}")
        elif isinstance(value, Enum):
            lines.append(f"{prefix}{label}: {value.name}")
        else:
            lines.append(f"{prefix}{label}: {value!r}")


def print_ast(node: ASTNode) -> str:
    """Convenience function for deterministic AST rendering."""
    return ASTPrinter().print(node)

