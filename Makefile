PYTHON ?= python

.PHONY: setup test lint run

setup:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

run:
	$(PYTHON) -m uvicorn story_companion.main:app --reload --host 0.0.0.0 --port 8000
