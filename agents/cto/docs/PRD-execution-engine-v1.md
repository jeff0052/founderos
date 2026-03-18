# PRD: CTO Agent 执行引擎补全

**版本**: v1.0 | **日期**: 2026-03-18  
**产品负责人**: Jeff | **执行者**: CTO Agent  
**上游文档**: CTO-AGENT-PRD-V2.md, CDRE Methodology, Superpowers (obra/superpowers)

---

## 1. 背景

### 1.1 现状

CTO Agent 拥有完整的战略框架：
- **CDRE 方法论** — 契约→规约→实现→验证，四层架构
- **Constitution** — 22 条铁律，含 3 条代码化拦截器
- **FPMS 集成** — 任务全生命周期追踪
- **决策分级** — L0-L3 四级权限体系
- **CODE-REVIEW-STANDARD** — 五维审查清单 + P0-P3 分级
- **GIT-WORKFLOW** — 分支策略 + commit 规范

但缺少**执行引擎**——CTO Agent 无法实际 dispatch subagent 完成开发任务。具体缺失：

| 缺失项 | 影响 |
|--------|------|
| 无 subagent prompt 模板 | 不知道怎么给 subagent 下指令 |
| 无状态码协议 | subagent 完成/失败后不知道怎么处理 |
| 无 plan 文档格式 | plan 粒度不可控，subagent 无法直接执行 |
| 无模型选择策略 | 所有任务用同一模型，浪费或不足 |
| 无物理隔离机制 | subagent 直接改 main，失败无法回滚 |
| AGENTS.md Phase 3 是空壳 | 写了"spawn coding agents"但没有具体执行协议 |

### 1.2 参考

业界最佳实践 **Superpowers** (github.com/obra/superpowers) 在执行引擎层面解决了上述问题：
- 具体的 prompt 模板（implementer / spec-reviewer / code-quality-reviewer）
- 4 种状态码（DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED）+ 处理策略
- Plan 文档含完整代码、文件路径、运行命令、预期输出
- 模型分级使用（机械任务用便宜模型，架构/审查用强模型）
- Git worktree 物理隔离

Superpowers 的弱项（我们已有的）：无领域约束、无项目管理、无记忆系统、无治理体系。

### 1.3 目标

**给 CTO Agent 的管理手册装上执行引擎。** 补全 subagent 调度、审查循环、plan 格式、物理隔离，使 CTO Agent 能端到端执行 CDRE Phase 3（AI 实现）。

---

## 2. 做什么

### 2.1 Subagent Prompt 模板

**三个模板文件**，每个模板融入 CDRE + Constitution 体系：

#### 2.1.1 implementer.md（实现者模板）

给 subagent 的完整指令，包含：

- **任务描述** — 从 plan 中提取的完整任务文本（不让 subagent 自己去读文件）
- **上下文** — 这个任务在整体架构中的位置、依赖关系
- **Module Spec 约束** — 职责、行为规则、**显式排除**（防止过度工程化）
- **Constitution 约束** — 适用于本任务的铁律子集（如支付任务必须包含浮点数禁令、幂等要求）
- **TDD 要求** — 先写测试、看到失败、再写实现
- **提问许可** — 明确允许 subagent 在开始前和执行中提问
- **升级许可** — 明确允许 subagent 说"这个太难了，我做不了"
- **Self-review 清单** — 完成前自查：完整性、质量、是否越界
- **报告格式** — 状态码 + 做了什么 + 测试结果 + 改了哪些文件 + 发现的问题

#### 2.1.2 spec-reviewer.md（规约审查者模板）

- **输入** — 任务的 Module Spec + implementer 的报告 + 实际代码
- **核心原则** — "不要信 implementer 的报告，自己读代码验证"
- **审查顺序**（CDRE 特化）：
  1. **反向阻断（最先查）** — 有没有实现"显式排除"中禁止的功能？有就直接 REJECT
  2. **完整性** — 所有 spec 要求是否都实现了？
  3. **过度工程化** — 有没有加 spec 之外的功能？
  4. **Constitution 合规** — 适用铁律是否遵守？
- **输出** — ✅ Spec compliant / ❌ Issues found（含具体文件:行号）

#### 2.1.3 code-quality-reviewer.md（质量审查者模板）

