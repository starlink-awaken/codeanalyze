# codeanalyze

统一代码与文档分析工具箱。两个 CLI、一个引擎、零云依赖。

```
codeanalyze status     → 哪些工具已安装
codeanalyze analyze .  → 全链路代码分析
codeanalyze serve      → 启动 MCP HTTP 服务（供 AI Agent 调用）

policydoc audit .      → 政策文档知识审计
policydoc documents .  → 公文元数据提取
```

## 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                       两个 CLI                                    │
│  codeanalyze（12个命令）       policydoc（9个命令）                 │
│  代码/文档分析                  公文/政策文档分析                     │
└────────────────────────┬─────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────────┐
│                        MCP HTTP 服务（serve 命令）                  │
│                 FastMCP，供 AI Agent / Agora 调用                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
┌────────────────────────▼──────────────┬──────────────────────────┐
│        代码分析引擎                     │     文档分析引擎          │
│  ┌──────┬──────┬──────┐               │  ┌──────┬──────┬──────┐ │
│  │ CRG  │GitNex│Graphi│               │  │MinerU│Doclin│Offici│ │
│  │(AST→ │us(依 │fy(语 │               │  │(中文 │g(通用│al(公 │ │
│  │SQLite│赖图) │义KG) │               │  │PDF)  │文档) │文)   │ │
│  │)     │      │      │               │  └──────┴──────┴──────┘ │
│  └──────┴──────┴──────┘               └──────────┬──────────────┘
│                         │                         │
│                         └──────────┬──────────────┘
│                                    ▼
│                    ┌──────────────────────────────┐
│                    │    知识图谱（Entity + Relation │
│                    │    + Provenance）             │
│                    │    5 种导出格式               │
│                    └──────┬───────────────────────┘
│                           │
│              ┌────────────┼────────────┬───────────┐
│              ▼            ▼            ▼           ▼
│           JSON       JSON-LD       Cypher      Markdown
│        (Agent/API) (Ontology/Web)  (Neo4j)    (Human)
│                           │
│              ┌────────────┘
│              ▼
│        ┌──────────────────┐
│        │  Eidos（校验）     │
│        │  → KOS（索引）     │
│        │  → OntoDerive（推理）│
│        └──────────────────┘
└────────────────────────────────────────────────────────────────┘
```

**分析流程：**

```
rg 搜代码 → CRG 查 AST 调用链 → GitNexus 算影响半径
                                       ↓
         Graphify 做语义聚类（社区检测、God Node）
                                       ↓
            知识图谱导出 → 报告 → Eidos 校验 → Wiki
```

## 安装

```bash
pip install -e /path/to/codeanalyze
```

两个 CLI 自动注册：`codeanalyze` + `policydoc`。

### 可选分析引擎

| 引擎 | 安装 | 用途 |
|------|------|------|
| **CRG** | `npm install -g code-review-graph` | Tree-sitter AST → SQLite 持久化，零 LLM 成本 |
| **GitNexus** | `npm install -g gitnexus` | 预计算依赖图 + 影响半径 |
| **Graphify** | `pip install graphifyy` | AST + LLM 语义图谱，社区检测 |
| **Docling** | `pip install docling docling-graph` | IBM 文档 → 结构化数据 → 知识图谱 |
| **MinerU** | `pip install mineru` | 中文 PDF → Markdown/JSON |
| **Marker** | `pip install marker-pdf` | 高精度 PDF → Markdown |
| **Unstructured** | `pip install unstructured` | 文档分块与分区 |

> 工具都是可选依赖。装多少用多少，未安装的工具自动跳过，不影响核心功能。

## 快速上手

### codeanalyze — 代码分析

```bash
# 查看已安装的工具
codeanalyze status

# 全链路代码分析（代码 + 文档）
codeanalyze analyze --docs /path/to/project

# 仅语义图谱
codeanalyze graph .

# 仅依赖图
codeanalyze deps .

# Tree-sitter CRG 知识图谱
codeanalyze crg build .
codeanalyze crg status .

# 启动 MCP HTTP 服务（供 AI Agent 调用）
codeanalyze serve --port 8765
```

### policydoc — 公文/政策分析

```bash
# 查看工具状态
policydoc status

# 提取公文元数据（文号/层级/机关/日期）
policydoc documents --levels /path/to/policies

