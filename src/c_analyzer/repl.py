"""Injectable, crash-resistant Phase 3 command REPL."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import shlex
import sys

_HELP = """Commands:
  help
  project-check
  goto-def FILE LINE COLUMN
  find-refs FILE LINE COLUMN
  show-cfg FILE FUNCTION
  callgraph
  dead-code
  rename FILE LINE COLUMN NEW_NAME
  quit | exit
"""


def run_repl(
    project_dir: Path,
    *,
    input_stream=None,
    output_stream=None,
) -> int:
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    print("c-analyzer Phase 3 REPL. Type 'help' for commands.", file=output_stream)
    while True:
        print("c-analyzer> ", end="", file=output_stream, flush=True)
        line = input_stream.readline()
        if line == "":
            print("", file=output_stream)
            return 0
        try:
            parts = shlex.split(line)
        except ValueError as error:
            print(f"error: {error}", file=output_stream)
            continue
        if not parts:
            continue
        command, *arguments = parts
        if command in {"quit", "exit"}:
            return 0
        if command == "help":
            print(_HELP, end="", file=output_stream)
            continue
        argv = _translate(command, arguments, project_dir)
        if argv is None:
            print(f"error: unknown or invalid command: {command}", file=output_stream)
            continue
        from c_analyzer.cli import main

        captured = StringIO()
        with redirect_stdout(captured), redirect_stderr(captured):
            try:
                main(argv)
            except Exception as error:
                print(f"error: {error}", file=captured)
        print(captured.getvalue(), end="", file=output_stream)


def _translate(
    command: str,
    arguments: list[str],
    project_dir: Path,
) -> list[str] | None:
    root = str(project_dir)
    if command == "project-check" and not arguments:
        return ["project-check", root]
    if command in {"goto-def", "find-refs"} and len(arguments) == 3:
        return [command, *arguments, "--project", root]
    if command == "show-cfg" and len(arguments) == 2:
        return [command, *arguments, "--project", root]
    if command == "callgraph" and not arguments:
        return ["callgraph", root]
    if command == "dead-code" and not arguments:
        return ["dead-code", root]
    if command == "rename" and len(arguments) == 4:
        return [command, *arguments, "--project", root]
    return None
