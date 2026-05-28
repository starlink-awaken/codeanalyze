#!/usr/bin/env bash
set -euo pipefail

echo "=== codeanalyze dev bootstrap ==="

# Create venv if needed
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "venv created"
fi

source .venv/bin/activate

# Install with dev deps
pip install -e ".[dev]" --quiet

# Install pre-commit hooks
if command -v pre-commit &> /dev/null; then
    pre-commit install
    pre-commit run --all-files || true
    echo "pre-commit hooks installed"
fi

# Install ruff for editor integration
pip install ruff --quiet 2>/dev/null || true

echo "=== ready ==="
echo "Run: source .venv/bin/activate"
echo "Run: pytest tests/ -v"
