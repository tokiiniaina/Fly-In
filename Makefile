PYTHON ?= python3
MAP ?= maps/01_linear_path.txt
MYPY_FLAGS = --warn-return-any --warn-unused-ignores \
    --ignore-missing-imports --disallow-untyped-defs \
    --check-untyped-defs

.PHONY: install run run-3d debug test clean lint lint-strict

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) fly_in.py $(MAP)

run-3d:
	$(PYTHON) fly_in.py $(MAP) --3d

debug:
	$(PYTHON) -m pdb fly_in.py $(MAP)

test:
	$(PYTHON) -m pytest -q

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	$(PYTHON) -m flake8 . --exclude .venv,venv,__pycache__
	$(PYTHON) -m mypy $(MYPY_FLAGS) --exclude '(\.venv|venv)/'

lint-strict:
	$(PYTHON) -m flake8 . --exclude .venv,venv,__pycache__
	$(PYTHON) -m mypy . --strict --ignore-missing-imports --exclude '(\.venv|venv)'