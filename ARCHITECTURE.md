# codeanalyze — 战略架构设计

> 作者: P10 CTO 视角 | 日期: 2026-05-21 | 状态: 草案
> 领域: 代码分析引擎 × 公文/文档分析引擎

---

## 一、战略判断

### 1.1 当前格局

你的工具生态目前由三部分构成：

```
AI 工作流层:    Pallas → OntoDerive → Minerva → Sophia (知识工程管线)
基础设施层:    Agora (MCP Hub) / KOS (知识检索) / Honeycomb (Agent 引擎)
业务层:        国转中心 (公文/政策/平台管理) / 代码项目 (Python/TS/Go)
```

`codeanalyze` 现在夹在"基础设施层"和"业务层"之间——它既不是平台也不是应用，而是一个 **分析编排器**。这个位置本身是对的，但它的形态需要演进。

### 1.2 关键矛盾

| 矛盾 | 代码分析 | 公文/文档分析 |
|------|---------|--------------|
| 底层生态 | 成熟（6+ 开源工具） | 空白（需自建） |
| 核心能力 | 编排统一调用 | 创造抽取逻辑 |
| 输出形式 | 结构化图数据 | 结构化元数据+自然语言 |
| 技术风险 | 低（工具替代成本低） | 中（抽取准确率不确定） |
| 你的需求频率 | 偶发（改代码时） | 持续（国转中心日常工作） |

**结论：这两个引擎的形态不同、生命周期不同、风险不同，但不需要拆项目。** 拆项目解决的是"代码归属权"的问题——你一个人维护，没有归属权问题。

> 阿里味翻译：这不是组织架构问题，这是模块边界问题。拆两个项目是3.25的决策——有成本没收益。正确做法是单体内部做领域隔离。

### 1.3 必须留意的外部趋势

1. **MCP 正在吃掉 CLI 层**：GitNexus、Serena 全是 MCP-native。CLI 是开发体验入口，但真正的能力暴露要走 MCP。
2. **Agent 才是消费者**：最终用户可能不是人，是 Agent。codeanalyze 的 API 设计要考虑 Agent 调用场景。
3. **中文文档分析门槛在快速下降**：MinerU 2.5 (1.2B VLM) 和 Granite-Docling 258M 让端侧文档解析精度接近商用水平。

---

## 二、架构设计

### 2.1 核心理念：双引擎 · 单壳 · MCP 优先

```
┌─────────────────────────────────────────────────────────┐
│                   codeanalyze (CLI Shell)                │
│  status · analyze · docscan · wiki · documents · report │
├──────────────────────┬──────────────────────────────────┤
│   Engine: Code       │   Engine: Document               │
│                      │                                  │
│  ┌──────────────┐    │  ┌──────────────┐                │
│  │ Graphify     │    │  │ MinerU       │  ← 中文解析   │
│  │   (semantic) │    │  │   (PDF→MD)   │                │
│  ├──────────────┤    │  ├──────────────┤                │
│  │ GitNexus     │    │  │ Docling-Graph│  ← 文档→图谱  │
│  │   (dependency)│   │  │   (doc→KG)   │                │
│  ├──────────────┤    │  ├──────────────┤                │
│  │ Serena       │    │  │ Official     │  ← 公文元数据 │
│  │   (symbol)   │    │  │   (policy)   │                │
│  └──────────────┘    │  └──────────────┘                │
│                      │                                  │
│  输出: entities/     │  输出: entities/                  │
│       relations/     │       relations/                  │
│       graph.json     │       policy-graph.md             │
└──────────────────────┴──────────────────────────────────┘
         │                          │
         └──────────┬───────────────┘
                    ▼
       ┌────────────────────────┐
       │   Merged Report Engine │
       │   (cross-domain merge) │
       └────────────────────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
   MCP Server            CLI Output
   (tools: analyze,      (Markdown/JSON)
    query, merge)
```

### 2.2 模块边界定义

```
codeanalyze/
├── cli.py                 ← CLI shell（命令路由 + 格式输出）
├── mcp.py                 ← MCP Server（长期演进方向）
├── core/                  ← 共享基础设施
│   ├── registry.py        ← 工具检测/安装引导
│   ├── workspace.py       ← 工作区类型检测
│   └── results.py         ← 统一实体/关系模型
├── code/                  ← 代码分析引擎（独立目录）
│   ├── analyzers/
│   │   ├── graphify.py    ← Graphify 适配
│   │   ├── gitnexus.py    ← GitNexus 适配
│   │   └── serena.py      ← Serena 引导
│   └── reports/
│       └── generate.py    ← 代码侧报告生成
├── documents/             ← 文档分析引擎（独立目录）
│   ├── parsers/
│   │   ├── mineru.py      ← MinerU 适配（中文PDF）
│   │   ├── docling.py     ← Docling 适配（通用文档）
│   │   └── marker.py      ← Marker 适配（高精度）
│   ├── extractors/
│   │   ├── policy.py      ← 公文元数据抽取
│   │   ├── entity.py      ← 命名实体抽取
│   │   └── relation.py    ← 文档间关系发现
│   └── reports/
│       ├── policy.py      ← 政策图谱报告
│       └── wiki.py        ← Wiki 生成
└── merge/                 ← 交叉合并引擎
    ├── aligner.py         ← 实体对齐（代码实体↔文档实体）
    └── reporter.py        ← 统一报告生成
```

