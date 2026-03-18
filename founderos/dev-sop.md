# FounderOS 开发 SOP

> 固定流程，不漂移。每次开发都走这个，不管大小。

---

## 核心原则：总分总

每一层、每一步都是总分总。做完"分"必须回到"总"，否则不算完成。

---

## Session 启动（每次）

```bash
# 1. 读上下文
读 MEMORY.md          # how — 工作约定
读 OVERVIEW.md        # where — 系统全景
python3 fpms/spine.py bootstrap  # what — FPMS 实时状态
```

不跳步。不凭记忆。

---

## 小任务（单文件，边界清晰）

```
总: 确认要做什么 + 为什么
分: 直接改 + 跑测试
总: 更新 MEMORY/OVERVIEW（如有变化）+ commit
```

---

## 大型开发（跨模块 / >3文件 / 新 interface）

### Phase 1 — 总：规划

| 步骤 | 产出 | 存放 | Jeff 确认 |
|------|------|------|-----------|
| 需求理解 | PRD | `docs/designs/YYYY-MM-DD-<topic>.md` | ✅ |
| 架构设计 | Design Doc | 同上 | ✅ |
| 任务拆解 | FPMS 任务 | `spine.py tool create_node` | ✅ |

**Jeff 确认后才能进 Phase 2。**

### Phase 2 — 分：执行

| 步骤 | 执行者 | 规则 |
|------|--------|------|
| 逐个任务实现 | CTO Agent (Claude Code) | 每个任务一个 session |
| 单元测试 | CTO Agent | 完成后自动跑 |
| Code Review | 主 Agent | 检查 Constitution 合规 |

每个任务完成后在 FPMS 更新状态。

### Phase 3 — 总：收尾

| 步骤 | 产出 |
|------|------|
| 全量测试 | `pytest -x` 全绿 |
| 更新 OVERVIEW.md | 架构/版本线/下一步 |
| 更新 MEMORY.md | 新约定/新教训 |
| 写 milestone 日志 | `reports/milestones/vX.Y.Z-<name>.md` |
| 更新 CHANGELOG.md | 版本记录 |
| commit + push | GitHub main |
| 通知 Jeff | 做了什么 + 全局变了什么 |

**没做 Phase 3，任务不算完成。**

---

## 铁律

1. **产出写文件**，不在聊天里飘
2. **Jeff 确认后才执行**（大型开发的 Phase 1）
3. **每次回到"总"**，更新全局文档
4. **任务状态只在 FPMS 里**，不维护第二份
5. **开发任务派 CTO Agent**，主 Agent 不自己写代码
6. **踩坑必须记录** → `memory/lessons/`

---

## 文档分工（不重叠）

```
FPMS          what — 任务实时状态
OVERVIEW.md   where — 系统架构和方向
MEMORY.md     how — 工作约定和教训
```
