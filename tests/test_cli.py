"""Tests for the Phase 0 command-line interface."""

import subprocess
import sys


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the installed module in a fresh Python process."""
    return subprocess.run(
        [sys.executable, "-m", "c_analyzer", *arguments],
        capture_output=True,
        check=False,
        text=True,
    )


def test_help_is_available() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "usage: c-analyzer" in result.stdout
    assert "--version" in result.stdout
    assert "Phase 0" in result.stdout
    assert result.stderr == ""


def test_version_is_available() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert result.stdout.strip() == "c-analyzer 0.1.0"
    assert result.stderr == ""

