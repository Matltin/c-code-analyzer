"""Command-line interface for the Phase 1 and Phase 2 analysis pipeline."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from c_analyzer import __version__
from c_analyzer.analysis import analyze_source, diagnostics_to_json
from c_analyzer.ast import FunctionDecl, print_ast
from c_analyzer.callgraph import (
    build_call_graph,
    callgraph_to_dot,
    callgraph_to_json,
    callgraph_to_text,
)
from c_analyzer.core import Severity
from c_analyzer.flow import (
    analyze_dataflow,
    build_cfg,
    cfg_to_dot,
    cfg_to_json,
    cfg_to_text,
    render_dead_code,
)
from c_analyzer.lexer import LexerResult, tokenize
from c_analyzer.parser import ParserResult, parse
from c_analyzer.project import (
    find_references,
    goto_definition,
    load_project_directory,
)
from c_analyzer.refactor import atomic_apply, plan_rename
from c_analyzer.rendering import render_ansi, render_html
from c_analyzer.semantic import complete, hover


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="c-analyzer",
        description=(
            "Analyze a documented subset of C. "
            "Phase 0 core, Phase 1 front-end, Phase 2 semantic tools, "
            "and Phase 3 project analysis are available."
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

    project_parser = subparsers.add_parser(
        "project-check",
        help="analyze every .c file in a project",
    )
    project_parser.add_argument("project_dir", type=Path)
    project_parser.add_argument("--json", action="store_true")

    goto_parser = subparsers.add_parser(
        "goto-def",
        help="find the definition at a project source position",
    )
    goto_parser.add_argument("file", type=Path)
    goto_parser.add_argument("line", type=int)
    goto_parser.add_argument("column", type=int)
    goto_parser.add_argument("--project", required=True, type=Path)
    goto_parser.add_argument("--json", action="store_true")

    refs_parser = subparsers.add_parser(
        "find-refs",
        help="find all references to the symbol at a position",
    )
    refs_parser.add_argument("file", type=Path)
    refs_parser.add_argument("line", type=int)
    refs_parser.add_argument("column", type=int)
    refs_parser.add_argument("--project", required=True, type=Path)
    refs_parser.add_argument("--json", action="store_true")

    cfg_parser = subparsers.add_parser(
        "show-cfg",
        help="show a function control-flow graph",
    )
    cfg_parser.add_argument("file", type=Path)
    cfg_parser.add_argument("function")
    cfg_parser.add_argument("--project", required=True, type=Path)
    cfg_parser.add_argument(
        "--format",
        choices=("text", "json", "dot"),
        default="text",
    )

    callgraph_parser = subparsers.add_parser(
        "callgraph",
        help="show the project call graph",
    )
    callgraph_parser.add_argument("project_dir", type=Path)
    callgraph_parser.add_argument("--entry", default="main")
    callgraph_parser.add_argument(
        "--format",
        choices=("text", "json", "dot"),
        default="text",
    )

    dead_parser = subparsers.add_parser(
        "dead-code",
        help="report unreachable code, dead assignments, and dead functions",
    )
    dead_parser.add_argument("project_dir", type=Path)
    dead_parser.add_argument("--entry", default="main")
    dead_parser.add_argument("--json", action="store_true")

    rename_parser = subparsers.add_parser(
        "rename",
        help="preview or atomically apply a scope-aware rename",
    )
    rename_parser.add_argument("file", type=Path)
    rename_parser.add_argument("line", type=int)
    rename_parser.add_argument("column", type=int)
    rename_parser.add_argument("new_name")
    rename_parser.add_argument("--project", required=True, type=Path)
    rename_parser.add_argument("--apply", action="store_true")
    rename_parser.add_argument("--json", action="store_true")

    repl_parser = subparsers.add_parser(
        "repl",
        help="start the Phase 3 project-analysis REPL",
    )
    repl_parser.add_argument("project_dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_help()
        return 0

    phase3_commands = {
        "project-check",
        "goto-def",
        "find-refs",
        "show-cfg",
        "callgraph",
        "dead-code",
        "rename",
        "repl",
    }
    if arguments.command in phase3_commands:
        try:
            return _run_phase3(arguments)
        except (OSError, UnicodeError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

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


def _run_phase3(arguments) -> int:
    if arguments.command == "repl":
        from c_analyzer.repl import run_repl

        return run_repl(arguments.project_dir)

    root = (
        arguments.project_dir
        if hasattr(arguments, "project_dir")
        else arguments.project
    )
    project = _load_project(root)

    if arguments.command == "project-check":
        if arguments.json:
            print(
                json.dumps(
                    {
                        "root": project.root,
                        "files": [item.path for item in project.files],
                        "symbols": [
                            {
                                "id": item.id,
                                "name": item.name,
                                "kind": item.kind.value,
                            }
                            for item in project.symbols
                        ],
                        "diagnostics": [
                            item.to_dict() for item in project.diagnostics
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(project.render_index())
            if project.diagnostics:
                print("diagnostics:")
                for diagnostic in project.diagnostics:
                    print(f"  {diagnostic}")
            else:
                print("No diagnostics.")
        return 1 if project.has_errors else 0

    if arguments.command == "goto-def":
        file = _relative_project_file(arguments.file, root)
        result = goto_definition(
            project,
            file,
            arguments.line,
            arguments.column,
        )
        if arguments.json:
            print(
                json.dumps(
                    {"definition": result.to_dict() if result else None},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif result is None:
            print("No symbol.")
        else:
            print(f"symbol: {result.symbol}")
            print(f"kind: {result.kind}")
            print(f"type: {result.type}")
            if result.definition is None:
                print("definition: built-in" if result.is_builtin else "definition: none")
            else:
                item = result.definition
                print(f"definition: {item.file}:{item.line}:{item.column}")
            for item in result.declarations:
                print(f"declaration: {item.file}:{item.line}:{item.column}")
        return 0

    if arguments.command == "find-refs":
        file = _relative_project_file(arguments.file, root)
        references = find_references(
            project,
            file,
            arguments.line,
            arguments.column,
        )
        if arguments.json:
            print(
                json.dumps(
                    {"references": [item.to_dict() for item in references]},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif not references:
            print("No references.")
        else:
            for item in references:
                location = item.location
                access = (
                    "definition"
                    if item.is_definition
                    else item.access_kind.value
                    if item.access_kind is not None
                    else "declaration"
                )
                print(
                    f"{location.file}:{location.line}:{location.column}: "
                    f"{access} length={location.length}"
                )
        return 0

    if arguments.command == "show-cfg":
        file = _relative_project_file(arguments.file, root)
        project_file = project.file(file)
        if project_file is None:
            raise ValueError(f"file is not part of project: {file}")
        function = next(
            (
                item
                for item in project_file.analysis.parser.ast.declarations
                if isinstance(item, FunctionDecl)
                and item.name.text == arguments.function
            ),
            None,
        )
        if function is None:
            raise ValueError(
                f"function definition not found: {arguments.function}"
            )
        local = project_file.analysis.semantic.model.symbol_of(function.name)
        if local is None:
            raise ValueError("function has no resolved symbol")
        symbol_id = project.local_to_project.get((file, local.id), local.id)
        cfg = build_cfg(function, symbol_id)
        print(
            cfg_to_json(cfg)
            if arguments.format == "json"
            else cfg_to_dot(cfg)
            if arguments.format == "dot"
            else cfg_to_text(cfg)
        )
        return 0

    if arguments.command == "callgraph":
        graph = build_call_graph(project)
        if graph.symbol_id(arguments.entry) is None:
            print(
                f"error: entry function not found: {arguments.entry}",
                file=sys.stderr,
            )
            if arguments.format != "json":
                print(callgraph_to_text(graph, entry=arguments.entry))
            else:
                print(callgraph_to_json(graph, entry=arguments.entry))
            return 1
        print(
            callgraph_to_json(graph, entry=arguments.entry)
            if arguments.format == "json"
            else callgraph_to_dot(graph)
            if arguments.format == "dot"
            else callgraph_to_text(graph, entry=arguments.entry)
        )
        return 0

    if arguments.command == "dead-code":
        payload = _project_dead_code(project, arguments.entry)
        if arguments.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for function in payload["functions"]:
                print(f"Function {function['file']}::{function['name']}")
                for line in function["report"].splitlines():
                    print(f"  {line}")
            print("dead_functions:")
            for item in payload["dead_functions"]:
                print(f"  {item['id']} {item['name']}")
            if not payload["entry_found"]:
                print(f"entry not found: {arguments.entry}")
        return 0 if payload["entry_found"] else 1

    if arguments.command == "rename":
        file = _relative_project_file(arguments.file, root)
        result = plan_rename(
            project,
            file,
            arguments.line,
            arguments.column,
            arguments.new_name,
        )
        if not result.ok:
            if arguments.json:
                print(
                    json.dumps(
                        {"ok": False, "errors": list(result.errors)},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                for error in result.errors:
                    print(f"error: {error}", file=sys.stderr)
            return 1
        if arguments.apply:
            atomic_apply(root, result)
        if arguments.json:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "applied": arguments.apply,
                        "symbol_id": result.symbol_id,
                        "old_name": result.old_name,
                        "new_name": result.new_name,
                        "edits": [
                            {
                                "file": item.file,
                                "start_offset": item.start_offset,
                                "end_offset": item.end_offset,
                                "replacement": item.replacement,
                            }
                            for item in result.edits
                        ],
                        "diff": result.diff,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(result.diff, end="" if result.diff.endswith("\n") else "\n")
            print("Applied atomically." if arguments.apply else "Preview only; no files changed.")
        return 0
    raise ValueError(f"unknown Phase 3 command: {arguments.command}")


def _load_project(root: Path):
    if not root.is_dir():
        raise ValueError(f"project directory does not exist: {root}")
    project = load_project_directory(root)
    if not project.files:
        raise ValueError(f"project contains no .c files: {root}")
    return project


def _relative_project_file(file: Path, root: Path) -> str:
    root_resolved = root.resolve()
    if file.is_absolute():
        try:
            return file.resolve().relative_to(root_resolved).as_posix()
        except ValueError as error:
            raise ValueError(f"file is outside project: {file}") from error
    candidate = file.resolve()
    try:
        return candidate.relative_to(root_resolved).as_posix()
    except ValueError:
        return file.as_posix()


def _project_dead_code(project, entry: str) -> dict[str, object]:
    functions: list[dict[str, object]] = []
    for file in project.files:
        for function in file.analysis.parser.ast.declarations:
            if not isinstance(function, FunctionDecl):
                continue
            local = file.analysis.semantic.model.symbol_of(function.name)
            if local is None:
                continue
            symbol_id = project.local_to_project.get((file.path, local.id), local.id)
            cfg = build_cfg(function, symbol_id)
            result = analyze_dataflow(
                function,
                file.analysis.semantic.model,
                cfg,
            )
            functions.append(
                {
                    "file": file.path,
                    "name": function.name.text,
                    "report": render_dead_code(result.dead_code),
                    "unreachable_blocks": list(
                        result.dead_code.unreachable_blocks
                    ),
                    "dead_assignments": [
                        finding.message
                        for finding in result.dead_code.dead_assignments
                    ],
                    "missing_returns": [
                        finding.message
                        for finding in result.dead_code.missing_returns
                    ],
                }
            )
    graph = build_call_graph(project)
    return {
        "entry": entry,
        "entry_found": graph.symbol_id(entry) is not None,
        "functions": functions,
        "dead_functions": [
            {"id": node.symbol_id, "name": node.name}
            for node in graph.dead_functions(entry)
        ],
    }


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