**关键决策：两引擎共享 core/（工具检测+结果模型），不共享分析逻辑。**

### 2.3 数据模型统一

所有分析器共享一套实体-关系模型：

```python
@dataclass
class Entity:
    id: str                    # 全局唯一 ID
    name: str                  # 实体名称
    type: str                  # Function/Class/Module/Policy/Org/Person
    source: str                # graphify/gitnexus/mineru/official
    confidence: float          # 0.0-1.0
    properties: dict           # 领域特定属性
    source_path: str           # 来源文件路径
    source_line: int           # 来源行号（可选）

@dataclass
class Relation:
    source_id: str             # 源实体 ID
    target_id: str             # 目标实体 ID
    type: str                  # IMPORTS/CALLS/REFERENCES/SUPERSEDES
    confidence: float
    metadata: dict             # 关系特定元数据
```

两引擎输出同一模型。合并引擎做实体对齐（同名实体合并、同义实体链接）。

---

## 三、演进路线图

### Phase 1：地基期（当前 → 2周）🟢 已完成

目标：CLI 可用，两引擎各有基础能力

- [x] CLI 框架：8 个子命令 + 工具注册表
- [x] 代码引擎：Graphify + GitNexus + Serena 适配
- [x] 文档引擎：MinerU + Docling + 公文元数据 + Wiki 生成
- [x] 混合项目检测 + 路由建议

### Phase 2：质量期（2-6周）🟡 当前

目标：文档抽取精度可量化、解决关键断点

```
P0: 公文元数据抽取实测
  └─ target: 对 国转中心/40-政策法规 跑一轮
  └─ metric: 文号召回率 >80%、层级分类准确率 >90%
  └─ blocker: 需装 MinerU 跑一次 .doc/.docx 解析

P0: 安装体验优化
  └─ codeanalyze install → 一键装所有可选依赖
  └─ codeanalyze install --minimal (仅核心)
  └─ 自动检测缺失工具并打印安装命令

P1: 国转中心全量扫描
  └─ codeanalyze docscan --wiki --versions
  └─ codeanalyze documents --levels
  └─ output: 与现有 00-政策图谱.md 交叉核对

P1: MCP 探测
  └─ codeanalyze mcp → 启动 MCP Server（stdio）
  └─ tools: analyze_project, query_graph, compare_docs
```

### Phase 3：集成期（6-12周）🔵

目标：接入现有基础设施，形成闭环

```
P0: Agora MCP Hub 注册
  └─ codeanalyze 作为 Agora pipeline step
  └─ agora pipeline codeanalyze /path/to/project

P0: KOS 知识同步
  └─ 分析结果自动同步到 KOS 索引
  └─ 文档实体→ENTITIES.md 自动更新
  └─ 政策关系→TIMELINE.md 自动追加

P1: Serena 深度集成
  └─ codeanalyze analyze 完成后自动触发 Serena 符号级查询
  └─ 分析报告内联 Serena 工具提示

P1: Graphify 结果缓存增量更新
  └─ git hook 自动触发 re-index
  └─ codeanalyze watch → 文件变更监听
```

### Phase 4：Agent 原生期（12周+）🟣

目标：Agent 是主要用户，CLI 是次要入口

```
P0: MCP Server 生产化
  └─ 支持 Agent 直接调用: /analyze-project, /query-graph, /diff-versions
  └─ 支持 SSE 传输（远程 Agent 调用）

P1: 跨项目知识图谱
  └─ 多个项目的实体/关系合并为全局图
  └─ 代码项目↔文档项目实体链接
  └─ 例: 政策文件中的"中试平台"实体 ↔ 代码项目中的 Platform 类

P2: 主动监测
  └─ 定时扫描国转中心政策目录变化
  └─ 新文件到达 → 自动抽取 → 追加到 TIMELINE.md
  └─ 通过定时任务而非 CLI 触发
```

---

## 四、不分拆的架构论证