- **前置条件** — 只有 spec review 通过后才 dispatch
- **输入** — 任务描述 + 变更的 git diff（BASE_SHA → HEAD_SHA）
- **审查维度** — 对接 CODE-REVIEW-STANDARD.md 的五维：
  1. Spec 合规（已由 spec-reviewer 覆盖，此处跳过）
  2. 安全边界（浮点数、硬编码密钥、静默吞异常）
  3. 代码质量（单一职责、循环依赖、错误处理、注释）
  4. 架构健康（复杂度预算、模块边界）
  5. 测试质量（铁律防篡改、防过度 Mock、边界覆盖）
- **输出** — P0-P3 分级 findings + Approve / Approve with debt / Reject
- **P0 = 阻断**，P1 = 修完再审，P2 = 录入 FPMS backlog

### 2.2 Subagent 状态码协议

#### 2.2.1 四种状态码

| 状态码 | 含义 | CTO Agent 处理 |
|--------|------|----------------|
| **DONE** | 正常完成 | 进入 spec review |
| **DONE_WITH_CONCERNS** | 完成但有疑虑 | 先读 concerns，评估后决定是否进入 review 或修改 |
| **NEEDS_CONTEXT** | 缺信息无法继续 | 补充上下文，重新 dispatch 同一 subagent |
| **BLOCKED** | 卡住无法完成 | 按升级路径处理（见下） |

#### 2.2.2 BLOCKED 升级路径（按顺序尝试）

```
① 补充 context → 重新 dispatch 同模型
② 换更强模型重新 dispatch
③ 拆成更小的子任务
④ 升级给 Jeff（人类介入）
```

每次升级同时更新 FPMS task 状态（active → waiting）。

#### 2.2.3 审查循环

```
Implementer 完成
    → Spec Reviewer 审查
        → ❌ 不通过 → Implementer 修复 → Spec Reviewer 重审（最多 3 轮）
        → ✅ 通过 → Code Quality Reviewer 审查
            → ❌ 不通过 → Implementer 修复 → Quality Reviewer 重审（最多 3 轮）
            → ✅ 通过 → 标记任务完成，更新 FPMS
    → 超过 3 轮 → 升级给 Jeff
```

### 2.3 Plan 文档格式标准

#### 2.3.1 Plan 头部（必须）

```markdown
# [Feature Name] Implementation Plan

**Goal:** 一句话描述
**Architecture:** 2-3 句话描述方案
**Tech Stack:** 关键技术
**FPMS Task:** task-xxxx
**Module Spec:** 引用路径
**Complexity Budget:** 模块数上限 / 最大文件行数 / 依赖深度上限

---
```

#### 2.3.2 Task 格式（每个 task 必须包含）

```markdown
### Task N: [组件名]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:行号范围`
- Test: `tests/exact/path/to/test_file.py`

**显式排除:** 这个 task 不做什么

**Constitution 约束:** 适用的铁律编号

- [ ] Step 1: 写失败测试
  （完整测试代码）

- [ ] Step 2: 运行测试，确认失败
  Run: `具体命令`
  Expected: FAIL with "具体错误信息"

- [ ] Step 3: 写最小实现
  （完整实现代码）

- [ ] Step 4: 运行测试，确认通过
  Run: `具体命令`
  Expected: PASS

- [ ] Step 5: 运行全量测试，确认无回归
  Run: `具体命令`
  Expected: 全绿

- [ ] Step 6: Commit
  `git add ... && git commit -m "type(scope): description"`
```

#### 2.3.3 粒度标准

- 每步 2-5 分钟
- 零上下文的 agent 也能执行
- 代码内联在 plan 中，不是"实现 XX 功能"
- 每步有精确的验证命令和预期输出

### 2.4 模型选择策略

| 任务类型 | 模型 | 理由 |
|----------|------|------|
| 机械实现（1-2 文件，spec 完整） | Sonnet | 快、便宜、spec 完整时够用 |
| 集成任务（多文件协调） | Sonnet | 标准推理即可 |
| 架构设计、Brainstorming | Opus | 需要深度推理 |
| Spec Review | Sonnet | 对照检查，不需要创造力 |
| Code Quality Review | Sonnet | 模式匹配为主 |
| 复杂调试（3+ 次修复失败） | Opus | 需要架构级思考 |
| Plan 编写 | Opus | 需要全局视角 |

**原则：用能完成任务的最便宜模型。** Sonnet 失败时升级 Opus，不反过来。

### 2.5 Git Worktree 集成

#### 2.5.1 生命周期

```
开始任务
  → git worktree add ../worktrees/<task-id> -b feat/task-<id>
  → 在 worktree 中验证测试基线（全绿才继续）
  → subagent 在 worktree 中工作
  → 审查通过
  → git checkout main && git merge feat/task-<id>
  → git worktree remove ../worktrees/<task-id>

