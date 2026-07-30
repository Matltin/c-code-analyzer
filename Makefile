SHELL := /bin/bash

PYTHON ?= python3
VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(PY) -m pip
PYTEST := $(PY) -m pytest
COVERAGE_ARGS := --cov=src/c_analyzer --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80
DOCKER ?= docker
DOCKER_IMAGE ?= c-code-analyzer:bonus
DOCKER_TEST_IMAGE ?= c-code-analyzer:test

PROJECT_DIR ?= examples/project
MAIN_FILE ?= $(PROJECT_DIR)/main.c
MAIN_FUNCTION ?= main
GOTO_LINE ?= 6
GOTO_COLUMN ?= 17
RENAME_LINE ?= 6
RENAME_COLUMN ?= 9
RENAME_TO ?= result

.DEFAULT_GOAL := help

.PHONY: help doctor setup install check-venv compile collect-tests list-tests \
	test test-all test-verbose test-first-failure test-last-failed test-k \
	test-file test-node test-phase0 test-phase1 test-phase2 test-phase3 \
	test-core test-token-rules test-lexer test-ast test-parser test-rendering \
	test-semantic test-symbols test-resolution test-types test-diagnostics \
	test-intellisense test-project test-cfg test-dataflow test-callgraph \
	test-rename test-cli test-integration test-docs test-error-recovery \
	test-determinism test-rename-atomic test-json cli-help cli-version \
	coverage coverage-html coverage-report bonus-coverage \
	docker-check docker-build docker-help docker-test docker-smoke bonus-docker \
	site site-serve bonus-site bonus-gate infrastructure-check \
	tokens ast check-valid check-invalid check-json highlight-ansi \
	highlight-html symbols complete hover project-check project-check-json \
	goto-def goto-def-json find-refs find-refs-json cfg-text cfg-json cfg-dot \
	callgraph-text callgraph-json callgraph-dot dead-code dead-code-json \
	rename-preview rename-preview-json repl smoke gate0 gate1 gate2 gate3 \
	gate-all verify clean

help:
	@echo "c-code-analyzer — command and test targets"
	@echo
	@echo "Setup:"
	@echo "  make doctor              Check Python, Make, and project files"
	@echo "  make setup               Create .venv and install .[dev]"
	@echo "  make install             Reinstall project editable in existing .venv"
	@echo
	@echo "Main verification:"
	@echo "  make test                Run the complete automated test suite"
	@echo "  make verify              Compile, run all tests, and run smoke CLI checks"
	@echo "  make gate3               Run the complete Phase Gate 3"
	@echo "  make gate-all            Run Phase Gates 0 through 3"
	@echo "  make coverage            Run tests with branch coverage and 80% gate"
	@echo "  make docker-build        Build the non-root runtime image"
	@echo "  make docker-smoke        Run help, version, and project demo in Docker"
	@echo "  make docker-test         Run the test stage in Docker"
	@echo "  make site                Build the local GitHub Pages site"
	@echo "  make site-serve          Serve site/ at http://localhost:8000"
	@echo "  make bonus-gate          Run the complete infrastructure Bonus gate"
	@echo
	@echo "Phase tests:"
	@echo "  make test-phase0         Core models and initial CLI"
	@echo "  make test-phase1         Lexer, AST, Parser, rendering, Phase 1 CLI"
	@echo "  make test-phase2         Semantic, Phase 2 CLI, Phase 2 integration"
	@echo "  make test-phase3         Project, flow, call graph, rename, Phase 3 CLI"
	@echo
	@echo "Focused tests:"
	@echo "  make test-lexer          Lexer rules and scanner"
	@echo "  make test-parser         Parser and recovery"
	@echo "  make test-semantic       All semantic tests"
	@echo "  make test-project        Multi-file index and navigation"
	@echo "  make test-cfg            CFG builder and validator"
	@echo "  make test-dataflow       Definite assignment, liveness, dead code"
	@echo "  make test-callgraph      Call graph, reachability, SCC"
	@echo "  make test-rename         Safe rename and rollback"
	@echo "  make test-cli            Every CLI phase"
	@echo "  make test-integration    End-to-end pipelines"
	@echo
	@echo "Flexible pytest:"
	@echo "  make test-k K=rename"
	@echo "  make test-file FILE=tests/test_flow/test_cfg.py"
	@echo "  make test-node NODE=tests/test_flow/test_cfg.py::test_empty_function_connects_entry_directly_to_exit"
	@echo
	@echo "CLI demos:"
	@echo "  make tokens | ast | check-valid | check-invalid | check-json"
	@echo "  make highlight-ansi | highlight-html | symbols | complete | hover"
	@echo "  make project-check | goto-def | find-refs"
	@echo "  make cfg-text | cfg-json | cfg-dot"
	@echo "  make callgraph-text | callgraph-json | callgraph-dot"
	@echo "  make dead-code | rename-preview | repl"
	@echo
	@echo "Defaults can be overridden, e.g.:"
	@echo "  make cfg-text MAIN_FILE=examples/project/math_utils.c MAIN_FUNCTION=factorial"

