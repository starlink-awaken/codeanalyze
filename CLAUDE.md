---
name: codeanalyze
description: 统一代码与文档分析工具箱。整合 Graphify(语义图)+GitNexus(依赖图)+Serena(符号)+Docling(文档)。当用户说「分析项目」「分析代码」「生成项目报告」「分析依赖」「分析文档」「codeanalyze」「运行分析管线」「项目结构化分析」时触发。提供 status/analyze/graph/deps/docs/report 六个子命令。
---

# codeanalyze — 统一代码与文档分析工具箱

整合了代码分析和文档分析两个领域的工具链，一个命令触发全链路分析。

## 安装

```bash
pip install -e /Users/xiamingxing/Workspace/codeanalyze

# 可选依赖（按需安装）：
pip install graphifyy           # 语义图谱（推荐）
npm install -g gitnexus          # 依赖关系图（推荐）
pip install docling docling-graph  # 文档→知识图谱
pip install marker-pdf           # PDF→Markdown
```

## 子命令速查

| 命令 | 作用 | 典型用法 |
|------|------|---------|
| `codeanalyze status` | 查看当前安装的分析工具 | `codeanalyze status` |
| `codeanalyze analyze [path]` | 运行全部分析（核心命令） | `codeanalyze analyze --docs .` |
| `codeanalyze graph [path]` | 仅 Graphify 语义图谱 | `codeanalyze graph .` |
| `codeanalyze deps [path]` | 仅 GitNexus 依赖图 | `codeanalyze deps --force .` |
| `codeanalyze docs [path]` | 仅文档分析 | `codeanalyze docs ./docs` |
| `codeanalyze report [path]` | 仅生成报告（不重跑分析） | `codeanalyze report --docs .` |
| `codeanalyze docscan [path]` | 扫描文档项目（目录/版本/Wiki） | `codeanalyze docscan --wiki --versions .` |
| `codeanalyze wiki [path]` | 生成 Wiki 文档（DeepWiki-Open/本地） | `codeanalyze wiki --api .` |
| `codeanalyze documents [path]` | **公文/政策分析**（文号/层级/关系） | `codeanalyze documents --levels .` |
| `codeanalyze export [path]` | **导出结构化知识图谱** | `codeanalyze export -f json-ld .` |

## 三层分析架构

```
Serena (符号层)   → LSP 符号级检索：找定义、找引用、重构
GitNexus (关系层) → 预计算依赖图：调用链、blast radius
Graphify (语义层) → AST+LLM 语义图谱：God Node、社区检测、置信度标签
                              ↓
                    Docling (文档层) → 文档→Markdown→知识图谱
                              ↓
                      Merged Report (跨工具汇总)
```

## 使用示例

```bash
# 查看工具状态
codeanalyze status

# 完整分析当前项目（代码+文档）
cd /Users/xiamingxing/Workspace/my-project
codeanalyze analyze --docs .

# 仅分析代码依赖关系
codeanalyze deps .

# 分析文档目录
codeanalyze docs ./docs
```

## 输出产物

- `codeanalyze-report.md` — 综合分析报告
- `codeanalyze-docs-report.md` — 文档分析报告（--docs 时）
- `graphify-out/GRAPH_REPORT.md` — Graphify 生成（如有）
- `graphify-out/graph.html` — 交互式图谱可视化

## 与 Serena MCP 配合

Serena 不通过 CLI 调用，而是在分析过程中提示 Agent 直接使用其 MCP 工具：

```
find_symbol          → 查找符号定义
find_referencing_symbols → 谁引用了这个符号
get_symbols_overview → 文件符号概览
replace_symbol_body  → 安全替换符号内容
rename_symbol        → 跨文件重命名
```

## 文档项目专用命令：docscan

## Wiki 生成：codeanalyze wiki

生成项目管理 Wiki，支持两种模式：

| 模式 | 条件 | 命令 |
|------|------|------|
| **DeepWiki-Open API** | 已部署 DeepWiki-Open + `DEEPWIKI_OPEN_URL` 环境变量 | `codeanalyze wiki --api .` |
| **本地生成** | 默认模式，用 Graphify/GitNexus 输出生成 Markdown Wiki | `codeanalyze wiki .` |

DeepWiki-Open 部署：

```bash
git clone https://github.com/AsyncFuncAI/deepwiki-open
cd deepwiki-open
# 配置 .env (需要 GOOGLE_API_KEY 或 OPENAI_API_KEY)
docker-compose up -d
export DEEPWIKI_OPEN_URL=http://localhost:3000
codeanalyze wiki --api .
```

适合扫描 `国转中心` 类型的文档密集型项目。自动识别：

- **分类目录**：按 00-99 前缀自动归类
- **文件类型**：PDF/DOCX/XLSX/MD/TXT 分类统计
- **版本链**：同一文件的多版本演化（v1→v2→v3）
- **Wiki 完整性**：检查 `_工作机制/wiki` 核心文件是否齐全
- **混合项目检测**：自动判断是代码项目、文档项目、还是混合项目

```bash
# 扫描文档项目
codeanalyze docscan /Users/xiamingxing/Documents/国转中心

# 带版本链和 Wiki 分析
codeanalyze docscan --wiki --versions /Users/xiamingxing/Documents/国转中心

# 保存报告
codeanalyze docscan -o ~/Desktop/国转中心扫描报告.md /Users/xiamingxing/Documents/国转中心
```

### Eidos 集成

Eidos 是 Workspace 的 schema 校验层。codeanalyze 通过 `--eidos` 标志输出 Eidos 兼容格式：

```bash
codeanalyze export --eidos /Users/xiamingxing/Documents/国转中心/40-政策法规
# 输出: codeanalyze-eidos.json（含 OntologyNode + Relation + Fact + KnowledgeCard）
# 之后可用: eidos validate codeanalyze-eidos.json --type node
```

路线：codeanalyze(分析) → Eidos(校验) → KOS(索引) → OntoDerive(推理)

### 项目文件清单

当前共 23 个源文件（src/codeanalyze/）：
```
cli.py              ← 9 个子命令入口
core/               ← registry, workspace, results(ER模型)
analyzers/          ← graphify, gitnexus, serena 适配器
documents/          ← scanner, official, docling, deepwiki, pipeline
integrations/        ← eidos_adapter (可选)
reports/            ← generate, export, validation
```
