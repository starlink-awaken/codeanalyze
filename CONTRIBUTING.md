# Contributing

## Setup

```bash
git clone <repo>
cd codeanalyze
pip install -e ".[dev]"
```

## Code style

- Python 3.10+ type hints on all public functions
- Google-style docstrings on modules and public APIs
- Imports: stdlib → third-party → local
- `ruff` for linting (when available)

## Tests

```bash
pytest tests/ -x -q
```

## Pull requests

1. One change per PR
2. Tests included
3. Format with `ruff format src/` before committing
4. Update `CLAUDE.md` if adding new commands

## Project structure

- `cli.py`: CLI commands only. No analysis logic.
- `core/`: Shared models (Entity, Relation, KnowledgeGraph).
- `analyzers/`: One file per external tool adapter.
- `documents/`: One file per document processing capability.
- `integrations/`: Optional integrations with external systems.
- `reports/`: Output generation and cross-validation.
