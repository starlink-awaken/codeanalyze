---
name: codeanalyze
description: 统一代码与文档分析工具箱。整合 CRG(AST→SQLite)+Graphify(语义图)+GitNexus(依赖图)+Docling(文档)+MinerU(中文PDF)+policydoc(公文分析)。提供 codeanalyze(12命令)+policydoc(9命令) 两个 CLI 及 MCP HTTP 服务。当用户说「分析项目」「分析代码」「生成项目报告」「分析依赖」「分析文档」「codeanalyze」「运行分析管线」「项目结构化分析」「公文分析」「政策文档」时触发。
---

# codeanalyze — 统一代码与文档分析工具箱

整合了代码分析和文档分析两个领域的工具链，两个 CLI 入口、一个共享引擎。

依赖探测机制：装多少用多少，未安装自动跳过。

## 安装

```bash
pip install -e /Users/xiamingxing/Workspace/codeanalyze
```

两个 CLI 自动注册：`codeanalyze` + `policydoc`。

可选依赖：
```
pip install graphifyy           # 语义图谱
npm install -g gitnexus         # 依赖关系图
npm install -g code-review-graph  # Tree-sitter AST→SQLite（零LLM成本）
pip install docling docling-graph  # 文档→知识图谱
pip install marker-pdf          # PDF→Markdown
pip install mineru              # 中文PDF解析
```

## 子命令速查

### codeanalyze（12 个命令 — 代码分析为主）

| 命令 | 作用 | 典型用法 |
|------|------|---------|
| `status` | 查看当前安装的分析工具 | `codeanalyze status` |
| `analyze` | 运行全部分析 | `codeanalyze analyze --docs .` |
| `graph` | 仅 Graphify 语义图谱 | `codeanalyze graph .` |
| `deps` | 仅 GitNexus 依赖图 | `codeanalyze deps --force .` |
| `docs` | 仅文档分析 | `codeanalyze docs ./docs` |
| `report` | 仅生成报告（不重跑分析） | `codeanalyze report --docs .` |
| `export` | 导出知识图谱（JSON/JSON-LD/Cypher/MD/Eidos） | `codeanalyze export -f json .` |
| `crg` | Tree-sitter CRG 知识图谱（build/status/viz） | `codeanalyze crg build .` |
| `dashboard` | 启动交互式知识图谱仪表盘 | `codeanalyze dashboard .` |
| `install` | 一键安装可选分析工具 | `codeanalyze install --all` |
| `search` | ripgrep 搜索代码 | `codeanalyze search "pattern" .` |
| `serve` | 启动 MCP HTTP 服务 | `codeanalyze serve --port 8765` |

### policydoc（9 个命令 — 公文/政策分析为主）

| 命令 | 作用 | 典型用法 |
|------|------|---------|
| `status` | 显示文档工具安装状态 | `policydoc status` |
| `analyze` | 全量公文分析（文档+Wiki+目录） | `policydoc analyze .` |
| `documents` | 公文/政策元数据提取（文号/层级/关系） | `policydoc documents --levels .` |
| `export` | 导出政策知识图谱 | `policydoc export -f json .` |
| `audit` | 知识审计（文档 vs Wiki 交叉验证） | `policydoc audit .` |
| `docscan` | 扫描文档项目结构（目录/版本/Wiki） | `policydoc docscan --wiki --versions .` |
| `dashboard` | 政策知识图谱仪表盘 | `policydoc dashboard .` |
| `wiki` | 生成政策文档 Wiki | `policydoc wiki .` |
| `install` | 文档工具安装指南 | `policydoc install --all` |

## 架构

```
              ┌────────────────────────┐
              │      两个 CLI           │
              │  codeanalyze / policydoc│
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │   MCP HTTP 服务        │
              │  (codeanalyze serve)   │
              │  15 个 FastMCP 工具    │
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────────────────┐
              │  core/ 注册中心 + ER 模型 + 工作区  │
              └───────┬──────────────────┬─────────┘
                      │                  │
         ┌────────────▼──────┐  ┌───────▼──────────┐
         │   代码分析引擎     │  │   文档分析引擎    │
         │  CRG / GitNexus   │  │  MinerU / Docling │
         │  Graphify / ripgrep│  │  official(公文)  │
         └────────┬──────────┘  └───────┬──────────┘
                  │                      │
                  └──────────┬───────────┘
                             ▼
                   ┌──────────────────┐
                   │  Entity-Relation │
                   │  22 种关系类型   │
                   │  5 种导出格式    │
                   │  + Provenance    │
                   └──────────────────┘
```

