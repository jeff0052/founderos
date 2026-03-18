# 技术方案：CTO Agent 执行引擎

**版本**: v1.0 | **日期**: 2026-03-18  
**上游 PRD**: PRD-execution-engine-v2.md  
**设计者**: CEO Agent (Main) | **审批**: Jeff

---

## 0. 设计原则

1. **文档即协议** — 所有执行规则以 Markdown 文件形式存在，不引入代码依赖
2. **最小上下文** — subagent 只看到与当前 task 相关的信息，不全量透传
3. **可审计** — 每次状态流转记录在 FPMS narrative 中
4. **渐进式** — 先跑通 L1/L2 轻量流程，再验证 L3/L4 重流程

---

## 1. 文件结构

```
agents/cto/
├── SOUL.md                          # 不动
├── CONSTITUTION.md                  # 不动
├── AGENTS.md                        # 修改 Phase 3
├── CODE-REVIEW-STANDARD.md          # 不动（被 reviewer 模板引用）
├── GIT-WORKFLOW.md                  # 不动（被 worktree 流程引用）
├── SUBAGENT-PROTOCOL.md             # 新建：执行协议总纲
├── prompts/
│   ├── implementer.md               # 新建：实现者模板
│   ├── spec-reviewer.md             # 新建：规约审查模板
│   ├── code-quality-reviewer.md     # 新建：质量审查模板
│   └── plan-template.md             # 新建：Plan 格式标准
└── docs/
    ├── PRD-execution-engine-v2.md   # 已有
    └── DESIGN-execution-engine-v1.md # 本文件
```

---

## 2. SUBAGENT-PROTOCOL.md 设计

这是执行引擎的核心文件，CTO Agent 每次进入 Phase 3 时加载。

### 2.1 内容结构

```markdown
# Subagent Protocol — CTO Agent 执行协议

## 1. 任务接入（Task Intake）
  - 输入契约字段表
  - 不满足契约时的处理规则
  - 任务分级定义（L1-L4）+ 自动升级规则

## 2. 上下文交接载荷（Context Handoff Payload）
  - 裁剪规则
  - 载荷组装模板

## 3. 状态机
  - 状态定义
  - 流转规则
  - 禁止的流转
  - 与 FPMS 的映射

## 4. 审查循环
  - 流程图
  - 最大迭代次数
  - 熔断规则

## 5. 升级边界
  - BLOCKED vs FAILED
  - 升级到 CTO Agent 的条件
  - 必须升级到 Jeff 的条件
  - 升级时的上下文要求

## 6. 模型选择与降级
  - 默认选择表
  - 高风险强制模型
  - Fallback 顺序
  - Token Budget
  - 重试上限

## 7. Git Worktree
  - 生命周期
  - 命名规则
  - 清理规则
```

### 2.2 上下文交接载荷（Context Handoff Payload）— 新增设计

这是 Gemini 审查指出的关键缺失。CTO Agent 拥有全局视野，但 dispatch 时必须裁剪。

**裁剪原则：subagent 看到的 = 完成任务所需的最小信息集**

#### 2.2.1 Implementer Payload 组装规则

```
[REQUIRED] Task 全文（从 plan 中提取，不让 subagent 自己读文件）
[REQUIRED] Module Spec 片段（仅当前模块的职责/行为规则/显式排除/约束）
[REQUIRED] Constitution 子集（仅与当前 task 相关的条款，不全量塞入）
[REQUIRED] 测试基线（当前测试命令 + 预期结果）
[REQUIRED] 工作目录（worktree 路径）
[OPTIONAL] 依赖模块接口（仅接口签名，不含实现）
[OPTIONAL] 相关 ADR（仅当 task 涉及该决策时）
[NEVER]    其他模块的 Module Spec
[NEVER]    FPMS 看板全貌
[NEVER]    CTO Agent 的 SOUL.md / MEMORY.md
[NEVER]    其他 task 的 plan
```

**Token 预算分配（implementer）：**

| 组件 | 预算 |
|------|------|
| 系统指令（模板框架） | ~2k tokens |
| Task 全文 | ~2-5k tokens |
| Module Spec 片段 | ~1-2k tokens |
| Constitution 子集 | ~0.5-1k tokens |
| 依赖接口 | ~0.5-1k tokens |
| **总输入** | **~6-10k tokens** |
| 留给 subagent 工作 | **~40k tokens** |