doctor:
	@command -v "$(PYTHON)" >/dev/null || { echo "ERROR: $(PYTHON) not found"; exit 2; }
	@command -v make >/dev/null || { echo "ERROR: make not found"; exit 2; }
	@"$(PYTHON)" --version
	@make --version | head -n 1
	@"$(PYTHON)" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ is required"'
	@test -f pyproject.toml || { echo "ERROR: run make from the project root"; exit 2; }
	@echo "Project root and prerequisites look correct."

setup: doctor
	$(PYTHON) -m venv "$(VENV)"
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "Setup complete. Run: make test"

install: check-venv
	$(PIP) install -e ".[dev]"

check-venv:
	@test -x "$(PY)" || { echo "ERROR: $(PY) not found. Run 'make setup' first."; exit 2; }

compile: check-venv
	$(PY) -m compileall -q src

collect-tests: check-venv
	$(PYTEST) --collect-only -q

list-tests: collect-tests

test test-all: check-venv
	$(PYTEST) -q

test-verbose: check-venv
	$(PYTEST) -vv

test-first-failure: check-venv
	$(PYTEST) -q -x

test-last-failed: check-venv
	$(PYTEST) -q --lf

test-k: check-venv
	@test -n "$(K)" || { echo "ERROR: use make test-k K=word"; exit 2; }
	$(PYTEST) -q -k "$(K)"

test-file: check-venv
	@test -n "$(FILE)" || { echo "ERROR: use make test-file FILE=tests/path/test_file.py"; exit 2; }
	$(PYTEST) -q "$(FILE)"

test-node: check-venv
	@test -n "$(NODE)" || { echo "ERROR: use make test-node NODE=path::test_name"; exit 2; }
	$(PYTEST) -q "$(NODE)"

# Phase groups reflect the actual repository test layout.
test-phase0: check-venv
	$(PYTEST) -q tests/test_core tests/test_cli.py

test-phase1: check-venv
	$(PYTEST) -q tests/test_lexer tests/test_ast tests/test_parser tests/test_rendering/test_highlighting.py tests/test_cli_phase1.py

test-phase2: check-venv
	$(PYTEST) -q tests/test_semantic tests/test_rendering/test_semantic_highlighting.py tests/test_cli_phase2.py tests/test_integration/test_phase2_pipeline.py

test-phase3: check-venv
	$(PYTEST) -q tests/test_project tests/test_flow tests/test_callgraph tests/test_refactor tests/test_cli_phase3.py tests/test_integration/test_phase3_pipeline.py tests/test_integration/test_phase3_docs.py

test-core: check-venv
	$(PYTEST) -q tests/test_core

test-token-rules: check-venv
	$(PYTEST) -q tests/test_lexer/test_rules.py

test-lexer: check-venv
	$(PYTEST) -q tests/test_lexer

test-ast: check-venv
	$(PYTEST) -q tests/test_ast

test-parser: check-venv
	$(PYTEST) -q tests/test_parser

test-rendering: check-venv
	$(PYTEST) -q tests/test_rendering

test-semantic: check-venv
	$(PYTEST) -q tests/test_semantic

test-symbols: check-venv
	$(PYTEST) -q tests/test_semantic/test_symbols.py

test-resolution: check-venv
	$(PYTEST) -q tests/test_semantic/test_resolution.py

test-types: check-venv
	$(PYTEST) -q tests/test_semantic/test_type_checker.py

test-diagnostics: check-venv
	$(PYTEST) -q tests/test_semantic/test_diagnostics_pipeline.py

test-intellisense: check-venv
	$(PYTEST) -q tests/test_semantic/test_intellisense.py

test-project: check-venv
	$(PYTEST) -q tests/test_project

