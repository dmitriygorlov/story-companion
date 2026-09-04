PYTHON ?= python

.PHONY: setup test lint check run

setup:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

check: lint test

run:
	$(PYTHON) -m uvicorn story_companion.main:app --reload --host 0.0.0.0 --port 8000
