# Monorepo 迁移方案

> 将 codeanalyze/kronos/agora/eidos/ontoderive/pallas/minerva 合并

---

## 现状

| 项目 | 行数 | 状态 |
|------|------|------|
| codeanalyze | 6,600 | v0.3.0, 活跃 |
| kronos | ~5K | 知识摄取管线，活跃 |
| agora | ~3K | MCP Hub，活跃 |
| eidos | ~3K | Schema 校验层，活跃 |
| ontoderive | ~4K | 知识推理引擎，活跃 |
| pallas | 331 | 薄 CLI 桥接层，可合并到 agora |
| minerva | ~10K | 深度研究系统，活跃 |
| gateway | <1K | 仅脚本，可废弃/合并到 agora |
| MetaOS | 5.7K | 元操作系统，待评估活跃度 |
| sophia | ~3K | 符号化研究，待评估 |
| SharedBrain | 71K | 保持独立（体积太大） |
| agentmesh | 120K (TS) | 独立 monorepo |

**总计**: Python ~36K (不含 SharedBrain) + SharedBrain 71K = 107K Python

---

## 目标结构

```
Workspace/agentmesh-python/     ← 新 monorepo 名
├── pyproject.toml              ← 根配置（workspace = true）
├── .venv/                      ← 单一 venv
├── Makefile                    ← 单根 Makefile
├── .pre-commit-config.yaml     ← 统一 pre-commit
├── packages/
│   ├── core-models/            ← Entity/Relation/Provenance 共享模型
│   │   ├── pyproject.toml
│   │   └── src/core_models/
│   ├── codeanalyze/            ← 代码分析 CLI
│   ├── kronos/                 ← 知识摄取管线
│   ├── agora/                  ← MCP Hub（含 gateway 功能）
│   ├── eidos/                  ← Schema 校验
│   ├── ontoderive/             ← 知识推理
│   ├── minerva/                ← 深度研究
│   └── sophia/                 ← 符号化研究
├── tools/                      ← 独立脚本
│   └── pallas.sh               ← pallas CLI 作为 alias
└── bin/
    └── converge.sh
```

---

## 迁移步骤

### Step 1: 创建 workspace 根配置（2h）

```bash
mkdir agentmesh-python && cd agentmesh-python
git init
# pyproject.toml with [tool.uv.workspace]
uv init --workspace
```

### Step 2: 创建 core-models 包（4h）

从 codeanalyze 的 `core/results.py` 提取 Entity/Relation/Provenance/KnowledgeGraph。
所有项目安装 `core-models` 作为依赖，删除各自重复实现。

### Step 3: 逐个迁移到 packages/（2h/包）

每个包：
```
cd agentmesh-python/packages/
cp -r /path/to/project .
git mv files
```

### Step 4: 统一 CI（1d）

- 单根 `.github/workflows/`
- 矩阵测试 `packages/*`
- ruff 统一配置

### Step 5: 废弃独立 repo（1h）

GitHub 层面将旧 repo 设为 archived。

---

## 风险

| 风险 | 缓解 |
|------|------|
| git 历史丢失 | 使用 `git mv` 或 subtree |
| 依赖冲突 | uv workspace 自动解析 |
| CI 中断 | 迁移期间双 CI 并行运行 |
| SharedBrain 依赖 | 通过 pypi 包引用 core-models，不强制入 repo |

---

## 时间估算

总工期：2-3 天（全职）
- 基础设施构建：半天
- core-models 提取：半天
- 逐个迁移：半天 × 6 包 = 1 天
- 统一 CI + 收尾：半天
