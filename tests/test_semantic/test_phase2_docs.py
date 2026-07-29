"""Documentation and checklist regression for the completed Phase 2 work."""

from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_required_phase_two_documents_exist_and_are_nonempty() -> None:
    required = (
        "docs/semantic_analysis.md",
        "docs/type_system.md",
        "docs/intellisense.md",
        "docs/diagnostics.md",
        "docs/architecture.md",
        "docs/algorithms.md",
        "docs/limitations.md",
        "docs/usage.md",
    )

    for relative in required:
        path = ROOT / relative
        assert path.is_file()
        assert path.read_text(encoding="utf-8").strip()


def test_readme_lists_phase_two_commands() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "symbols examples/semantic/valid/scopes.c" in text
    assert "check examples/semantic/invalid/type_errors.c --json" in text
    assert "complete examples/semantic/valid/completion.c 11 27" in text
    assert "hover examples/semantic/valid/hover.c 6 18" in text


def test_checklist_matches_user_confirmation_boundaries() -> None:
    text = (ROOT / "PROJECT_CHECKLIST.md").read_text(encoding="utf-8")

    assert "### [x] Phase Gate 1" in text
    for section in ("2.1", "2.2", "2.3", "2.4", "2.5"):
        assert f"### [x] {section}" in text
    assert "### [x] Phase Gate 2" in text
    assert "### [?] 3.1" in text


def test_no_phase_three_package_was_created() -> None:
    package = ROOT / "src/c_analyzer"

    assert not (package / "cfg").exists()
    assert not (package / "call_graph").exists()
    assert not (package / "navigation").exists()
    assert not (package / "rename").exists()