这个问题必须有回应不以回避：

### 4.1 分拆的收益分析

| 收益 | 评估 |
|------|------|
| 独立版本演进 | 你一个人维护，无多团队协调需求 → 收益为 0 |
| 独立部署 | 两引擎共享 Python 3.10+ 依赖，无独立部署必要 → 收益为 0 |
| 职责清晰 | 当前目录结构已按 code/ 和 documents/ 隔离 → 收益为 0 |
| 降低新人认知成本 | 没有新人 → 收益为 0 |
| 减少 pip install 体积 | 用户可只装需要的 extra → 用 optional-dependencies 解决 |

**分拆的总收益 = 0。**

### 4.2 不分拆的价值

- **共享 core/ 基础设施**：工具检测、工作区识别、结果模型——这些代码引擎和文档引擎共用，拆了就得复制或者抽成第三个包
- **混合项目一口价**：docscan 自动判断项目类型，用户不用想"我这个项目该用哪个工具"
- **合并报告**：代码实体和文档实体在同一份报告里交叉引用——分拆就做不到
- **维护成本低**：一个 pyproject.toml、一套 CI、一个 `pip install -e .`

### 4.3 结论

> **不分拆。用目录隔离代替仓库隔离，用 optional-dependencies 代替独立分发。**

---

## 五、关键技术决策

### 决策 1：CLI 为当前主力，MCP 为演进方向

不是二选一。当前基础设施（Agora/KOS/Minerva）都是 CLI-native，你的工作流也以 CLI 为主。MCP Server 在 Phase 3 加入，与 CLI 并行存在，不替代。

### 决策 2：两引擎共享 core/，不共享分析逻辑

core/ 只放：
- 工具注册表 (registry.py)
- 工作区检测 (workspace.py)
- 结果数据模型 (results.py)
- 公共 CLI 选项 (shared options)

不放：
- 任何分析器的具体逻辑
- 任何领域特定的抽取规则
- 任何外部工具适配

### 决策 3：文档引擎的抽取逻辑优先用规则+正则，再升级到 LLM

公文文号/发文机关/日期有固定的模式可循（`〔2026〕2号`、`京发改规〔2026〕1号`），先用正则召回，token 成本为零。OCR 和语义理解才上 LLM。这个层级要分开：

```
Layer 1: 模式匹配（正则）→ 文号、日期、金额
Layer 2: 规则分类（目录+关键词）→ 政策层级、业务领域
Layer 3: LLM 抽取 → 核心条款摘要、政策关系推断
```

每层保底可用，越高层越可选。

### 决策 4：与现有系统的集成不做硬耦合

- **KOS**：codeanalyze 产出写文件，KOS 按自己的节奏索引——不直接写 KOS 数据库
- **Agora**：codeanalyze 提供 MCP 接口，Agora 按 pipeline 调用——不引入 Agora 依赖
- **Minerva**：graphify_adapter.py 继续存在，codeanalyze 不替代它

---

## 六、关键风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| MinerU 安装复杂（GPU依赖） | 高 | 用户在中文PDF场景用不上 | 降级到 Docling + 提示安装引导 |
| 公文元数据抽取准确率低 | 中 | 用户不信赖自动输出 | 打 confidence 标签，强制人工确认后才写入|
| 文档引擎代码引擎耦合腐烂 | 低 | 改一个影响另一个 | 目录隔离 + 各自独立测试 |
| 工具生态变化快 | 中 | GitNexus/Graphify API 变更 | 版本锁定 + 适配器模式 |
| 用户直接需求超过工程投入 | 中 | 工具做了没人用 | 每期只做用户当前需求队列的前2项 |

---

## 七、即刻行动项

```
┌──────────────────────────────────────────────────────┐
│ [P0] 跑一次 documents 命令验证抽取质量              │
│      codeanalyze documents --levels                  │
│      /Users/xiamingxing/Documents/国转中心           │
│      验证：文号提取/层级分类/日期准确性              │
│      输出：与 00-政策图谱.md 交叉核对                │
├──────────────────────────────────────────────────────┤
│ [P0] 装 MinerU，跑一篇中文政策文件的完整解析         │
│      pip install mineru                              │
│      对比 MinerU vs Docling 的中文 PDF 解析质量       │
├──────────────────────────────────────────────────────┤
│ [P1] 补充 documents 命令的置信度标注                 │
│      每条提取结果标注：EXTRACTED / PATTERN / INFERRED│
│      让用户知道什么可靠什么靠猜                      │
├──────────────────────────────────────────────────────┤
│ [P2] 看 Phase 2 的剩余项目——install 命令 / MCP 探测 │
└──────────────────────────────────────────────────────┘
```