审查不通过且放弃
  → git worktree remove ../worktrees/<task-id>
  → git branch -D feat/task-<id>
```

#### 2.5.2 规则

- 每个 FPMS task 一个 worktree + 一个 branch
- Branch 命名：`feat/task-<fpms-id>-<short-description>`
- Subagent 只在 worktree 中操作，不碰 main
- 合并前必须通过全量测试
- 失败的 worktree 可以干净丢弃

### 2.6 AGENTS.md Phase 3 改写

将当前 Phase 3 的空壳描述替换为具体的执行协议，引用上述模板和协议文件。

---

## 3. 不做什么

| 项 | 原因 |
|----|------|
| 不改 SOUL.md | 战略层不动 |
| 不改 CONSTITUTION.md | 铁律不动 |
| 不改 CDRE 方法论 | 方法论不动，只补执行层 |
| 不做 Runtime 注册 | 另一个独立任务 |
| 不做流程 Gate 代码化拦截器 | 另一个独立任务 |
| 不做 brainstorming skill | Phase 0 已覆盖 |
| 不做 skill 自动触发系统 | 我们用 FPMS task 驱动，不用上下文匹配 |
| 不引入 Superpowers 的 TodoWrite | 我们用 FPMS |
| 不做 visual companion | 现阶段不需要 |

---

## 4. 成功标准

1. CTO Agent 拿到一个 FPMS task + plan，能按模板 dispatch implementer subagent
2. Subagent 用 4 种状态码报告结果
3. 完成后自动走 spec review → code quality review 循环（最多 3 轮）
4. 失败/卡住时有明确的升级路径
5. 所有工作在 git worktree 中隔离，不污染 main
6. 所有模板融入 CDRE 体系（Module Spec、显式排除、Constitution 约束）
7. FPMS task 状态在全程中自动更新

---

## 5. 交付物

| 文件 | 类型 | 说明 |
|------|------|------|
| `agents/cto/prompts/implementer.md` | 新建 | 实现者 subagent 指令模板 |
| `agents/cto/prompts/spec-reviewer.md` | 新建 | 规约审查 subagent 指令模板 |
| `agents/cto/prompts/code-quality-reviewer.md` | 新建 | 质量审查 subagent 指令模板 |
| `agents/cto/prompts/plan-template.md` | 新建 | Plan 文档格式标准 + 示例 |
| `agents/cto/SUBAGENT-PROTOCOL.md` | 新建 | 状态码 + 处理策略 + 模型选择 + worktree 流程 |
| `agents/cto/AGENTS.md` | 修改 | Phase 3 接入执行引擎 |

---

## 6. 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 模板太重，subagent context 爆炸 | 中 | 执行质量下降 | 模板只包含当前任务相关的约束子集，不全量塞入 |
| Worktree 操作出错（merge 冲突等） | 低 | 代码丢失 | 合并前全量测试 + main 永远可回退 |
| 审查循环卡在第 3 轮 | 中 | 任务停滞 | 超限自动升级人类 |
| Sonnet 能力不足以执行复杂实现 | 低 | 任务失败 | 升级路径已定义（→ Opus） |

---

## 7. 约束

- 所有新文件必须纳入 git 版本控制
- 模板内容不得违反现有 Constitution 任何条款
- 不引入外部依赖（纯 Markdown 文档）
- 与现有 CODE-REVIEW-STANDARD.md 和 GIT-WORKFLOW.md 保持一致，不重复不矛盾

---

*本 PRD 定义 CTO Agent 执行引擎的补全范围。审批后进入方案设计。*
