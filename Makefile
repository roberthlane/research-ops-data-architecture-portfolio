PYTHON ?= python3

.PHONY: generate test demo check

generate:
	PYTHONPATH=src $(PYTHON) -m research_ops_architecture.cli

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests

demo:
	PYTHONPATH=src $(PYTHON) scripts/demo.py

check: test demo
