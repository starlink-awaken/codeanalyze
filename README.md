# codeanalyze

Unified code & document analysis toolkit. One CLI to analyze any project—code, documents, or both.

```
codeanalyze status      → which tools are installed
codeanalyze analyze .   → run all available analyzers
codeanalyze export -f json --code .   → export structured knowledge graph
```

## Architecture

```
                          ┌─────────────────────┐
                          │   CLI (9 commands)   │
                          └──────┬──────┬───────┘
                                 │      │
                    ┌────────────┘      └────────────┐
                    ▼                                 ▼
           Code Engine                          Document Engine
  ┌───────────┬───────────┬──────┐    ┌──────┬──────────┬──────────┐
  │ Graphify  │ GitNexus  │Serena│   │MinerU│ Docling  │ Official │
  │ (semantic)│(dependency)│(sym.)│   │(CN PDF)│(general)│ (policy) │
  └───────────┴───────────┴──────┘    └──────┴──────────┴──────────┘
                    │                         │
                    └──────────┬──────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   Knowledge Graph   │
                    │  Entity + Relation  │
                    │  + Provenance       │
                    └─────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
           JSON             JSON-LD          Cypher
        (Agent/API)      (Ontology/Web)    (Neo4j)
```

## Install

```bash
pip install -e /path/to/codeanalyze

# Optional engines:
pip install graphifyy              # semantic code graph
npm install -g gitnexus            # dependency graph
pip install docling docling-graph  # document → knowledge graph
pip install mineru                 # Chinese PDF parsing
```

## Quick start

```bash
# Check what's available
codeanalyze status

# Analyze a document project (e.g. policy documents)
codeanalyze documents --levels /path/to/policies

# Export as structured knowledge graph
codeanalyze export -f json --eidos /path/to/project

# Full pipeline with code analysis
codeanalyze analyze --docs /path/to/code-project

# Cross-reference with existing wiki
codeanalyze docscan --wiki --versions /path/to/wiki-project
```

## Export formats

| Flag | Format | Use case |
|------|--------|----------|
| `-f json` | JSON | Agent consumption, API |
| `-f json-ld` | JSON-LD | Ontology modeling, semantic web |
| `-f cypher` | Cypher | Neo4j import |
| `-f md` | Markdown | Human review |
| `--eidos` | Eidos JSON | Integration with Eidos → KOS → OntoDerive |

## Data model

Every entity carries **provenance**: source file, extraction method, confidence score.

```json
{
  "id": "docnum-京发改〔2026〕287号",
  "name": "京发改〔2026〕287号",
  "type": "Policy",
  "provenance": {
    "source_file": "/path/to/notice.pdf",
    "method": "regex+pdftotext",
    "confidence": 0.95
  }
}
```

Relations are explicit, typed, and semantically labeled:

```
[Document] --REFERENCES--> [Policy]
[Entity]   --EXTRACTED_FROM--> [SourceFile]
[Entity]   --BELONGS_TO--> [Category]
```

## Project structure

```
codeanalyze/
├── pyproject.toml
├── LICENSE
├── CLAUDE.md
├── src/codeanalyze/
│   ├── cli.py              # 9 CLI commands
│   ├── core/               # registry, workspace, results (ER model)
│   ├── analyzers/          # graphify, gitnexus, serena adapters
│   ├── documents/          # scanner, official, docling, deepwiki
│   ├── integrations/       # eidos_adapter
│   └── reports/            # generate, export, validation
└── tests/
    ├── test_results.py
    ├── test_official.py
    └── test_eidos.py
```

## Integration with Eidos

codeanalyze can export directly to [Eidos](https://github.com/workspace/eidos) format—the schema and validation layer for the Workspace knowledge foundation:

```
codeanalyze (analysis) → Eidos (validation) → KOS (storage) → OntoDerive (reasoning)
```

```bash
codeanalyze export --eidos /path
eidos validate codeanalyze-eidos.json --type node
```

## License

MIT