#### 2.2.2 Reviewer Payload 组装规则

```
[REQUIRED] Task 原始 spec（用于对照）
[REQUIRED] Implementer 的结构化报告
[REQUIRED] Git diff（实际代码变更）
[REQUIRED] 适用的 Constitution 条款
[REQUIRED] 显式排除列表
[OPTIONAL] 测试输出 log
[NEVER]    Implementer 的 prompt（避免偏见）
[NEVER]    其他 task 信息
```

#### 2.2.3 Constitution 子集选择规则

根据 task 属性自动选择适用条款：

| task 属性 | 包含的 Constitution 条款 |
|-----------|------------------------|
| 所有 task | §4(契约优先) §5(铁律测试不改) §6(CLAUDE.md 同步) §7(显式排除) §8(先 design) §9(TDD) |
| task_type = feat | + §21(复杂度预算) §22(能删就不加) |
| touched_modules 含支付 | + §3(支付核心变更) §11(密钥) §13(禁浮点数) |
| risk_level ≥ L3 | + §18(不超 3 个高风险) §19(Token 预算) |
| task_type = refactor | + §20(顺序不可跳) §22(能删就不加) |

---

## 3. Prompt 模板设计

### 3.1 implementer.md

```markdown
# Implementer Subagent Instructions

## Your Task

{TASK_FULL_TEXT}

## Context

{ARCHITECTURE_CONTEXT}

## Module Spec (Your Boundaries)

**Responsibilities:** {MODULE_RESPONSIBILITIES}
**Behavior Rules:** {MODULE_BEHAVIOR_RULES}
**Constraints:** {MODULE_CONSTRAINTS}

### ⛔ Explicit Exclusions (DO NOT implement these)
{MODULE_EXCLUSIONS}

## Constitution Constraints (Non-Negotiable)
{CONSTITUTION_SUBSET}

## Working Directory
{WORKTREE_PATH}

## Test Baseline
Run: `{TEST_COMMAND}`
Expected: {BASELINE_RESULT}
Verify this BEFORE starting any work. If tests are not green, STOP and report BLOCKED.

## How to Work

1. **TDD — no exceptions**
   - Write failing test first
   - Watch it fail (verify the failure message)
   - Write minimal code to pass
   - Watch it pass
   - Run full test suite — no regressions
   - Commit

2. **Stay in scope**
   - Implement ONLY what the task specifies
   - Do NOT add features not in the spec
   - Do NOT refactor code outside your task
   - Do NOT make architecture decisions — escalate instead

3. **Ask questions**
   - Before starting: if requirements are unclear, ASK
   - During work: if you hit something unexpected, ASK
   - It is always OK to pause and clarify

4. **Escalate when stuck**
   - If this is too hard for you — say so (BLOCKED)
   - If you need information not provided — say so (NEEDS_CONTEXT)
   - Bad work is worse than no work. You will not be penalized for escalating.

## Before Reporting: Self-Review Checklist

- [ ] Did I implement everything in the spec?
- [ ] Did I implement anything NOT in the spec?
- [ ] Did I violate any Constitution constraint?
- [ ] Did I implement anything from the Explicit Exclusions?
- [ ] Do all tests pass (including full suite)?
- [ ] Is my code the minimal implementation needed?
- [ ] Are file-level comments present (what this module does, doesn't do)?
- [ ] Did I commit my work?

## Report Format (MANDATORY)

```
## Report
- **Status:** DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- **Understood Objective:** (restate in your own words)
- **Change Scope:** (exact file paths + line ranges)
- **Explicit Non-Changes:** (what I deliberately did NOT do)
- **Risk Flags:** (anything that concerns me)
- **Change Summary:** (one sentence per file)
- **Test Results:** (command + output + pass/fail counts)
- **Reviewer Attention:** (what reviewer should focus on)
- **Self-Review Findings:** (issues found, fixed or unfixed)
- **Unfinished Items:** (if any)
- **Next Action Recommendation:** (what should happen next)
```
```

**设计决策：**
- 占位符用 `{VARIABLE}` 格式，CTO Agent dispatch 时填充
- Constitution 子集按 §2.2.3 规则自动选择，不全量塞入
- Self-review checklist 反向检查"有没有做不该做的"（CDRE 特化）
- 报告格式完全匹配 PRD §2.4.1 输出契约