test-cfg: check-venv
	$(PYTEST) -q tests/test_flow/test_cfg.py

test-dataflow: check-venv
	$(PYTEST) -q tests/test_flow/test_dataflow.py

test-callgraph: check-venv
	$(PYTEST) -q tests/test_callgraph

test-rename: check-venv
	$(PYTEST) -q tests/test_refactor

test-cli: check-venv
	$(PYTEST) -q tests/test_cli.py tests/test_cli_phase1.py tests/test_cli_phase2.py tests/test_cli_phase3.py

test-integration: check-venv
	$(PYTEST) -q tests/test_integration

test-docs: check-venv
	$(PYTEST) -q tests/test_semantic/test_phase2_docs.py tests/test_integration/test_phase3_docs.py

test-error-recovery: check-venv
	$(PYTEST) -q -k "recover or recovery or incomplete or multiple_errors or no_raw_traceback"

test-determinism: check-venv
	$(PYTEST) -q -k "deterministic or stable or state_does_not_leak or do_not_share_state"

test-rename-atomic: check-venv
	$(PYTEST) -q tests/test_refactor/test_rename.py -k "atomic or staging_failure or rollback or rolls_back or reanalyzed"

test-json: check-venv
	$(PYTEST) -q -k "json"

coverage: check-venv
	$(PYTEST) $(COVERAGE_ARGS)

coverage-html: check-venv
	$(PYTEST) --cov=src/c_analyzer --cov-branch --cov-report=html --cov-fail-under=80
	@echo "HTML coverage: htmlcov/index.html"

coverage-report: check-venv
	$(PYTEST) --cov=src/c_analyzer --cov-branch --cov-report=term-missing --cov-fail-under=80

bonus-coverage: coverage

docker-check:
	@command -v "$(DOCKER)" >/dev/null || { \
		echo "ERROR: Docker is not installed or not available in PATH."; \
		echo "B2 remains pending until Docker is tested on Ubuntu."; \
		exit 2; \
	}

docker-build: docker-check
	$(DOCKER) build --target runtime -t "$(DOCKER_IMAGE)" .

docker-help: docker-check
	$(DOCKER) run --rm "$(DOCKER_IMAGE)" --help
	$(DOCKER) run --rm "$(DOCKER_IMAGE)" --version

docker-smoke: docker-help
	$(DOCKER) run --rm "$(DOCKER_IMAGE)" project-check examples/project

docker-test: docker-check
	$(DOCKER) build --target test -t "$(DOCKER_TEST_IMAGE)" .
	$(DOCKER) run --rm "$(DOCKER_TEST_IMAGE)"

bonus-docker:
	@if command -v "$(DOCKER)" >/dev/null; then \
		$(MAKE) docker-build docker-smoke docker-test; \
	else \
		echo "PENDING: Docker is unavailable; run 'make bonus-docker' on Ubuntu with Docker installed."; \
	fi

site: coverage-html
	@mkdir -p site
	$(PY) -m c_analyzer highlight examples/valid/basic.c --format html --output site/highlight.html
	$(PY) scripts/build_site.py --output site --coverage htmlcov --readme README.md
	@echo "Static site: site/index.html"

site-serve: site
	$(PYTHON) -m http.server --directory site 8000

bonus-site: site

infrastructure-check: check-venv
	$(PYTEST) -q tests/test_bonus

bonus-gate: compile test coverage site infrastructure-check bonus-docker
	@echo "Bonus infrastructure gate completed locally."
	@echo "Docker, GitHub Actions, and Pages remain pending until run in their real environments."

cli-help: check-venv
	$(PY) -m c_analyzer --help

cli-version: check-venv
	$(PY) -m c_analyzer --version

tokens: check-venv
	$(PY) -m c_analyzer tokens examples/valid/basic.c

ast: check-venv
	$(PY) -m c_analyzer ast examples/valid/basic.c

check-valid: check-venv
	$(PY) -m c_analyzer check examples/valid/basic.c

check-invalid: check-venv
	@$(PY) -m c_analyzer check examples/invalid/multiple_errors.c; code=$$?; \
	if [[ $$code -ne 1 ]]; then echo "ERROR: expected exit code 1, got $$code"; exit 1; fi; \
	echo "Expected diagnostic exit code received: 1"

check-json: check-venv
	@$(PY) -m c_analyzer check examples/semantic/invalid/type_errors.c --json; code=$$?; \
	if [[ $$code -ne 1 ]]; then echo "ERROR: expected exit code 1, got $$code"; exit 1; fi; \
	echo "Expected diagnostic exit code received: 1"

