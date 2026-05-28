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
- `ruff` for linting: `ruff check src/ && ruff format src/`

## Tests

```bash
.venv/bin/python -m pytest tests/ -x -q
```

105 tests total. New commands need tests.

## Project structure

- `src/codeanalyze/` — code analysis CLI (12 commands)
- `src/policydoc/` — document analysis CLI (9 commands)
- `src/codeanalyze/commands/` — codeanalyze CLI subcommands
- `src/codeanalyze/core/` — shared models (Entity, Relation, KnowledgeGraph)
- `src/codeanalyze/analyzers/` — one file per external tool adapter
- `src/codeanalyze/documents/` — document processing capabilities
- `src/codeanalyze/integrations/` — optional integrations (forge, eidos)
- `src/codeanalyze/reports/` — output generation and cross-validation
- `src/policydoc/commands/` — policydoc CLI subcommands
- `tests/` — 105 pytest tests

## Pull requests

1. One change per PR
2. Tests included
3. Format with `ruff format src/` before committing
4. Update `CLAUDE.md` if adding new commands