分层分析流程：
```
rg 搜代码 → CRG 查 AST 调用链 → GitNexus 算影响半径
             → Graphify 做语义聚类
             → 知识图谱导出 → 报告/Eidos校验/Wiki
```

## MCP 服务

`codeanalyze serve` 启动 FastMCP HTTP 服务，暴露的工具：

| 工具 | 用途 |
|------|------|
| `status` | 已安装工具列表 |
| `analyze_project` | 全链路分析 |
| `export_graph` | 知识图谱导出 |
| `audit_project` | 知识审计 |
| `extract_policy_docs` | 公文元数据提取 |
| `scan_directory` | 目录扫描 |
| `rg_search` | ripgrep 代码搜索 |
| `codegraph_search/callers/callees/context` | CRG 查询 |
| `crg_status/crg_build` | CRG 管理 |

与 Agora 集成：
```bash
agora proxy add codeanalyze --command "codeanalyze serve --port 8765"
```

## 输出产物

- `codeanalyze-report.md` — 综合分析报告
- `codeanalyze-export.json` — JSON 知识图谱导出
- `graphify-out/GRAPH_REPORT.md` — Graphify 语义图谱报告
- `graphify-out/graph.html` — 交互式 D3.js 可视化
- `*-audit-report.md` — 知识审计报告

## 集成管线

```
codeanalyze (分析) → Eidos (Schema 校验)
                     → KOS (知识索引)
                     → OntoDerive (逻辑推理)
```

```bash
codeanalyze export --eidos /project
eidos validate codeanalyze-eidos.json --type node
```

## 项目结构

```
src/codeanalyze/          # 代码+文档分析 CLI
├── cli.py                # 薄 Click 组（29 行）
├── mcp.py                # MCP 服务（15 工具）
├── commands/             # 12 个子命令
├── core/                 # registry / results(ER模型) / workspace
├── analyzers/            # ripgrep / crg_graph / codereviewgraph
│                         # gitnexus / graphify
├── documents/            # official(公文) / scanner / docling
│                         # deepwiki / pipeline
├── reports/              # export / generate / audit / understand
└── integrations/         # forge(Guardrails) / eidos_adapter

src/policydoc/            # 公文政策分析 CLI
├── cli.py                # 薄 Click 组（32 行）
└── commands/             # 9 个子命令
```

## 数据模型

```python
@dataclass
class Entity:
    id: str                    # 全局唯一 ID
    name: str                  # 实体名称
    type: str                  # Policy/Function/Class/Org/Person
    provenance: Provenance     # 来源溯源（file/method/confidence）
    properties: dict           # 领域属性

@dataclass
class Relation:
    source_id: str             # 源实体
    target_id: str             # 目标实体
    type: str                  # REFERENCES/CALLS/DEPENDS_ON/...
    confidence: float          # 0.0-1.0
```

## 开发规则

1. 新增命令在 `src/codeanalyze/commands/` 或 `src/policydoc/commands/` 加文件
2. 分析引擎适配器在 `analyzers/`，文档处理在 `documents/`
3. 测试统一用 pytest：`pytest tests/ -q`
4. 所有 `except` 必须 `logger.warning()`，不能 silent pass
5. 用户路径必须 `_validate_path()` 校验

## 红队结论（必知）

两轮红队攻击后，安全要点：
1. 路径：`_validate_path()` 不可绕过
2. Cypher 输出：转义 `\` 和 `'`
3. XML 解析：用 `_safe_parse()`，不用 `ET.fromstring()`
4. ZIP 解析：10MB 上限每文件
5. 异常处理：必须日志，禁止 `except: pass`

见 REDTEAM.md / REDTEAM_V2.md。
