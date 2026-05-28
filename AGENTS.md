# AGENTS.md — codeanalyze

Instructions for AI coding agents (Claude Code, Cursor, Codex, etc.)
working with this project.

## Project Overview

codeanalyze wraps multiple code and document analysis tools (CRG,
Graphify, GitNexus, Docling, MinerU) into two unified CLIs and exports
structured knowledge graphs. Local-first, zero cloud dependency.

## Key Files

| File | Purpose |
|------|---------|
| `src/codeanalyze/cli.py` | 29-line Click group, commands in `commands/` |
| `src/codeanalyze/core/results.py` | Entity, Relation, KnowledgeGraph data model |
| `src/codeanalyze/analyzers/crg_graph.py` | CRG SQLite queries (search/callers/callees/context) |
| `src/codeanalyze/documents/official/` | Policy document extraction (models/parsers/pipeline) |
| `src/codeanalyze/reports/audit/` | Wiki cross-validation (models/checkers/pipeline) |
| `src/codeanalyze/mcp.py` | MCP HTTP server (15 tools) |
| `src/policydoc/` | Document-focused CLI (9 commands) |
| `tests/` | 105 pytest tests |

## Architecture

```
CLI (codeanalyze 12 + policydoc 9)
  → MCP HTTP server
  → core/ (registry + entity-relation model)
  → analyzers/ + documents/ (domain adapters)
  → reports/ (export/audit/understand)
  → integrations/ (forge guardrails + eidos adapter)
```

## CLI Commands

### codeanalyze (12 commands — code-focused)

- `status` — show installed tool versions
- `analyze` — full pipeline (code + docs)
- `graph` — Graphify semantic graph only
- `deps` — GitNexus dependency graph only
- `docs` — document analysis only
- `report` — regenerate report without re-analysis
- `export` — export knowledge graph (JSON/JSON-LD/Cypher/MD/Eidos)
- `crg` — Tree-sitter CRG management (build/status/viz)
- `dashboard` — interactive knowledge graph dashboard
- `install` — one-click dependency install guide
- `search` — ripgrep code search
- `serve` — start MCP HTTP server

### policydoc (9 commands — document-focused)

- `status` — show doc tool versions
- `analyze` — full document pipeline
- `documents` — policy metadata extraction (doc numbers/levels/relations)
- `export` — export policy knowledge graph
- `audit` — cross-validate docs vs wiki
- `docscan` — scan document project structure
- `dashboard` — policy knowledge graph dashboard
- `wiki` — generate project wiki
- `install` — install guide for doc tools

## Development Rules

1. **Add tests.** `tests/` directory. Run with `.venv/bin/python -m pytest tests/ -q`.
2. **One file per analyzer.** Analyzers go in `analyzers/` or `documents/`.
3. **No silent failures.** Use `logger.warning()` in except blocks.
4. **Path validation.** All user paths go through `_validate_path()`.
5. **Semantic versioning.** Update `CHANGELOG.md`, `__init__.py`, `pyproject.toml`.

## Data Model

Core types in `core/results.py`:

- `Entity` — typed node with id, name, domain, confidence, provenance
- `Relation` — typed edge between two entities with confidence and weight
- `Provenance` — source tracking (file, method, analyzer, confidence)
- `KnowledgeGraph` — container for entities + relations + merge

Export converters: `reports/export.py` and `integrations/eidos_adapter.py`

## Red Team Findings (Must Know)

Two rounds of adversarial analysis completed. Key findings:

1. Paths validated via `_validate_path()` — do not bypass
2. Cypher output escapes `\` and `'` — do not skip
3. XML parsing uses `_safe_parse()` — do not call `ET.fromstring()` directly
4. ZIP parsing has 10MB limit — do not remove
5. All except blocks must log — do not `except: pass`

See `REDTEAM.md` and `REDTEAM_V2.md` for full reports.