### 3.2 spec-reviewer.md

```markdown
# Spec Compliance Reviewer Instructions

## What Was Requested

{TASK_SPEC}

## Acceptance Criteria

{ACCEPTANCE_CRITERIA}

## Explicit Exclusions (Must NOT be implemented)

{EXCLUSIONS}

## Applicable Constitution Clauses

{CONSTITUTION_SUBSET}

## Implementer's Report

{IMPLEMENTER_REPORT}

## ⚠️ CRITICAL: Do Not Trust the Report

The implementer's report may be incomplete, inaccurate, or optimistic.
You MUST verify everything independently by reading the actual code.

**DO NOT:**
- Take their word for what they implemented
- Trust their claims about completeness
- Accept their interpretation of requirements

**DO:**
- Read the actual code changes
- Compare implementation to spec line by line
- Check for missing pieces
- Look for extra features not in spec

## Review Order (MANDATORY — follow this exact sequence)

### Step 1: Reverse Block Check (FIRST)
Did the implementer build anything from the Explicit Exclusions list?
→ If YES: immediate FAIL, do not continue review.

### Step 2: Completeness Check
For each acceptance criterion:
- Is it implemented? (cite file:line)
- Does the implementation match the spec? (cite spec clause)

### Step 3: Over-Engineering Check
Did the implementer add:
- Features not in the spec?
- Abstraction layers not requested?
- "Nice to have" improvements?
→ If YES: FAIL with specific findings.

### Step 4: Constitution Compliance
For each applicable Constitution clause:
- Is it respected? (cite evidence)

## Evidence Requirements

Every finding MUST include:
- **Spec clause:** which requirement is affected
- **Code location:** file:line
- **Deviation:** what's wrong (specific, not vague)

## Report Format (MANDATORY)

```
## Spec Review Verdict
- **Verdict:** PASS | FAIL
- **Spec Reference:** (document paths used for review)
- **Evidence:**
  - Blocking Issues: [file:line + problem + spec clause]
  - Non-Blocking Issues: [file:line + problem + spec clause]
- **Out-of-Scope Check:** (did they build excluded features? yes/no + evidence)
- **Constitution Check:** (per-clause pass/fail)
- **Required Changes:** (specific items to fix)
- **Status:** PASS | FAIL | ESCALATE
- **Next Action Recommendation:** (what should happen next)
```
```

**设计决策：**
- "Do Not Trust the Report" — 直接借鉴 Superpowers 的核心洞察
- Review 顺序强制：先查排除项（CDRE 特化），再查完整性
- 不给 reviewer 看 implementer 的 prompt（避免认知偏见）

### 3.3 code-quality-reviewer.md

```markdown
# Code Quality Reviewer Instructions

## Prerequisite
This review ONLY happens after spec compliance review has PASSED.
If spec review has not passed, do NOT proceed.

## What Was Implemented

{TASK_DESCRIPTION}

## Code Changes

Base SHA: {BASE_SHA}
Head SHA: {HEAD_SHA}

Review the git diff between these commits.

## Applicable Constitution Clauses

{CONSTITUTION_SUBSET}

## Review Dimensions

Review in this order. For each finding, assign severity P0-P3.

### 1. Safety Boundaries
- [ ] Float arithmetic for money? (Constitution §13 — P0 if found)
- [ ] Hardcoded secrets/keys? (Constitution §11 — P0 if found)
- [ ] Silent exception swallowing on critical paths? (P0 if found)
- [ ] Direct production environment access? (Constitution §12 — P0 if found)
- [ ] Payment-specific: idempotency? state machine integrity? reconciliation?

### 2. Code Quality
- [ ] Single responsibility per module?
- [ ] Circular dependencies?
- [ ] Import style consistency?
- [ ] Error handling (no bare except, no swallowed errors)?
- [ ] Comments: module header (what/not-what/interactions), key functions (why not what)

### 3. Architecture Health
- [ ] Within Complexity Budget? (module count / max file LOC / dependency depth)
- [ ] New modules have Module Spec?
- [ ] CLAUDE.md / ARCHITECTURE.md updated?
- [ ] Irreversible coupling introduced?

### 4. Test Quality
- [ ] Invariant test files modified? (Constitution §5 — P0 if found)
- [ ] Over-mocking? (mock everything + assert call_count = waste test)
- [ ] Boundary conditions tested? (extremes, negatives, concurrency, timeouts)
- [ ] Error paths tested?
- [ ] Tests independently runnable? (no execution order dependency)

## Severity Classification

| Level | Meaning | Action |
|-------|---------|--------|
| **P0** | Cannot ship | Float money, bypassed Tool Call, state machine error, contract mismatch, hardcoded secret, missing invariant test, excluded feature built, invariant test tampered |
| **P1** | Must fix before merge | Module boundary violation, circular dependency, missing critical path, idempotency gap, doc not synced, silent exception swallow |
| **P2** | Can merge, must log to FPMS | Module too large, heavy abstraction, insufficient comments, weak boundary tests |
| **P3** | Optional | Naming improvements, local structure optimization |

## Evidence Requirements

Every finding MUST include:
- **Severity:** P0 / P1 / P2 / P3
- **Category:** Safety / Quality / Architecture / Tests
- **Location:** file:line
- **Problem:** (one sentence)
- **Fix suggestion:** (specific)

## Verdict Rules

- Any P0 → **Reject**
- Any P1 → **Reject** (fix then re-review)
- Only P2/P3 → **Approve with debt** (P2 items logged to FPMS)
- Nothing found → **Approve**

## Report Format (MANDATORY)

```
## Quality Review Verdict
- **Verdict:** Approve | Approve with debt | Reject
- **Highest Severity:** P0 / P1 / P2 / P3
- **Evidence:**
  - Findings: [severity + category + file:line + problem + fix suggestion]