# 交叉审计：原始文档 vs Wiki 知识库
policydoc audit .

# 浏览式扫描文档项目
policydoc docscan --wiki --versions .

# 导出知识图谱
policydoc export -f json .
```

### MCP HTTP 服务

`codeanalyze serve` 启动 FastMCP HTTP 服务，对 AI Agent 暴露所有分析工具：

```bash
codeanalyze serve --port 8765

# 与 Agora 集成
agora proxy add codeanalyze --command "codeanalyze serve --port 8765"
```

暴露的 MCP 工具：

| 工具 | 用途 |
|------|------|
| `status` | 查看已安装分析工具 |
| `analyze_project` | 全链路分析 |
| `export_graph` | 导出知识图谱 |
| `audit_project` | 知识审计 |
| `extract_policy_docs` | 公文元数据提取 |
| `scan_directory` | 文档目录扫描 |
| `rg_search` | ripgrep 代码搜索 |
| `codegraph_search` | CRG 符号搜索 |
| `codegraph_callers` | 上游调用链 |
| `codegraph_callees` | 下游调用链 |
| `codegraph_context` | 文件上下文 |
| `crg_status` / `crg_build` | CRG 管理 |

## 导出格式

| 标志 | 格式 | 用途 |
|------|------|------|
| `-f json` | JSON | Agent 消费、API |
| `-f json-ld` | JSON-LD | 本体建模、语义网 |
| `-f cypher` | Cypher | Neo4j 导入 |
| `-f md` | Markdown | 人类阅读 |
| `--eidos` | Eidos JSON | → KOS → OntoDerive 推理管线 |

## 知识图谱数据模型

每个实体携带**来源溯源（Provenance）**：

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

关系类型（22 种）：`REFERENCES`, `EXTRACTED_FROM`, `BELONGS_TO`, `CALLS`, `DEPENDS_ON`, `CONTAINS`, `IMPLEMENTS`, etc.

## 可靠性保障

Forge Guardrails — 所有 MCP 工具自动包裹：

- **Rescue Parsing**：解析失败时自动重试策略
- **Retry Nudge**：失败后智能重试（可配最大次数）
- **Step Enforcement**：多步骤管道，步骤依赖检查
- **Error Recovery**：异常捕获 + 结构化错误响应

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
src/
├── codeanalyze/              # 代码/文档分析 CLI
│   ├── cli.py                # 薄 Click 组 (29 行)
│   ├── mcp.py                # MCP 服务 (15 个工具)
│   ├── commands/             # 12 个 CLI 子命令
│   ├── core/                 # 注册中心、ER 模型、工作区
│   ├── analyzers/            # 分析引擎适配器
│   │   ├── ripgrep.py        # Rust rg 搜索
│   │   ├── crg_graph.py      # CRG SQLite 查询
│   │   ├── codereviewgraph.py# CodeReviewGraph 管理
│   │   ├── gitnexus.py       # LadybugDB 依赖图
│   │   └── graphify.py       # 语义图谱
│   ├── documents/            # 文档分析引擎
│   │   ├── official/         # 公文/政策解析（PDF/DOCX/XLSX）
│   │   ├── scanner.py        # 目录扫描
│   │   ├── docling.py        # Docling 集成
│   │   ├── deepwiki.py       # DeepWiki 集成
│   │   └── pipeline.py       # 文档全链路
│   ├── reports/              # 报告生成器
│   │   ├── audit/            # 知识审计（5 组检查）
│   │   └── understand.py     # Understand Anything 仪表盘
│   └── integrations/         # 外部集成
│       ├── forge.py          # Forge Guardrails
│       └── eidos_adapter.py  # Eidos Schema 校验
├── policydoc/                # 公文/政策文档 CLI
│   ├── cli.py                # 薄 Click 组 (32 行)
│   └── commands/             # 9 个子命令
└── ...pyproject.toml, README.md, ARCHITECTURE.md
```

## 架构原则

| 原则 | 说明 |
|------|------|
| **本地优先** | 无云依赖，所有分析在本地运行 |
| **Graceful Degradation** | 工具未安装自动跳过，不报错 |
| **零 LLM 成本层** | CRG + ripgrep 不调用 LLM |
| **Provenance 追踪** | 每个实体记录来源和置信度 |
| **安全默认** | 参数化 SQL、defusedxml XXE 防护、路径验证 |

## License

MIT
