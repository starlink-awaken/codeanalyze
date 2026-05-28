# Bus Factor 治理 — 单人维护风险缓解

> 当前状态：1 人维护 4 个活跃 Python 项目 + 2 TS 项目

---

## 风险矩阵

| 场景 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 维护者休假 2 周 | 项目冻结 | 高 | 文档化 CI/CD + PR 流程 |
| 维护者离开 | 项目死亡 | 中 | 备份维护者 + 自动化 |
| 关键依赖上游 break | 功能损坏 3 个月 | 高 | CI 工具巡检 + schema 验证 |
| 安全漏洞需紧急修复 | 跨 7 项目修复 | 中 | 统一 CI 管线 |

---

## 行动项

### 1. 代码可继承性（当前可做）

- [x] CLAUDE.md — Agent 工作指令，完整
- [x] REDTEAM.md / REDTEAM_V2.md — 架构决策记录
- [ ] CHANGELOG.md — 保持更新（当前 OK）
- [ ] 每个项目 README 含"快速上手"（codeanalyze OK，其他需检查）
- [ ] AGENTS.md 覆盖关键文件位置（codeanalyze OK）

### 2. CI 自治（正在做）

- [x] codeanalyze — 105 测试 + CI
- [x] SharedBrain — 26 CI workflows
- [ ] kronos — 检查 CI 覆盖率
- [ ] agora/eidos/ontoderive — 检查 CI 状态

### 3. 文档化架构决策（需做）

- [ ] 关键架构 RFC 文档化（为什么选 MCP？为什么分层？）
- [ ] 外部工具依赖清单及替代方案
- [ ] 发布流程文档

### 4. 备份维护者（长期）

- [ ] 确定第二个有写入权限的人
- [ ] 文档化紧急发布流程
- [ ] CODEOWNERS 多点覆盖

---

## 生态位清理

以下项目应标记 `@deprecated` 或合并：

| 项目 | 建议 | 理由 |
|------|------|------|
| pallas (331 行) | 合并到 agora | 仅 CLI 桥接，无独立功能 |
| gateway (无 src) | 废弃 | 功能已被 agora 覆盖 |
| kos | 保持但标记 | 被 ontoderive 替代趋势 |
| eCOS | 废弃 | 未活跃开发 >30 天 |
| bos-skill-cli | 废弃 | 未活跃开发 >30 天 |

清理后可维护项目从 11 降到 6 个。
