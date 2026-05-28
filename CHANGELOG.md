# Changelog

All notable changes to codeanalyze will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] — 2026-05-28

### Added
- `codeanalyze serve` 子命令：启动 MCP HTTP 服务（FastMCP，默认 127.0.0.1:8765）
- `policydoc` 5 个命令全部实现（之前为 TODO 空壳）：audit/dashboard/docscan/install/wiki
- `.gitignore` 新增生成文件过滤（export/report/graphify-out 等）

### Changed
- `codeanalyze` 命令从 11 个扩展到 12 个（新增 serve）
- `policydoc` 命令从 4 个（含 5 个 TODO）扩展到 9 个（全部实现）
- README.md 重写（141→260 行）：架构图更新、命令列全、MCP 服务说明、最新数据模型
- CLAUDE.md 更新：同步当前 12+9 命令、最新架构、已删除模块清理
- AGENTS.md 更新：测试数（39→105）、文件引用、架构图
- ARCHITECTURE.md 标记 Phase 1/2 完成状态

### Fixed
- ruff lint 自动修复 27 处代码风格问题

## [0.2.0] — 2026-05-21

### Added
- `audit` command: cross-validate raw docs vs wiki knowledge base (5 groups, 20 checks)
- `install` command: one-click dependency installation guide
- Eidos integration: `--eidos` export flag converts KG to OntologyNode + Relation + Fact + KnowledgeCard
- Provenance tracking on every entity (source_file, method, confidence, timestamp)
- `.doc` file support via LibreOffice bridge
- XLSX structured parsing (sharedStrings.xml + ElementTree)
- GitHub Actions CI (test matrix 3.10–3.13 + security scan)
- Pre-commit hooks (ruff, mypy, bandit)
- `.editorconfig`, `.pre-commit-config.yaml`, `scripts/bootstrap.sh`

### Changed
- CLI path handling: centralized `_validate_path()` on all 10 commands
- Content extraction: unified `_extract_file_content()` for 6 file types
- Report timestamps: `...` → actual `datetime.now()`

### Fixed
- Red team round 1 (13 issues): path injection, Cypher injection, XXE, phantom relations, ZIP bomb, control chars, silent exceptions, regex backtracking, duplicate imports
- Red team round 2 (4 bypasses): path validation insertion, backslash escape in Cypher, defusedxml XXE protection

### Security
- Path traversal: all 10 commands now validate against home directory
- Cypher injection: `replace("\\", "\\\\")` before single-quote escape
- XXE: `_safe_parse()` uses defusedxml or disabled external entity parsing
- ZIP bomb: `MAX_EMBEDDED_FILE_SIZE` (10MB) per-entry limit
- PDF timeout: increased from 15s to 60s with logging

## [0.1.0] — 2026-05-20

### Added
- Initial release: 10 CLI commands for code & document analysis
- Code engine: Graphify (semantic) + GitNexus (dependency) + Serena (symbol) adapters
- Document engine: policy/doc metadata extraction, cross-format content parsing (PDF, DOCX, XLSX, PPTX, MD, TXT)
- Export formats: JSON (Agent), JSON-LD (ontology), Cypher (Neo4j), Markdown (human)
- Knowledge Graph model: Entity + Relation + Provenance
- Policy document analysis: doc number, issuing org, date, level extraction
- 39 tests, MIT license