highlight-ansi: check-venv
	$(PY) -m c_analyzer highlight examples/valid/basic.c --format ansi

highlight-html: check-venv
	@mkdir -p output
	$(PY) -m c_analyzer highlight examples/valid/basic.c --format html --output output/highlight.html
	@echo "Open output/highlight.html in a browser."

symbols: check-venv
	$(PY) -m c_analyzer symbols examples/semantic/valid/scopes.c

complete: check-venv
	$(PY) -m c_analyzer complete examples/semantic/valid/completion.c 11 27

hover: check-venv
	$(PY) -m c_analyzer hover examples/semantic/valid/hover.c 6 18

project-check: check-venv
	$(PY) -m c_analyzer project-check "$(PROJECT_DIR)"

project-check-json: check-venv
	$(PY) -m c_analyzer project-check "$(PROJECT_DIR)" --json

goto-def: check-venv
	$(PY) -m c_analyzer goto-def "$(MAIN_FILE)" "$(GOTO_LINE)" "$(GOTO_COLUMN)" --project "$(PROJECT_DIR)"

goto-def-json: check-venv
	$(PY) -m c_analyzer goto-def "$(MAIN_FILE)" "$(GOTO_LINE)" "$(GOTO_COLUMN)" --project "$(PROJECT_DIR)" --json

find-refs: check-venv
	$(PY) -m c_analyzer find-refs "$(MAIN_FILE)" "$(GOTO_LINE)" "$(GOTO_COLUMN)" --project "$(PROJECT_DIR)"

find-refs-json: check-venv
	$(PY) -m c_analyzer find-refs "$(MAIN_FILE)" "$(GOTO_LINE)" "$(GOTO_COLUMN)" --project "$(PROJECT_DIR)" --json

cfg-text: check-venv
	$(PY) -m c_analyzer show-cfg "$(MAIN_FILE)" "$(MAIN_FUNCTION)" --project "$(PROJECT_DIR)" --format text

cfg-json: check-venv
	$(PY) -m c_analyzer show-cfg "$(MAIN_FILE)" "$(MAIN_FUNCTION)" --project "$(PROJECT_DIR)" --format json

cfg-dot: check-venv
	$(PY) -m c_analyzer show-cfg "$(MAIN_FILE)" "$(MAIN_FUNCTION)" --project "$(PROJECT_DIR)" --format dot

callgraph-text: check-venv
	$(PY) -m c_analyzer callgraph "$(PROJECT_DIR)" --entry main --format text

callgraph-json: check-venv
	$(PY) -m c_analyzer callgraph "$(PROJECT_DIR)" --entry main --format json

callgraph-dot: check-venv
	$(PY) -m c_analyzer callgraph "$(PROJECT_DIR)" --entry main --format dot

dead-code: check-venv
	$(PY) -m c_analyzer dead-code "$(PROJECT_DIR)"

dead-code-json: check-venv
	$(PY) -m c_analyzer dead-code "$(PROJECT_DIR)" --json

rename-preview: check-venv
	$(PY) -m c_analyzer rename "$(MAIN_FILE)" "$(RENAME_LINE)" "$(RENAME_COLUMN)" "$(RENAME_TO)" --project "$(PROJECT_DIR)"

rename-preview-json: check-venv
	$(PY) -m c_analyzer rename "$(MAIN_FILE)" "$(RENAME_LINE)" "$(RENAME_COLUMN)" "$(RENAME_TO)" --project "$(PROJECT_DIR)" --json

repl: check-venv
	$(PY) -m c_analyzer repl "$(PROJECT_DIR)"

smoke: cli-help cli-version check-valid project-check goto-def cfg-text callgraph-text dead-code rename-preview

gate0: doctor install cli-help cli-version test-phase0

gate1: compile test-phase1 tokens ast check-valid check-invalid highlight-ansi highlight-html

gate2: compile test-phase2 symbols check-json complete hover

gate3: compile test project-check callgraph-text dead-code goto-def find-refs cfg-text rename-preview

gate-all: gate0 gate1 gate2 gate3

verify: compile test smoke

clean:
	@find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
	@rm -rf .pytest_cache output htmlcov coverage.xml .coverage site
	@echo "Removed generated caches, coverage, site, and output files. Source files were not touched."
