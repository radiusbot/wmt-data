# wmt-data: static site and remote config for Where is My Train. No railway data.
#
#   make venv                 create .venv with pinned dev tools (pytest, ruff, mypy)
#   make check-site           validate site/ against docs/contracts/remote_files.md
#   make sync-parser-config   copy $(APP_REPO)/assets/config/parser-config.json into site/
#   make check                lint + typecheck + tests + check-site (what CI runs)

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
APP_REPO ?= ../app
WMT = PYTHONPATH=src $(PYTHON) -m wmt_data

.PHONY: venv check-site sync-parser-config test lint typecheck check clean

venv:
	/opt/homebrew/bin/python3 -m venv .venv || python3 -m venv .venv
	.venv/bin/pip install --quiet --no-cache-dir -r requirements-dev.txt

check-site:
	$(WMT) check

sync-parser-config:
	APP_REPO="$(APP_REPO)" $(WMT) sync-parser-config

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests

typecheck:
	$(PYTHON) -m mypy

check: lint typecheck test check-site

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
