"""Static B2 checks that complement, but never replace, real Docker runs."""

from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_dockerfile_has_builder_test_and_runtime_stages() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim AS base" in text
    assert "AS builder" in text
    assert "AS test" in text
    assert "AS runtime" in text
    assert "pip install --no-cache-dir" in text


def test_runtime_uses_non_root_user_and_cli_entrypoint() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime = text.split("FROM base AS runtime", maxsplit=1)[1]

    assert "USER analyzer" in runtime
    assert 'ENTRYPOINT ["c-analyzer"]' in runtime
    assert 'CMD ["--help"]' in runtime
    assert runtime.index("USER analyzer") < runtime.index("ENTRYPOINT")


def test_test_dependencies_are_not_installed_in_runtime_stage() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime = text.split("FROM base AS runtime", maxsplit=1)[1]

    assert "[dev]" not in runtime
    assert "pytest" not in runtime


def test_dockerignore_excludes_generated_and_sensitive_context() -> None:
    entries = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    required = {
        ".git",
        ".venv",
        "**/__pycache__",
        ".pytest_cache",
        "htmlcov",
        "coverage.xml",
        "site",
        "output",
        "*.zip",
        ".idea",
        ".vscode",
    }

    assert required <= entries


def test_makefile_exposes_all_required_docker_targets() -> None:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")

    for target in (
        "docker-build:",
        "docker-help:",
        "docker-test:",
        "docker-smoke:",
        "bonus-docker:",
    ):
        assert target in text


def test_docker_compose_is_intentionally_absent_and_docs_exist() -> None:
    assert not (ROOT / "docker-compose.yml").exists()
    assert not (ROOT / "docker-compose.yaml").exists()
    assert (ROOT / "docs/docker.md").read_text(encoding="utf-8").strip()
