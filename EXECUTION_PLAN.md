# 架构治理实施规划

> 基于 REDTEAM_TODO.md，按可操作性分级

---

## Phase 1 — 立刻执行（本 session）

| # | 项 | 操作 | 目标项目 |
|---|-----|------|---------|
| 1 | 外部工具版本巡检 | 创建 `.github/workflows/tool-audit.yml` | codeanalyze |
| 3 | DomainRegistry | 标记 `@deprecated`，更清晰说明 | SharedBrain |
| 5 | MD/YAML 治理 | pre-commit 添加 yamllint + markdownlint | SharedBrain |
| 6 | CI push stage | 核心 hook 添加 `stages: [push]` | SharedBrain |
| 8 | insights 通用化 | ✅ 已修复（跳过+说明） | codeanalyze |
| 4 | ruff target-version | ✅ 已修复（py313） | codeanalyze |

## Phase 2 — 制定详细方案（本 session 输出规划文档）

| # | 项 | 输出 |
|---|-----|------|
| 2 | 10 repo → monorepo | `MIGRATION_PLAN.md` |
| 3 | DomainRegistry 完整接入 | 更新 TODO 为具体步骤 |
| 7 | 单人维护风险 | `BUS_FACTOR.md` |

## Phase 3 — 后续 sprint 执行

monorepo 合并、DomainRegistry 真实迁移、测试覆盖率提升。
