"""Recursive-descent parser with panic-mode recovery."""

from dataclasses import dataclass

from c_analyzer.ast import (
    AssignmentExpr,
    BinaryExpr,
    BlockStmt,
    BreakStmt,
    CallExpr,
    CharLiteral,
    ContinueStmt,
    Declaration,
    EmptyStmt,
    ErrorExpr,
    ErrorStmt,
    Expression,
    ExprStmt,
    FieldDecl,
    FloatLiteral,
    ForStmt,
    FunctionDecl,
    FunctionPrototype,
    IdentifierExpr,
    IfStmt,
    IndexExpr,
    InitializerList,
    IntegerLiteral,
    MemberExpr,
    Name,
    Parameter,
    Program,
    ReturnStmt,
    Statement,
    StringLiteral,
    StructDecl,
    TypeRef,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from c_analyzer.core import (
    Diagnostic,
    DiagnosticPhase,
    Severity,
    SourcePosition,
    SourceSpan,
    Token,
    TokenKind,
)
from c_analyzer.lexer import TYPE_KEYWORDS


TRIVIA_KINDS = frozenset(
    {
        TokenKind.LINE_COMMENT,
        TokenKind.BLOCK_COMMENT,
        TokenKind.PREPROCESSOR_DIRECTIVE,
    }
)

ASSIGNMENT_OPERATORS = frozenset(
    {
        TokenKind.ASSIGN,
        TokenKind.PLUS_ASSIGN,
        TokenKind.MINUS_ASSIGN,
        TokenKind.STAR_ASSIGN,
        TokenKind.SLASH_ASSIGN,
        TokenKind.PERCENT_ASSIGN,
    }
)

PREFIX_OPERATORS = frozenset(
    {
        TokenKind.PLUS,
        TokenKind.MINUS,
        TokenKind.LOGICAL_NOT,
        TokenKind.AMPERSAND,
        TokenKind.STAR,
        TokenKind.INCREMENT,
        TokenKind.DECREMENT,
    }
)

SYNC_KINDS = frozenset(
    {
        TokenKind.SEMICOLON,
        TokenKind.RIGHT_BRACE,
        TokenKind.KW_IF,
        TokenKind.KW_WHILE,
        TokenKind.KW_FOR,
        TokenKind.KW_RETURN,
        TokenKind.KW_BREAK,
        TokenKind.KW_CONTINUE,
    }
)


class _ParseError(Exception):
    """Internal control-flow exception after a reported syntax error."""


@dataclass(frozen=True, slots=True)
class ParserResult:
    """Partial AST and every syntax diagnostic produced by parsing."""

    ast: Program
    diagnostics: tuple[Diagnostic, ...]


class Parser:
    """Parse a token sequence according to ``grammar/c_subset.ebnf``."""

    def __init__(self, tokens: tuple[Token, ...] | list[Token]) -> None:
        if not tokens:
            raise ValueError("tokens must include at least EOF")
        if tokens[-1].kind is not TokenKind.EOF:
            raise ValueError("tokens must end with EOF")

        self._all_tokens = tuple(tokens)
        self._tokens = tuple(token for token in tokens if token.kind not in TRIVIA_KINDS)
        self._current = 0
        self._diagnostics: list[Diagnostic] = []

    def parse(self) -> ParserResult:
        """Parse all external declarations and return a partial AST on errors."""
        declarations: list[Declaration] = []
        program_start = self._all_tokens[0].span.start

        while not self._at_end():
            start_index = self._current
            try:
                declarations.append(self._parse_external_declaration())
            except _ParseError:
                self._synchronize()

            if self._current == start_index and not self._at_end():
                self._advance()

        program_end = self._peek().span.end
        program = Program(
            span=SourceSpan(start=program_start, end=program_end),
            declarations=declarations,
        )
        return ParserResult(ast=program, diagnostics=tuple(self._diagnostics))

    def _parse_external_declaration(self) -> Declaration:
        if (
            self._check(TokenKind.KW_STRUCT)
            and self._check_next(TokenKind.IDENTIFIER)
            and self._check_at(2, TokenKind.LEFT_BRACE)
        ):
            return self._parse_struct_declaration()

        start = self._peek().span.start
        type_ref = self._parse_type_ref()
        name = self._expect_name("expected a declaration name")

        if self._match(TokenKind.LEFT_PAREN):
            parameters = self._parse_parameter_list()
            closing = self._expect_soft(
                TokenKind.RIGHT_PAREN,
                "expected ')' after parameter list",
            )
            if self._match(TokenKind.SEMICOLON):
                return FunctionPrototype(
                    span=self._span(start, self._previous().span.end),
                    return_type=type_ref,
                    name=name,
                    parameters=parameters,
                )
            if self._match(TokenKind.LEFT_BRACE):
                body = self._parse_block(self._previous())
                return FunctionDecl(
                    span=self._span(start, body.span.end),
                    return_type=type_ref,
                    name=name,
                    parameters=parameters,
                    body=body,
                )
            self._report(self._peek(), "expected ';' or function body")
            raise _ParseError

        return self._finish_variable_declaration(start, type_ref, name)

    def _parse_struct_declaration(self) -> StructDecl:
        start_token = self._expect(TokenKind.KW_STRUCT, "expected 'struct'")
        name = self._expect_name("expected struct name")
        self._expect(TokenKind.LEFT_BRACE, "expected '{' after struct name")
        fields: list[FieldDecl] = []

        while not self._check(TokenKind.RIGHT_BRACE) and not self._at_end():
            field_start = self._peek().span.start
            start_index = self._current
            try:
                type_ref = self._parse_type_ref()
                field_name = self._expect_name("expected field name")
                array_size = self._parse_optional_array_suffix()
                semicolon = self._expect_soft(
                    TokenKind.SEMICOLON,
                    "expected ';' after field declaration",
                )
                fields.append(
                    FieldDecl(
                        span=self._span(field_start, semicolon.span.end),
                        type_ref=type_ref,
                        name=field_name,
                        array_size=array_size,
                    )
                )
            except _ParseError:
                self._synchronize()
            if (
                self._current == start_index
                and not self._at_end()
                and not self._check(TokenKind.RIGHT_BRACE)
            ):
                self._advance()

        closing = self._expect_soft(
            TokenKind.RIGHT_BRACE,
            "expected '}' after struct fields",
        )
        semicolon = self._expect_soft(
            TokenKind.SEMICOLON,
            "expected ';' after struct declaration",
        )
        return StructDecl(
            span=self._span(start_token.span.start, semicolon.span.end),
            name=name,
            fields=fields,
        )

    def _parse_type_ref(self) -> TypeRef:
        if self._peek().kind not in TYPE_KEYWORDS:
            self._report(self._peek(), "expected type name")
            raise _ParseError

        type_token = self._advance()
        struct_name: Name | None = None
        end = type_token.span.end

        if type_token.kind is TokenKind.KW_STRUCT:
            struct_name = self._expect_name("expected name after 'struct'")
            end = struct_name.span.end

        pointer_span: SourceSpan | None = None
        if self._match(TokenKind.STAR):
            pointer_span = self._previous().span
            end = pointer_span.end

        return TypeRef(
            span=self._span(type_token.span.start, end),
            keyword=type_token.lexeme,
            struct_name=struct_name,
            is_pointer=pointer_span is not None,
            pointer_span=pointer_span,
        )

    def _parse_parameter_list(self) -> list[Parameter]:
        if self._check(TokenKind.RIGHT_PAREN):
            return []
        if self._check(TokenKind.KW_VOID) and (
            self._check_next(TokenKind.RIGHT_PAREN)
            or self._check_next(TokenKind.LEFT_BRACE)
        ):
            self._advance()
            return []

        parameters = [self._parse_parameter()]
        while self._match(TokenKind.COMMA):
            parameters.append(self._parse_parameter())
        return parameters

    def _parse_parameter(self) -> Parameter:
        start = self._peek().span.start
        type_ref = self._parse_type_ref()
        name = self._expect_name("expected parameter name")
        is_array = False
        end = name.span.end
        if self._match(TokenKind.LEFT_BRACKET):
            is_array = True
            closing = self._expect_soft(
                TokenKind.RIGHT_BRACKET,
                "expected ']' after array parameter",
            )
            end = closing.span.end
        return Parameter(
            span=self._span(start, end),
            type_ref=type_ref,
            name=name,
            is_array=is_array,
        )

    def _finish_variable_declaration(
        self,
        start: SourcePosition,
        type_ref: TypeRef,
        name: Name,
    ) -> VarDecl:
        array_size = self._parse_optional_array_suffix()
        initializer: Expression | None = None
        if self._match(TokenKind.ASSIGN):
            initializer = self._parse_initializer()

        semicolon = self._expect_soft(
            TokenKind.SEMICOLON,
            "expected ';' after variable declaration",
        )
        return VarDecl(
            span=self._span(start, semicolon.span.end),
            type_ref=type_ref,
            name=name,
            array_size=array_size,
            initializer=initializer,
        )

    def _parse_optional_array_suffix(self) -> Expression | None:
        if not self._match(TokenKind.LEFT_BRACKET):
            return None

        if self._match(TokenKind.INTEGER_LITERAL):
            size: Expression = IntegerLiteral(
                span=self._previous().span,
                lexeme=self._previous().lexeme,
            )
        else:
            token = self._peek()
            self._report(token, "expected integer array size")
            size = ErrorExpr(span=token.span, message="missing array size")
            if token.kind not in {TokenKind.RIGHT_BRACKET, TokenKind.EOF}:
                self._advance()

        self._expect_soft(
            TokenKind.RIGHT_BRACKET,
            "expected ']' after array size",
        )
        return size

    def _parse_initializer(self) -> Expression:
        if not self._match(TokenKind.LEFT_BRACE):
            return self._parse_assignment()

        opening = self._previous()
        values: list[Expression] = []
        if not self._check(TokenKind.RIGHT_BRACE):
            values.append(self._parse_assignment())
            while self._match(TokenKind.COMMA):
                if self._check(TokenKind.RIGHT_BRACE):
                    break
                values.append(self._parse_assignment())

        closing = self._expect_soft(
            TokenKind.RIGHT_BRACE,
            "expected '}' after initializer list",
        )
        return InitializerList(
            span=self._span(opening.span.start, closing.span.end),
            values=values,
        )

    def _parse_block(self, opening: Token) -> BlockStmt:
        items: list[Declaration | Statement] = []
        while not self._check(TokenKind.RIGHT_BRACE) and not self._at_end():
            start_index = self._current
            try:
                if self._peek().kind in TYPE_KEYWORDS:
                    start = self._peek().span.start
                    type_ref = self._parse_type_ref()
                    name = self._expect_name("expected variable name")
                    items.append(
                        self._finish_variable_declaration(start, type_ref, name)
                    )
                else:
                    items.append(self._parse_statement())
            except _ParseError:
                error_token = self._peek()
                items.append(
                    ErrorStmt(
                        span=error_token.span,
                        message="recovered statement",
                    )
                )
                self._synchronize()

            if (
                self._current == start_index
                and not self._at_end()
                and not self._check(TokenKind.RIGHT_BRACE)
            ):
                self._advance()

        closing = self._expect_soft(
            TokenKind.RIGHT_BRACE,
            "expected '}' after block",
        )
        return BlockStmt(
            span=self._span(opening.span.start, closing.span.end),
            items=items,
        )

    def _parse_statement(self) -> Statement:
        if self._match(TokenKind.LEFT_BRACE):
            return self._parse_block(self._previous())
        if self._match(TokenKind.SEMICOLON):
            return EmptyStmt(span=self._previous().span)
        if self._match(TokenKind.KW_IF):
            return self._parse_if(self._previous())
        if self._match(TokenKind.KW_WHILE):
            return self._parse_while(self._previous())
        if self._match(TokenKind.KW_FOR):
            return self._parse_for(self._previous())
        if self._match(TokenKind.KW_RETURN):
            return self._parse_return(self._previous())
        if self._match(TokenKind.KW_BREAK):
            return self._parse_jump(self._previous(), is_break=True)
        if self._match(TokenKind.KW_CONTINUE):
            return self._parse_jump(self._previous(), is_break=False)

        start = self._peek().span.start
        expression = self._parse_expression()
        semicolon = self._expect_soft(
            TokenKind.SEMICOLON,
            "expected ';' after expression",
        )
        return ExprStmt(
            span=self._span(start, semicolon.span.end),
            expression=expression,
        )

    def _parse_if(self, keyword: Token) -> IfStmt:
        self._expect_soft(TokenKind.LEFT_PAREN, "expected '(' after 'if'")
        condition = self._parse_expression()
        self._expect_soft(TokenKind.RIGHT_PAREN, "expected ')' after condition")
        then_branch = self._parse_statement()
        else_branch = None
        end = then_branch.span.end
        if self._match(TokenKind.KW_ELSE):
            else_branch = self._parse_statement()
            end = else_branch.span.end
        return IfStmt(
            span=self._span(keyword.span.start, end),
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
        )

    def _parse_while(self, keyword: Token) -> WhileStmt:
        self._expect_soft(TokenKind.LEFT_PAREN, "expected '(' after 'while'")
        condition = self._parse_expression()
        self._expect_soft(TokenKind.RIGHT_PAREN, "expected ')' after condition")
        body = self._parse_statement()
        return WhileStmt(
            span=self._span(keyword.span.start, body.span.end),
            condition=condition,
            body=body,
        )

    def _parse_for(self, keyword: Token) -> ForStmt:
        self._expect_soft(TokenKind.LEFT_PAREN, "expected '(' after 'for'")
        initializer: Declaration | Expression | None

        if self._peek().kind in TYPE_KEYWORDS:
            start = self._peek().span.start
            type_ref = self._parse_type_ref()
            name = self._expect_name("expected variable name")
            initializer = self._finish_variable_declaration(start, type_ref, name)
        elif self._match(TokenKind.SEMICOLON):
            initializer = None
        else:
            initializer = self._parse_expression()
            self._expect_soft(
                TokenKind.SEMICOLON,
                "expected ';' after for initializer",
            )

        condition = None
        if not self._check(TokenKind.SEMICOLON):
            condition = self._parse_expression()
        self._expect_soft(
            TokenKind.SEMICOLON,
            "expected ';' after for condition",
        )

        update = None
        if not self._check(TokenKind.RIGHT_PAREN):
            update = self._parse_expression()
        self._expect_soft(TokenKind.RIGHT_PAREN, "expected ')' after for clauses")
        body = self._parse_statement()
        return ForStmt(
            span=self._span(keyword.span.start, body.span.end),
            initializer=initializer,
            condition=condition,
            update=update,
            body=body,
        )

    def _parse_return(self, keyword: Token) -> ReturnStmt:
        value = None
        if not self._check(TokenKind.SEMICOLON):
            value = self._parse_expression()
        semicolon = self._expect_soft(
            TokenKind.SEMICOLON,
            "expected ';' after return",
        )
        return ReturnStmt(
            span=self._span(keyword.span.start, semicolon.span.end),
            value=value,
        )

    def _parse_jump(self, keyword: Token, *, is_break: bool) -> Statement:
        semicolon = self._expect_soft(
            TokenKind.SEMICOLON,
            "expected ';' after jump statement",
        )
        span = self._span(keyword.span.start, semicolon.span.end)
        if is_break:
            return BreakStmt(span=span)
        return ContinueStmt(span=span)

    def _parse_expression(self) -> Expression:
        return self._parse_assignment()

    def _parse_assignment(self) -> Expression:
        target = self._parse_logical_or()
        if self._peek().kind not in ASSIGNMENT_OPERATORS:
            return target

        operator = self._advance()
        value = self._parse_assignment()
        return AssignmentExpr(
            span=self._span(target.span.start, value.span.end),
            target=target,
            operator=operator.kind,
            operator_span=operator.span,
            value=value,
        )

    def _parse_logical_or(self) -> Expression:
        return self._parse_left_associative(
            self._parse_logical_and,
            {TokenKind.LOGICAL_OR},
        )

    def _parse_logical_and(self) -> Expression:
        return self._parse_left_associative(
            self._parse_equality,
            {TokenKind.LOGICAL_AND},
        )

    def _parse_equality(self) -> Expression:
        return self._parse_left_associative(
            self._parse_relational,
            {TokenKind.EQUAL_EQUAL, TokenKind.BANG_EQUAL},
        )

    def _parse_relational(self) -> Expression:
        return self._parse_left_associative(
            self._parse_additive,
            {
                TokenKind.LESS,
                TokenKind.LESS_EQUAL,
                TokenKind.GREATER,
                TokenKind.GREATER_EQUAL,
            },
        )

    def _parse_additive(self) -> Expression:
        return self._parse_left_associative(
            self._parse_multiplicative,
            {TokenKind.PLUS, TokenKind.MINUS},
        )

    def _parse_multiplicative(self) -> Expression:
        return self._parse_left_associative(
            self._parse_unary,
            {TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT},
        )

    def _parse_left_associative(
        self,
        operand_parser: object,
        operators: set[TokenKind],
    ) -> Expression:
        parse_operand = operand_parser
        expression = parse_operand()  # type: ignore[operator]
        while self._peek().kind in operators:
            operator = self._advance()
            right = parse_operand()  # type: ignore[operator]
            expression = BinaryExpr(
                span=self._span(expression.span.start, right.span.end),
                left=expression,
                operator=operator.kind,
                operator_span=operator.span,
                right=right,
            )
        return expression

    def _parse_unary(self) -> Expression:
        if self._peek().kind in PREFIX_OPERATORS:
            operator = self._advance()
            operand = self._parse_unary()
            return UnaryExpr(
                span=self._span(operator.span.start, operand.span.end),
                operator=operator.kind,
                operator_span=operator.span,
                operand=operand,
            )
        return self._parse_postfix()

    def _parse_postfix(self) -> Expression:
        expression = self._parse_primary()
        while True:
            if self._match(TokenKind.LEFT_PAREN):
                arguments: list[Expression] = []
                if not self._check(TokenKind.RIGHT_PAREN):
                    arguments.append(self._parse_assignment())
                    while self._match(TokenKind.COMMA):
                        arguments.append(self._parse_assignment())
                closing = self._expect_soft(
                    TokenKind.RIGHT_PAREN,
                    "expected ')' after arguments",
                )
                expression = CallExpr(
                    span=self._span(expression.span.start, closing.span.end),
                    callee=expression,
                    arguments=arguments,
                )
            elif self._match(TokenKind.LEFT_BRACKET):
                index = self._parse_expression()
                closing = self._expect_soft(
                    TokenKind.RIGHT_BRACKET,
                    "expected ']' after index",
                )
                expression = IndexExpr(
                    span=self._span(expression.span.start, closing.span.end),
                    target=expression,
                    index=index,
                )
            elif self._match(TokenKind.DOT, TokenKind.ARROW):
                operator = self._previous()
                member = self._expect_name_soft("expected member name")
                expression = MemberExpr(
                    span=self._span(expression.span.start, member.span.end),
                    target=expression,
                    operator=operator.kind,
                    operator_span=operator.span,
                    member=member,
                )
            elif self._match(TokenKind.INCREMENT, TokenKind.DECREMENT):
                operator = self._previous()
                expression = UnaryExpr(
                    span=self._span(expression.span.start, operator.span.end),
                    operator=operator.kind,
                    operator_span=operator.span,
                    operand=expression,
                    is_postfix=True,
                )
            else:
                break
        return expression

    def _parse_primary(self) -> Expression:
        if self._match(TokenKind.IDENTIFIER):
            token = self._previous()
            return IdentifierExpr(
                span=token.span,
                name=Name(span=token.span, text=token.lexeme),
            )
        if self._match(TokenKind.INTEGER_LITERAL):
            token = self._previous()
            return IntegerLiteral(span=token.span, lexeme=token.lexeme)
        if self._match(TokenKind.FLOAT_LITERAL):
            token = self._previous()
            return FloatLiteral(span=token.span, lexeme=token.lexeme)
        if self._match(TokenKind.STRING_LITERAL):
            token = self._previous()
            return StringLiteral(span=token.span, lexeme=token.lexeme)
        if self._match(TokenKind.CHAR_LITERAL):
            token = self._previous()
            return CharLiteral(span=token.span, lexeme=token.lexeme)
        if self._match(TokenKind.LEFT_PAREN):
            expression = self._parse_expression()
            self._expect_soft(
                TokenKind.RIGHT_PAREN,
                "expected ')' after expression",
            )
            return expression
        if self._match(TokenKind.INVALID):
            token = self._previous()
            self._report(token, "invalid token in expression")
            return ErrorExpr(span=token.span, message="invalid token")

        token = self._peek()
        self._report(token, "expected expression")
        if token.kind not in {
            TokenKind.SEMICOLON,
            TokenKind.RIGHT_PAREN,
            TokenKind.RIGHT_BRACKET,
            TokenKind.RIGHT_BRACE,
            TokenKind.COMMA,
            TokenKind.EOF,
        }:
            self._advance()
        return ErrorExpr(span=token.span, message="missing expression")

    def _expect_name(self, message: str) -> Name:
        if not self._check(TokenKind.IDENTIFIER):
            self._report(self._peek(), message)
            raise _ParseError
        token = self._advance()
        return Name(span=token.span, text=token.lexeme)

    def _expect_name_soft(self, message: str) -> Name:
        if self._check(TokenKind.IDENTIFIER):
            token = self._advance()
            return Name(span=token.span, text=token.lexeme)
        token = self._peek()
        self._report(token, message)
        return Name(span=self._zero_span(token.span.start), text="<error>")

    def _expect(self, kind: TokenKind, message: str) -> Token:
        if self._check(kind):
            return self._advance()
        self._report(self._peek(), message)
        raise _ParseError

    def _expect_soft(self, kind: TokenKind, message: str) -> Token:
        if self._check(kind):
            return self._advance()
        token = self._peek()
        self._report(token, message)
        return Token(kind=kind, lexeme="", span=self._zero_span(token.span.start))

    def _report(self, token: Token, message: str) -> None:
        self._diagnostics.append(
            Diagnostic(
                phase=DiagnosticPhase.PARSER,
                severity=Severity.ERROR,
                message=message,
                span=token.span,
            )
        )

    def _synchronize(self) -> None:
        while not self._at_end():
            if self._peek().kind is TokenKind.SEMICOLON:
                self._advance()
                return
            if self._peek().kind in SYNC_KINDS:
                return
            self._advance()

    def _match(self, *kinds: TokenKind) -> bool:
        if self._peek().kind in kinds:
            self._advance()
            return True
        return False

    def _check(self, kind: TokenKind) -> bool:
        return self._peek().kind is kind

    def _check_next(self, kind: TokenKind) -> bool:
        return self._check_at(1, kind)

    def _check_at(self, distance: int, kind: TokenKind) -> bool:
        index = min(self._current + distance, len(self._tokens) - 1)
        return self._tokens[index].kind is kind

    def _advance(self) -> Token:
        token = self._peek()
        if not self._at_end():
            self._current += 1
        return token

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _at_end(self) -> bool:
        return self._peek().kind is TokenKind.EOF

    @staticmethod
    def _span(start: SourcePosition, end: SourcePosition) -> SourceSpan:
        return SourceSpan(start=start, end=end)

    @staticmethod
    def _zero_span(position: SourcePosition) -> SourceSpan:
        return SourceSpan(start=position, end=position)


def parse(tokens: tuple[Token, ...] | list[Token]) -> ParserResult:
    """Convenience API for parsing a complete EOF-terminated token stream."""
    return Parser(tokens).parse()
