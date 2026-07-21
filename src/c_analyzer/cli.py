"""Command-line interface for the Phase 0 project scaffold."""

import argparse
from collections.abc import Sequence

from c_analyzer import __version__


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="c-analyzer",
        description=(
            "Analyze a documented subset of C. "
            "Phase 0 currently provides project setup and core models only."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="show the program version and exit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    parser.parse_args(argv)
    return 0

