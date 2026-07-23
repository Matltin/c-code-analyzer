"""Deterministic completion and hover over a Phase 2 semantic model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from c_analyzer.core import SourcePosition, SourceSpan, Token, TokenKind
from c_analyzer.semantic.symbols import (
    Scope,
    Symbol,
    SymbolKind,
    SymbolNamespace,
)
from c_analyzer.semantic.types import (
    ArrayType,
    CType,
    ERROR,
    FunctionType,
    PointerType,
    StructType,
    UNKNOWN,
    is_numeric,
    numeric_rank,
)

if TYPE_CHECKING:
    from c_analyzer.analysis import AnalysisResult

_TRIVIA_KINDS = frozenset(
    {
        TokenKind.LINE_COMMENT,
        TokenKind.BLOCK_COMMENT,
        TokenKind.PREPROCESSOR_DIRECTIVE,
    }
)


@dataclass(frozen=True, slots=True)
class CompletionItem:
    label: str
    kind: str
    detail: str
    sort_order: int
    insert_text: str
    symbol_id: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "label": self.label,
            "kind": self.kind,
            "detail": self.detail,
            "sort_order": self.sort_order,
            "insert_text": self.insert_text,
            "symbol_id": self.symbol_id,
        }


@dataclass(frozen=True, slots=True)
class DefinitionLocation:
    file: str
    line: int
    column: int

    def to_dict(self) -> dict[str, str | int]:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True, slots=True)
class HoverInfo:
    name: str
    kind: str
    type: str
    signature: str | None
    scope: str
    definition: DefinitionLocation | None
    is_builtin: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "type": self.type,
            "signature": self.signature,
            "scope": self.scope,
            "definition": (
                self.definition.to_dict() if self.definition is not None else "built-in"
            ),
            "is_builtin": self.is_builtin,
        }


def position_from_line_column(
    source: str,
    file_name: str,
    line: int,
    column: int,
) -> SourcePosition:
    """Convert a user-facing 1-based cursor to a validated source position."""
    if isinstance(line, bool) or not isinstance(line, int) or line < 1:
        raise ValueError("line must be a positive integer")
    if isinstance(column, bool) or not isinstance(column, int) or column < 1:
        raise ValueError("column must be a positive integer")

    starts = [0]
    starts.extend(index + 1 for index, char in enumerate(source) if char == "\n")
    if line > len(starts):
        raise ValueError(f"line {line} is outside the source")
    start = starts[line - 1]
    newline = source.find("\n", start)
    end = len(source) if newline < 0 else newline
    maximum = end - start + 1
    if column > maximum:
        raise ValueError(
            f"column {column} is outside line {line}; maximum is {maximum}"
        )
    return SourcePosition(
        file=file_name,
        line=line,
        column=column,
        offset=start + column - 1,
    )


def complete(
    analysis: AnalysisResult,
    line: int,
    column: int,
) -> tuple[CompletionItem, ...]:
    position = position_from_line_column(
        analysis.source_text,
        analysis.file_name,
        line,
        column,
    )
    engine = CompletionEngine(analysis)
    return engine.complete(position)


def hover(
    analysis: AnalysisResult,
    line: int,
    column: int,
) -> HoverInfo | None:
    position = position_from_line_column(
        analysis.source_text,
        analysis.file_name,
        line,
        column,
    )
    model = analysis.semantic.model
    symbol = _symbol_at(model.symbols, position.offset)
    if symbol is None and position.offset > 0:
        symbol = _symbol_at(model.symbols, position.offset - 1)
    if symbol is None:
        return None
    definition = None
    if symbol.definition_span is not None:
        start = symbol.definition_span.start
        definition = DefinitionLocation(
            file=start.file,
            line=start.line,
            column=start.column,
        )
    return HoverInfo(
        name=symbol.name,
        kind=symbol.kind.value,
        type=str(symbol.type),
        signature=symbol.signature,
        scope=symbol.scope_id,
        definition=definition,
        is_builtin=symbol.kind is SymbolKind.BUILTIN_FUNCTION,
    )


def _symbol_at(symbols: tuple[Symbol, ...], offset: int) -> Symbol | None:
    for symbol in symbols:
        if symbol.definition_span is not None and _span_has_offset(
            symbol.definition_span,
            offset,
        ):
            return symbol
        for reference in symbol.references:
            if _span_has_offset(reference.span, offset):
                return symbol
    return None


def _span_has_offset(span: SourceSpan, offset: int) -> bool:
    return span.start.offset <= offset < span.end.offset


class CompletionEngine:
    def __init__(self, analysis: AnalysisResult) -> None:
        self._analysis = analysis
        self._model = analysis.semantic.model
        self._tokens = tuple(
            token
            for token in analysis.lexer.tokens
            if token.kind not in _TRIVIA_KINDS and token.kind is not TokenKind.EOF
        )

    def complete(self, position: SourcePosition) -> tuple[CompletionItem, ...]:
        member = self._member_context(position)
        if member is not None:
            operator, receiver, prefix = member
            return self._member_items(position, operator, receiver, prefix)

        prefix = _identifier_prefix(self._analysis.source_text, position.offset)
        expected = self._expected_argument_type(position)
        scope = self._model.scope_at(position)
        symbols = self._visible_symbols(scope, position.offset)
        return self._rank_symbols(symbols, prefix, scope, expected)

    def _member_context(
        self,
        position: SourcePosition,
    ) -> tuple[TokenKind, Token, str] | None:
        relevant = [
            token for token in self._tokens if token.span.start.offset < position.offset
        ]
        if not relevant:
            return None
        prefix = _identifier_prefix(self._analysis.source_text, position.offset)
        index = len(relevant) - 1
        if (
            relevant[index].kind is TokenKind.IDENTIFIER
            and relevant[index].span.end.offset == position.offset
            and prefix
        ):
            index -= 1
        if index < 1 or relevant[index].kind not in {
            TokenKind.DOT,
            TokenKind.ARROW,
        }:
            return None
        receiver = relevant[index - 1]
        if receiver.kind is not TokenKind.IDENTIFIER:
            return None
        return relevant[index].kind, receiver, prefix

    def _member_items(
        self,
        position: SourcePosition,
        operator: TokenKind,
        receiver: Token,
        prefix: str,
    ) -> tuple[CompletionItem, ...]:
        scope = self._model.scope_at(position)
        symbol = scope.lookup(
            receiver.lexeme,
            offset=receiver.span.start.offset,
        )
        if symbol is None:
            return ()
        type_ = symbol.type
        if operator is TokenKind.DOT:
            struct_type = type_ if isinstance(type_, StructType) else None
        else:
            struct_type = (
                type_.pointee
                if isinstance(type_, PointerType)
                and isinstance(type_.pointee, StructType)
                else None
            )
        if struct_type is None:
            return ()
        tag = scope.lookup(struct_type.name, SymbolNamespace.TAG)
        if tag is None:
            return ()
        struct_scope = self._model.symbol_table.struct_scopes.get(tag.id)
        if struct_scope is None:
            return ()
        fields = tuple(struct_scope.symbols[SymbolNamespace.FIELD].values())
        return self._rank_symbols(fields, prefix, struct_scope, None)

    def _expected_argument_type(self, position: SourcePosition) -> CType | None:
        relevant = [
            token for token in self._tokens if token.span.start.offset < position.offset
        ]
        depth = 0
        opening_index: int | None = None
        for index in range(len(relevant) - 1, -1, -1):
            token = relevant[index]
            if token.kind is TokenKind.RIGHT_PAREN:
                depth += 1
            elif token.kind is TokenKind.LEFT_PAREN:
                if depth == 0:
                    opening_index = index
                    break
                depth -= 1
        if opening_index is None or opening_index == 0:
            return None
        callee = relevant[opening_index - 1]
        if callee.kind is not TokenKind.IDENTIFIER:
            return None
        scope = self._model.scope_at(position)
        symbol = scope.lookup(callee.lexeme, offset=callee.span.start.offset)
        if symbol is None or not isinstance(symbol.type, FunctionType):
            return None

        argument_index = 0
        nested = 0
        for token in relevant[opening_index + 1 :]:
            if token.kind in {TokenKind.LEFT_PAREN, TokenKind.LEFT_BRACKET}:
                nested += 1
            elif token.kind in {TokenKind.RIGHT_PAREN, TokenKind.RIGHT_BRACKET}:
                nested = max(0, nested - 1)
            elif token.kind is TokenKind.COMMA and nested == 0:
                argument_index += 1
        if argument_index >= len(symbol.type.parameter_types):
            return None
        return symbol.type.parameter_types[argument_index]

    def _visible_symbols(self, scope: Scope, offset: int) -> tuple[Symbol, ...]:
        visible: list[Symbol] = []
        seen: set[str] = set()
        current: Scope | None = scope
        while current is not None:
            for symbol in current.symbols[SymbolNamespace.ORDINARY].values():
                if symbol.name in seen or symbol.visible_from > offset:
                    continue
                seen.add(symbol.name)
                visible.append(symbol)
            current = current.parent
        for symbol in self._model.global_scope.symbols[SymbolNamespace.TAG].values():
            if symbol.name not in seen:
                seen.add(symbol.name)
                visible.append(symbol)
        return tuple(visible)

    def _rank_symbols(
        self,
        symbols: tuple[Symbol, ...],
        prefix: str,
        cursor_scope: Scope,
        expected_type: CType | None,
    ) -> tuple[CompletionItem, ...]:
        items: list[CompletionItem] = []
        for symbol in symbols:
            match_rank = _match_rank(prefix, symbol.name)
            if match_rank is None:
                continue
            compatibility = (
                0
                if expected_type is not None
                and _type_compatible(expected_type, symbol.type)
                else 1
                if expected_type is not None
                else 0
            )
            distance = _scope_distance(cursor_scope, symbol.scope_id)
            kind_rank = list(SymbolKind).index(symbol.kind)
            sort_order = (
                match_rank * 10_000
                + compatibility * 1_000
                + distance * 10
                + kind_rank
            )
            items.append(
                CompletionItem(
                    label=symbol.name,
                    kind=symbol.kind.value,
                    detail=symbol.signature or str(symbol.type),
                    sort_order=sort_order,
                    insert_text=symbol.name,
                    symbol_id=symbol.id,
                )
            )
        return tuple(
            sorted(
                items,
                key=lambda item: (
                    item.sort_order,
                    item.label,
                    item.kind,
                    item.symbol_id,
                ),
            )
        )


def _identifier_prefix(source: str, offset: int) -> str:
    start = offset
    while start > 0:
        char = source[start - 1]
        if not (char.isascii() and (char.isalnum() or char == "_")):
            break
        start -= 1
    return source[start:offset]


def _match_rank(prefix: str, label: str) -> int | None:
    if not prefix:
        return 0
    prefix_lower = prefix.lower()
    label_lower = label.lower()
    if label_lower.startswith(prefix_lower):
        return 0
    iterator = iter(label_lower)
    if all(any(char == candidate for candidate in iterator) for char in prefix_lower):
        return 1
    return None


def _scope_distance(cursor_scope: Scope, target_scope_id: str) -> int:
    distance = 0
    current: Scope | None = cursor_scope
    while current is not None:
        if current.id == target_scope_id:
            return distance
        distance += 1
        current = current.parent
    return distance + 100


def _type_compatible(expected: CType, actual: CType) -> bool:
    if expected == actual:
        return True
    if expected in {ERROR, UNKNOWN} or actual in {ERROR, UNKNOWN}:
        return False
    if is_numeric(expected) and is_numeric(actual):
        return numeric_rank(actual) <= numeric_rank(expected)
    if isinstance(expected, PointerType) and isinstance(actual, ArrayType):
        return expected.pointee == actual.element_type
    return False