- **Constitution Compliance:** [per-clause check result]
- **Complexity Assessment:** modules / max file LOC / dependency depth
- **FPMS Debt Items:** [P2 items to log in FPMS backlog]
- **Required Changes:** [P0/P1 items that must be fixed]
- **Status:** APPROVE | REJECT | ESCALATE
- **Next Action Recommendation:** (what should happen next)
```
```

**设计决策：**
- 完全对接现有 CODE-REVIEW-STANDARD.md，不重新发明
- P0-P3 分级和 verdict 规则与现有标准一致
- 跳过 Spec 合规维度（已由 spec-reviewer 覆盖，避免重复）
- Constitution §5（铁律测试防篡改）和 §13（浮点数）标为 P0

### 3.4 plan-template.md

```markdown
# Plan 文档格式标准

## 头部（必须）

# [Feature Name] Implementation Plan

> **For subagents:** Each task will be dispatched to a fresh subagent
> via implementer.md template. Use TDD for all implementation.

**Goal:** 一句话
**Architecture:** 2-3 句话
**Tech Stack:** 关键技术
**FPMS Task:** task-xxxx
**Module Spec:** 路径
**Risk Level:** L1-L4
**Complexity Budget:** 模块数上限 / 最大文件 LOC / 依赖深度上限
**Test Baseline:** `命令` → 预期结果

---

## File Structure（实现前锁定）

列出所有将创建或修改的文件，每个文件一句话说明职责。

## Tasks

### Task N: [组件名]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:行号范围`
- Test: `tests/exact/path/to/test_file.py`

**Explicit Exclusions:** 这个 task 不做什么
**Constitution Constraints:** 适用铁律编号
**Depends on:** Task X（如有依赖）

- [ ] Step 1: Write failing test
  ```python
  # 完整测试代码
  ```

- [ ] Step 2: Run test, verify failure
  Run: `pytest tests/path/test_file.py::test_name -v`
  Expected: FAIL with "具体错误信息"

- [ ] Step 3: Write minimal implementation
  ```python
  # 完整实现代码
  ```

- [ ] Step 4: Run test, verify pass
  Run: `pytest tests/path/test_file.py::test_name -v`
  Expected: PASS

- [ ] Step 5: Run full suite, no regressions
  Run: `pytest tests/ -q`
  Expected: all passed

- [ ] Step 6: Commit
  ```bash
  git add tests/path/test_file.py src/path/file.py
  git commit -m "feat(scope): description"
  ```

## 粒度标准

