PYTHON ?= python3
SQL_SERVER_ARGS ?=

.PHONY: generate refresh test demo lint format-check typecheck check-generated check-package check check-sql

generate:
	PYTHONPATH=src $(PYTHON) -m research_ops_architecture.cli

refresh:
	PYTHONPATH=src $(PYTHON) scripts/check_generated.py --write

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests

demo:
	PYTHONPATH=src $(PYTHON) scripts/demo.py

lint:
	$(PYTHON) -m ruff check .

format-check:
	$(PYTHON) -m ruff format --check .

typecheck:
	$(PYTHON) -m mypy

check-generated:
	PYTHONPATH=src $(PYTHON) scripts/check_generated.py

check-package:
	$(PYTHON) scripts/check_package.py

check: lint format-check typecheck test check-generated check-package

check-sql:
	PYTHONPATH=src $(PYTHON) scripts/test_sql_server.py $(SQL_SERVER_ARGS)
