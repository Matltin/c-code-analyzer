"""Structural tests for CI, Pages, coverage, and the static-site builder."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).parents[2]
CI = ROOT / ".github/workflows/ci.yml"
PAGES = ROOT / ".github/workflows/pages.yml"


def test_coverage_gate_is_at_least_eighty_percent() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["tool"]["coverage"]["run"]["branch"] is True
    assert config["tool"]["coverage"]["report"]["fail_under"] >= 80
    assert "pytest-cov>=6.0" in config["project"]["optional-dependencies"]["dev"]
    assert any(
        dependency.startswith("tomli>=2.0;")
        for dependency in config["project"]["optional-dependencies"]["dev"]
    )


def test_ci_workflow_has_required_triggers_matrix_and_checks() -> None:
    text = CI.read_text(encoding="utf-8")

    for expected in (
        "push:",
        "pull_request:",
        "workflow_dispatch:",
        'python-version: ["3.10", "3.12"]',
        "python -m compileall -q src",
        "python -m pytest -q",
        "make coverage PY=python",
        "make highlight-html PY=python",
    ):
        assert expected in text


def test_ci_workflow_uses_current_actions_and_uploads_artifacts() -> None:
    text = CI.read_text(encoding="utf-8")

    assert "actions/checkout@v6" in text
    assert "actions/setup-python@v6" in text
    assert text.count("actions/upload-artifact@v6") == 2
    assert "coverage.xml" in text
    assert "htmlcov" in text
    assert "output/highlight.html" in text


def test_workflows_use_minimal_permissions_and_no_embedded_secrets() -> None:
    combined = CI.read_text(encoding="utf-8") + PAGES.read_text(encoding="utf-8")

    assert "contents: read" in combined
    assert "pages: write" in combined
    assert "id-token: write" in combined
    for forbidden in ("PASSWORD=", "TOKEN=", "API_KEY=", "BEGIN PRIVATE KEY"):
        assert forbidden not in combined


def test_pages_workflow_builds_and_deploys_site_from_main() -> None:
    text = PAGES.read_text(encoding="utf-8")

    for expected in (
        "branches: [main]",
        "workflow_dispatch:",
        "group: pages",
        "cancel-in-progress: true",
        "make site PY=python",
        "actions/configure-pages@v5",
        "actions/upload-pages-artifact@v4",
        "actions/deploy-pages@v4",
        "path: site",
    ):
        assert expected in text


def test_site_builder_creates_valid_internal_targets(tmp_path: Path) -> None:
    coverage = tmp_path / "htmlcov"
    output = tmp_path / "site"
    readme = tmp_path / "README.md"
    coverage.mkdir()
    output.mkdir()
    (coverage / "index.html").write_text("<h1>Coverage</h1>", encoding="utf-8")
    (coverage / "asset.css").write_text("body{}", encoding="utf-8")
    (output / "highlight.html").write_text("<h1>Highlight</h1>", encoding="utf-8")
    readme.write_text("# Demo\n<script>alert(1)</script>", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_site.py"),
            "--output",
            str(output),
            "--coverage",
            str(coverage),
            "--readme",
            str(readme),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    index = (output / "index.html").read_text(encoding="utf-8")
    for target in ("highlight.html", "coverage/index.html", "readme.html"):
        assert f"href='{target}'" in index
        assert output.joinpath(*target.split("/")).is_file()
    readme_html = (output / "readme.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;" in readme_html
    assert "<script>" not in readme_html


def test_makefile_has_bonus_site_and_gate_targets() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "coverage:",
        "bonus-coverage:",
        "docker-build:",
        "docker-test:",
        "site:",
        "site-serve:",
        "infrastructure-check:",
        "bonus-gate:",
    ):
        assert target in text


def test_bonus_documents_exist_and_advanced_features_remain_out_of_scope() -> None:
    for relative in (
        "docs/coverage.md",
        "docs/docker.md",
        "docs/ci_cd.md",
        "docs/github_pages.md",
        "docs/bonus.md",
    ):
        assert ROOT.joinpath(relative).read_text(encoding="utf-8").strip()

    checklist = (ROOT / "PROJECT_CHECKLIST.md").read_text(encoding="utf-8")
    assert "### [?] B1" in checklist
    assert "### [?] B2" in checklist
    assert "### [?] B3" in checklist
    assert "### [?] GitHub Pages" in checklist
    assert "### [ ] Bonusهای پیشرفته" in checklist