- 每步 2-5 分钟
- 代码内联，不是"实现 XX 功能"
- 每步有精确验证命令 + 预期输出
- 零上下文 agent 也能执行
```

---

## 4. AGENTS.md Phase 3 改写

### 4.1 现有内容（要替换的部分）

```markdown
### Phase 3: AI 实现（10% 时间）
- 将契约（精简版）+ Module Spec + 测试用例组装为完整 prompt
- **Subagent-Driven Development:**
  - 每个 task spawn 一个新 agent（隔离 context）
  - agent 完成后双重审查:
    1. **Spec 合规审查** ...
    2. **代码质量审查** ...
  - 两轮都过才标记完成
- **TDD 铁律: 先写了代码？删掉，从测试重来**
- **不满意就重新生成，不要手动修补**
- 每批完成后更新 FPMS task 状态
```

### 4.2 替换为

```markdown
### Phase 3: AI 实现（Subagent-Driven Development）

**协议文件:** `SUBAGENT-PROTOCOL.md`  
**Prompt 模板:** `prompts/implementer.md`, `prompts/spec-reviewer.md`, `prompts/code-quality-reviewer.md`

#### 3.0 前置检查
- [ ] Task 满足输入契约（SUBAGENT-PROTOCOL §1）
- [ ] Risk level 已确认（L1-L4）
- [ ] Plan 已完成（`prompts/plan-template.md` 格式）
- [ ] L3/L4 任务：Plan 已经 Jeff 确认

#### 3.1 环境准备
```bash
git worktree add ../worktrees/task-<id> -b feat/task-<id>-<desc>
cd ../worktrees/task-<id>
# 验证测试基线
<test_command>  # 必须全绿
```

#### 3.2 Dispatch Implementer
1. 按 SUBAGENT-PROTOCOL §2 组装 Context Handoff Payload
2. 填充 `prompts/implementer.md` 模板
3. 选择模型（SUBAGENT-PROTOCOL §6）
4. Dispatch subagent
5. 更新 FPMS narrative：`状态: IMPLEMENTING`

#### 3.3 处理 Implementer 结果
| Status | Action |
|--------|--------|
| DONE | → 3.4 Spec Review |
| DONE_WITH_CONCERNS | 读 concerns → 评估 → 3.4 或 修改后重新 dispatch |
| NEEDS_CONTEXT | 补充信息 → 重新 dispatch（同模型） |
| BLOCKED | 按升级路径处理（SUBAGENT-PROTOCOL §5） |

#### 3.4 Spec Review
1. 组装 Reviewer Payload（SUBAGENT-PROTOCOL §2.2.2）
2. 填充 `prompts/spec-reviewer.md`
3. Dispatch spec-reviewer subagent
4. 更新 FPMS narrative：`状态: SPEC_REVIEW`

| Verdict | Action |
|---------|--------|
| PASS | → 3.5 Quality Review |
| FAIL | Implementer 修复 → 重新 Spec Review（最多 3 轮） |
| 3 轮不收敛 | → ESCALATED → 通知 Jeff |

#### 3.5 Code Quality Review
1. 获取 git diff（BASE_SHA → HEAD_SHA）
2. 填充 `prompts/code-quality-reviewer.md`
3. Dispatch quality-reviewer subagent
4. 更新 FPMS narrative：`状态: QUALITY_REVIEW`

| Verdict | Action |
|---------|--------|
| Approve | → 3.6 完成 |
| Approve with debt | → 3.6 完成 + 录入 FPMS backlog |
| Reject | Implementer 修复 → 重新 Quality Review（最多 3 轮） |
| P0 found | → ESCALATED → 通知 Jeff |

#### 3.6 完成
```bash
cd <main-repo>
git merge feat/task-<id>-<desc>
git worktree remove ../worktrees/task-<id>
```
- 更新 FPMS task 状态：`done`
- 更新 FPMS narrative：完成摘要
- 下一个 task

