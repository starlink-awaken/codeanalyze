# 架构治理 TODO — 重量级项目

> 生成时间: 2026-05-28
> 来源: 三轮红队攻击分析

---

## P0 — 需专项规划

### 1. 外部工具版本漂移监测

问题：10+ 外部工具（graphify/gitnexus/CRG/docling 等）各自独立发布，codeanalyze 没有上游变更检测机制。一个工具的 breaking change 可能在 3 个月后才被 silent 发现。

方案：
- 在 CI 中添加每周巡检：`codeanalyze status` 输出版本快照
- 对比上周版本列表，变化时自动开 issue
- 对每个外部工具输出做 JSON Schema 验证（加载前检测结构不兼容）

依赖：CI 基础设施 + 初步 schema 定义

---

### 2. 10 repo 合并为 monorepo

问题：10 个独立 Python git repo + 16 个 .venv，跨项目改动需手工同步。核心数据模型（Entity/Relation/Provenance）在各项目中独立实现，零共享。

方案：
- 参考 agentmesh 的 packages/* 布局
- 创建 `core-models` 共享包（Entity/Relation/Provenance）
- codeanalyze/pallas/kronos/agora/eidos/ontoderive/minerva 合并
- SharedBrain 保持独立（体积太大 + 发布状态不同）

工作估算：2-3 天

---

### 3. DomainRegistry 接入

问题：nucleus/Z-Microkernel/interfaces/domain_registry.py 215 行代码零引用。架构解耦从未真正发生，微内核仍直接 import organs。

方案：
- 添加 ruff rule 禁止器官层被微内核直接 import
- 逐个迁移 16 个文件中的器官 import 为 DomainRegistry 查找
- 或承认废弃，直接删除 215 行死代码

工作估算：1 天

---

## P1 — 需计划

### 4. ruff target-version 与实际运行时脱节

问题：pyproject.toml 设 `target-version = "py314"`，但所有 .venv 跑在 Python 3.13.13。ruff 可能格式化出 3.14 专属语法导致运行时 crash。

方案：已修复 → `py313`。所有 .venv 升级到 3.14 后再改回。

---

### 5. SharedBrain Markdown/YAML 治理

问题：14K+ MD + 1.6K YAML 文件零架构治理。pre-commit hooks 和 CI 全部只针对 .py。

方案：
- yamllint pre-commit hook
- markdownlint pre-commit hook
- 跨文档引用完整性检查
- governance-config.yaml 中声明的门禁检查器

---

### 6. CI 治理管线完善度

问题：governance.yml 的 ruff 规则已修复，但 pre-commit `--no-verify` 始终可跳过。需添加 `stages: [push]` 到核心架构 hook。

方案：（部分可快速修复）架构 hook 添加 push stage + CI 运行 pre-commit run --all-files

---

## P2 — 中长期

### 7. 单人维护风险

问题：240K 行 / 7+ 项目 / 1 人维护。没有统一发布管道、测试覆盖率不均、无备份维护者。

方案：
- 明确项目生命周期（标记废弃中间层项目）
- 统一测试管道
- 建立 CI 每周巡检

---

### 8. insights.py 非 SharedBrain 测评

问题：`_LAYER_RULES` 硬编码 SharedBrain。已添加跳过+报告说明，但非 SharedBrain 项目无架构分析。

方案：从 `pyproject.toml` 的 `[tool.codeanalyze.layers]` 段读取规则，或写死为通用指标（包大小、扇入/扇出）
