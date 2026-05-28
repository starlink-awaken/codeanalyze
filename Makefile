PYTHON := $(shell (command -v uv >/dev/null 2>&1 && echo "uv run python3") || echo python3)
.PHONY: test lint format clean

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