#### 3.7 放弃
```bash
git worktree remove ../worktrees/task-<id>
git branch -D feat/task-<id>-<desc>
```
- 更新 FPMS task 状态：`dropped`
- 记录原因
```

---

## 5. 关键设计决策（ADR 级别）

### ADR-EE-001: 文档协议 vs 代码实现

**决定**: 执行引擎以 Markdown 文档形式实现，不写代码。

**理由**:
- CTO Agent 本身是 LLM，通过 prompt 驱动，文档即执行指令
- 不引入新的代码依赖，保持系统简单
- 文档可以被人类直接阅读和修改
- 状态机流转由 CTO Agent 按文档规则执行，FPMS narrative 提供审计

**后果**: 状态机没有代码级强制力，依赖 CTO Agent 遵守。如果未来需要强制，可升级为代码拦截器（Constitution Guard 扩展）。

### ADR-EE-002: Context Handoff Payload 裁剪策略

**决定**: CTO Agent 在 dispatch 时负责裁剪上下文，遵循 NEVER/REQUIRED/OPTIONAL 三级规则。

**理由**:
- 全量透传会导致 subagent token 爆炸和指令失焦
- CTO Agent 拥有全局视野，是唯一有能力做裁剪的角色
- 裁剪规则文档化，可审计可迭代

**后果**: CTO Agent 的 dispatch 逻辑变复杂。如果裁剪不当，subagent 可能缺少必要信息。通过 NEEDS_CONTEXT 状态码回路解决。

### ADR-EE-003: 状态机不替代 FPMS

**决定**: 执行引擎状态机是 FPMS task 状态的细粒度补充，记录在 narrative 中，不修改 FPMS schema。

**理由**:
- FPMS 是跨项目的管理系统，不应被单个执行引擎的需求污染
- 10 个执行状态 vs FPMS 的 6 个生命周期状态，粒度不同
- Narrative 是自由文本，天然支持细粒度状态记录

**后果**: 状态查询不如字段级查询方便。但当前阶段 FPMS 的 narrative 足够用。

### ADR-EE-004: Reviewer 不看 Implementer 的 Prompt

**决定**: Spec-reviewer 和 quality-reviewer 不接收 implementer 的原始 prompt，只接收 task spec + implementer 的结构化报告 + 实际代码。

**理由**:
- 避免认知偏见（reviewer 被 prompt 中的"预期行为"影响判断）
- Reviewer 应独立对照 spec 评判，不受 implementer 上下文干扰
- Superpowers 同样采用此设计

**后果**: Reviewer 可能对某些实现选择缺乏背景理解。但这是 feature not bug——如果实现需要额外背景才能理解，说明代码不够自解释。

---

## 6. 实现计划

### 6.1 批次划分

| 批次 | 交付物 | 依赖 |
|------|--------|------|
| Batch 1 | SUBAGENT-PROTOCOL.md | 无 |
| Batch 2 | prompts/implementer.md + prompts/plan-template.md | Batch 1 |
| Batch 3 | prompts/spec-reviewer.md + prompts/code-quality-reviewer.md | Batch 1 |
| Batch 4 | AGENTS.md Phase 3 改写 | Batch 1-3 |

### 6.2 验证方式

由于交付物全部是 Markdown 文档（不是代码），验证方式是：

1. **文档自洽检查** — 模板中的占位符是否都有对应的组装规则
2. **交叉引用检查** — 模板引用的 Constitution 条款、CODE-REVIEW-STANDARD 维度是否正确
3. **Dry Run** — 拿一个真实的 FPMS task（如 task-a489: MCP Server 升级），走完整个流程：
   - 填充输入契约
   - 确定 risk level
   - 组装 implementer payload
   - 模拟 implementer 输出
   - 模拟 spec review
   - 模拟 quality review
   - 验证状态机流转
4. **Jeff Review** — 最终人工审查

### 6.3 Dry Run 计划

**选定任务**: task-a489（接入方式升级为 MCP Server）
- 理由：L2 级别，跨文件但边界清晰，不涉支付核心，适合首次验证
- 验证点：输入契约填充 → plan 生成 → implementer dispatch → review 循环 → worktree 合并

---

## 7. 风险与缓解（方案级）

| 风险 | 缓解 |
|------|------|
| 模板过长导致 subagent context 不够用 | Token 预算分配已定义（§2.2.1），implementer 输入控制在 ~10k |
| CTO Agent 裁剪上下文时遗漏关键信息 | NEEDS_CONTEXT 回路兜底 + 迭代改进裁剪规则 |
| 状态机靠 prompt 约束不够硬 | 先跑通验证，如果频繁违规再代码化（Constitution Guard 扩展） |
| Plan 中内联代码质量不够 | Plan 由 Opus 生成（需要全局视角），实现由 Sonnet 执行 |
| Dry Run 暴露大量问题需要返工 | 这是 feature——先用轻量 task 暴露问题，比直接上支付系统安全 |

---

*本方案基于 PRD-execution-engine-v2.md，定义 CTO Agent 执行引擎的具体实现设计。审批后进入实现。*
