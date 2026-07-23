"""Command-line interface for the Phase 1 and Phase 2 analysis pipeline."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from c_analyzer import __version__
from c_analyzer.analysis import analyze_source, diagnostics_to_json
from c_analyzer.ast import print_ast
from c_analyzer.core import Severity
from c_analyzer.lexer import LexerResult, tokenize
from c_analyzer.parser import ParserResult, parse
from c_analyzer.rendering import render_ansi, render_html
from c_analyzer.semantic import complete, hover


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="c-analyzer",
        description=(
            "Analyze a documented subset of C. "
            "Phase 0 core, Phase 1 front-end, and Phase 2 semantic tools "
            "are available."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="show the program version and exit",
    )
    subparsers = parser.add_subparsers(dest="command")

    tokens_parser = subparsers.add_parser("tokens", help="print the token stream")
    tokens_parser.add_argument("file", type=Path)

    ast_parser = subparsers.add_parser("ast", help="print the parsed AST")
    ast_parser.add_argument("file", type=Path)

    check_parser = subparsers.add_parser("check", help="print diagnostics")
    check_parser.add_argument("file", type=Path)
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable diagnostics",
    )

    highlight_parser = subparsers.add_parser(
        "highlight",
        help="render syntax-highlighted source",
    )
    highlight_parser.add_argument("file", type=Path)
    highlight_parser.add_argument(
        "--format",
        choices=("ansi", "html"),
        default="ansi",
    )
    highlight_parser.add_argument("--output", type=Path)

    symbols_parser = subparsers.add_parser(
        "symbols",
        help="print the scope and symbol tree",
    )
    symbols_parser.add_argument("file", type=Path)

    complete_parser = subparsers.add_parser(
        "complete",
        help="suggest visible symbols at a cursor",
    )
    complete_parser.add_argument("file", type=Path)
    complete_parser.add_argument("line", type=int)
    complete_parser.add_argument("column", type=int)
    complete_parser.add_argument("--json", action="store_true")

    hover_parser = subparsers.add_parser(
        "hover",
        help="show symbol information at a cursor",
    )
    hover_parser.add_argument("file", type=Path)
    hover_parser.add_argument("line", type=int)
    hover_parser.add_argument("column", type=int)
    hover_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_help()
        return 0

    source = _read_source(arguments.file)
    if source is None:
        return 2

    file_name = str(arguments.file)
    lexer_result = tokenize(source, file_name)
    if arguments.command == "tokens":
        _print_tokens(lexer_result)
        return _error_exit_code(lexer_result, None)

    analysis_result = analyze_source(source, file_name)
    parser_result = analysis_result.parser
    if arguments.command == "ast":
        print(print_ast(parser_result.ast))
        _print_diagnostics(
            analysis_result.lexer,
            parser_result,
            stream=sys.stderr,
        )
        return _error_exit_code(analysis_result.lexer, parser_result)

    if arguments.command == "check":
        diagnostics = analysis_result.diagnostics
        if arguments.json:
            print(diagnostics_to_json(diagnostics))
            return 1 if analysis_result.has_errors else 0
        if not diagnostics:
            print("No diagnostics.")
            return 0
        for diagnostic in diagnostics:
            print(diagnostic)
        return (
            1
            if any(item.severity is Severity.ERROR for item in diagnostics)
            else 0
        )

    if arguments.command == "symbols":
        print(analysis_result.semantic.model.render_symbols())
        _print_all_diagnostics(analysis_result.diagnostics, stream=sys.stderr)
        return 1 if analysis_result.has_errors else 0

    if arguments.command == "complete":
        try:
            items = complete(analysis_result, arguments.line, arguments.column)
        except ValueError as error:
            print(f"error: invalid position: {error}", file=sys.stderr)
            return 2
        if arguments.json:
            print(
                json.dumps(
                    {"items": [item.to_dict() for item in items]},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif not items:
            print("No completions.")
        else:
            for item in items:
                print(f"{item.label:<20} {item.kind:<18} {item.detail}")
        return 0

    if arguments.command == "hover":
        try:
            information = hover(
                analysis_result,
                arguments.line,
                arguments.column,
            )
        except ValueError as error:
            print(f"error: invalid position: {error}", file=sys.stderr)
            return 2
        if arguments.json:
            print(
                json.dumps(
                    {
                        "hover": (
                            information.to_dict()
                            if information is not None
                            else None
                        )
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif information is None:
            print("No symbol.")
        else:
            definition = (
                "built-in"
                if information.definition is None
                else (
                    f"{information.definition.file}:"
                    f"{information.definition.line}:"
                    f"{information.definition.column}"
                )
            )
            print(f"name: {information.name}")
            print(f"kind: {information.kind}")
            print(f"type: {information.type}")
            print(f"signature: {information.signature or '-'}")
            print(f"scope: {information.scope}")
            print(f"definition: {definition}")
        return 0

    if arguments.command == "highlight":
        rendered = (
            render_ansi(
                source,
                analysis_result.lexer.tokens,
                parser_result.ast,
                analysis_result.semantic.model,
            )
            if arguments.format == "ansi"
            else render_html(
                source,
                analysis_result.lexer.tokens,
                parser_result.ast,
                analysis_result.semantic.model,
            )
        )
        if arguments.output is None:
            print(rendered, end="")
        else:
            try:
                arguments.output.write_text(rendered, encoding="utf-8")
            except OSError as error:
                print(f"error: cannot write {arguments.output}: {error}", file=sys.stderr)
                return 2
            print(f"Wrote {arguments.output}")
        _print_all_diagnostics(analysis_result.diagnostics, stream=sys.stderr)
        return 1 if analysis_result.has_errors else 0

    parser.error(f"unknown command: {arguments.command}")
    return 2


def _read_source(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"error: cannot read {path}: {error}", file=sys.stderr)
        return None


def _print_tokens(result: LexerResult) -> None:
    for token in result.tokens:
        start = token.span.start
        print(
            f"{token.kind.name:<24} "
            f"{token.lexeme!r:<24} "
            f"{start.line}:{start.column}"
        )
    for diagnostic in result.diagnostics:
        print(diagnostic, file=sys.stderr)


def _print_diagnostics(
    lexer_result: LexerResult,
    parser_result: ParserResult,
    *,
    stream: object,
) -> None:
    for diagnostic in (*lexer_result.diagnostics, *parser_result.diagnostics):
        print(diagnostic, file=stream)


def _print_all_diagnostics(
    diagnostics: tuple[object, ...] | list[object],
    *,
    stream: object,
) -> None:
    for diagnostic in diagnostics:
        print(diagnostic, file=stream)


def _error_exit_code(
    lexer_result: LexerResult,
    parser_result: ParserResult | None,
) -> int:
    if lexer_result.diagnostics:
        return 1
    if parser_result is not None and parser_result.diagnostics:
        return 1
    return 0
