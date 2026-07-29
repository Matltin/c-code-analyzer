"""Phase 3 documentation, example, and checklist gate tests."""

from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_required_phase_three_documents_exist_and_are_nonempty() -> None:
    required = (
        "README.md",
        "PROJECT_CHECKLIST.md",
        "docs/architecture.md",
        "docs/algorithms.md",
        "docs/limitations.md",
        "docs/usage.md",
        "docs/project_analysis.md",
        "docs/navigation.md",
        "docs/cfg.md",
        "docs/dataflow.md",
        "docs/callgraph.md",
        "docs/refactoring.md",
        "docs/repl.md",
    )
    for relative in required:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert text.strip(), relative


def test_example_project_has_exact_required_files_and_features() -> None:
    project = ROOT / "examples/project"
    assert sorted(path.name for path in project.glob("*.c")) == [
        "main.c",
        "math_utils.c",
        "structs.c",
        "unused.c",
    ]
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in project.glob("*.c")
    )
    for feature in (
        "int main(",
        "int add(",
        "factorial(",
        "struct Point",
        "unused_helper",
        "discarded = 10",
        "return factorial(total)",
    ):
        assert feature in combined


def test_checklist_uses_user_review_state_and_bonus_is_unstarted() -> None:
    text = (ROOT / "PROJECT_CHECKLIST.md").read_text(encoding="utf-8")

    for section in ("3.1", "3.2", "3.3", "3.4", "3.5"):
        assert f"### [?] {section}" in text
    assert "### [?] Phase Gate 3" in text
    assert "### [ ] خارج از Scope" in text
    assert "### [x] Phase Gate 2" in text

