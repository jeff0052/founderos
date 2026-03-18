# 技术方案：CTO Agent 执行引擎

**版本**: v1.1 | **日期**: 2026-03-18  
**上游 PRD**: PRD-execution-engine-v2.md  
**设计者**: CEO Agent (Main) | **审批**: Jeff  
**变更记录**: v1.0→v1.1: 补充完整状态机表、machine-readable 输出、分级 Plan 模板、协议一致性约束、Dry Run 验收标准

---

## 0. 设计原则

1. **文档即协议** — 所有执行规则以 Markdown 文件形式存在，不引入代码依赖
2. **最小上下文** — subagent 只看到与当前 task 相关的信息，不全量透传
3. **可审计** — 每次状态流转记录在 FPMS narrative 中
4. **渐进式** — 先跑通 L1/L2 轻量流程，再验证 L3/L4 重流程
5. **单一来源** — 所有枚举、字段定义只在 SUBAGENT-PROTOCOL.md 中定义一次，其他文件只引用（v1.1 新增）

---

## 1. 文件结构

```
agents/cto/
├── SOUL.md                          # 不动
├── CONSTITUTION.md                  # 不动
├── AGENTS.md                        # 修改 Phase 3
├── CODE-REVIEW-STANDARD.md          # 不动（被 reviewer 模板引用）
├── GIT-WORKFLOW.md                  # 不动（被 worktree 流程引用）
├── SUBAGENT-PROTOCOL.md             # 新建：执行协议总纲（唯一定义源）
├── prompts/
│   ├── implementer.md               # 新建：实现者模板
│   ├── spec-reviewer.md             # 新建：规约审查模板
│   ├── code-quality-reviewer.md     # 新建：质量审查模板
│   └── plan-template.md             # 新建：Plan 格式标准（含分级）
└── docs/
    ├── PRD-execution-engine-v2.md   # 已有
    └── DESIGN-execution-engine-v1.1.md # 本文件
```

---

## 2. SUBAGENT-PROTOCOL.md 设计

这是执行引擎的核心文件，也是所有枚举和字段定义的**唯一来源（Single Source of Truth）**。

### 2.1 内容结构

```markdown
# Subagent Protocol — CTO Agent 执行协议

## 1. 任务接入（Task Intake）
## 2. 上下文交接载荷（Context Handoff Payload）
## 3. 状态机（Execution State Machine）
## 4. 输出契约（Output Contracts）
## 5. 审查循环（Review Loop）
## 6. 升级边界（Escalation Boundaries）
## 7. 模型选择与降级（Model Strategy）
## 8. Git Worktree
## 9. 协议一致性约束（Consistency Rules）
```

### 2.2 完整状态机（v1.1 补充）

#### 2.2.1 状态定义表

| 状态 | 含义 | 允许进入来源 | 允许流向 | 终态 | 需 narrative | 需 Jeff 批准 |
|------|------|-------------|---------|------|-------------|-------------|
| **READY** | task 满足输入契约，等待执行 | （入口） | PLANNING | 否 | 是 | 否 |
| **PLANNING** | 正在生成 plan | READY | IMPLEMENTING | 否 | 否 | L3/L4: 是 |
| **IMPLEMENTING** | subagent 正在实现 | PLANNING, BLOCKED, ESCALATED | SPEC_REVIEW, BLOCKED | 否 | 是 | 否 |
| **SPEC_REVIEW** | spec reviewer 正在审查 | IMPLEMENTING, REWORK | QUALITY_REVIEW, REWORK, ESCALATED | 否 | 是 | 否 |
| **QUALITY_REVIEW** | quality reviewer 正在审查 | SPEC_REVIEW, REWORK | DONE, REWORK, ESCALATED | 否 | 是 | 否 |
| **REWORK** | implementer 修复 reviewer 发现的问题 | SPEC_REVIEW, QUALITY_REVIEW | SPEC_REVIEW, QUALITY_REVIEW, ESCALATED | 否 | 是（含 rework_round） | 否 |
| **BLOCKED** | subagent 卡住，等 CTO Agent 干预 | IMPLEMENTING | IMPLEMENTING, ESCALATED | 否 | 是 | 否 |
| **ESCALATED** | 已升级给 Jeff | BLOCKED, SPEC_REVIEW, QUALITY_REVIEW, REWORK | IMPLEMENTING, ABORTED | 否 | 是 | 是 |
| **DONE** | 完成，已合并 main | QUALITY_REVIEW | （终态） | ✅ | 是 | 否 |
| **ABORTED** | 放弃，worktree 已清理 | ESCALATED, 任何状态(Jeff 强制) | （终态） | ✅ | 是 | 是 |

#### 2.2.2 禁止的流转（硬约束）

| 禁止流转 | 原因 |
|---------|------|
| IMPLEMENTING → DONE | 不能跳过 review |
| SPEC_REVIEW → DONE | 不能跳过 quality review |
| PLANNING → SPEC_REVIEW | 不能跳过实现 |
| REWORK（第 3 次） → REWORK | 连续 3 次 rework 必须 ESCALATED |
| BLOCKED（第 2 次同原因） → IMPLEMENTING | 同原因连续 2 次 blocked 必须 ESCALATED |

#### 2.2.3 FPMS 状态映射

| 执行引擎状态 | FPMS task 状态 |
|-------------|---------------|
| READY, PLANNING, IMPLEMENTING, SPEC_REVIEW, QUALITY_REVIEW, REWORK | active |
| BLOCKED, ESCALATED | waiting |
| DONE | done |
| ABORTED | dropped |

#### 2.2.4 Narrative 记录格式

每次状态变更，记录到 FPMS narrative：

```
[YYYY-MM-DD HH:MM] STATE_CHANGE: {from} → {to}
  reason: {触发原因}
  rework_round: {N}/3（如适用）
  model: {使用的模型}
  action: {下一步操作}
```

### 2.3 上下文交接载荷（Context Handoff Payload）

**裁剪原则：subagent 看到的 = 完成任务所需的最小信息集**

#### 2.3.1 Implementer Payload 组装规则

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

#### 2.3.2 Reviewer Payload 组装规则

```
[REQUIRED] Task 原始 spec（用于对照）
[REQUIRED] Implementer 的结构化报告（含 machine-readable 区块）
[REQUIRED] Git diff（实际代码变更）
[REQUIRED] 适用的 Constitution 条款
[REQUIRED] 显式排除列表
[OPTIONAL] 测试输出 log
[NEVER]    Implementer 的 prompt（避免偏见）
[NEVER]    其他 task 信息
```

#### 2.3.3 Constitution 子集选择规则

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

## Report Format (MANDATORY — two sections required)

### Human-Readable Report
- **Understood Objective:** (restate in your own words)
- **Change Scope:** (exact file paths + line ranges)
- **Explicit Non-Changes:** (what I deliberately did NOT do)
- **Risk Flags:** (anything that concerns me)
- **Change Summary:** (one sentence per file)
- **Test Results:** (command + full output)
- **Reviewer Attention:** (what reviewer should focus on)
- **Self-Review Findings:** (issues found, fixed or unfixed)
- **Unfinished Items:** (if any)

### Machine-Readable Result
status_code: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
next_action: SPEC_REVIEW | PROVIDE_CONTEXT | ESCALATE
requires_human: true | false
rework_round: 0
touched_files: [file1.py, file2.py]
tests_passed: 42/42
tests_failed: 0
blocking_reason: (null or description)
concerns: (null or description)
```

**设计决策：**
- 占位符用 `{VARIABLE}` 格式，CTO Agent dispatch 时填充
- Constitution 子集按 §2.3.3 规则自动选择，不全量塞入
- Self-review checklist 反向检查"有没有做不该做的"（CDRE 特化）
- **v1.1**: 报告分两部分——human-readable 给人看，machine-readable 给流程消费

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

## Report Format (MANDATORY — two sections required)

### Human-Readable Verdict
- **Spec Reference:** (document paths used for review)
- **Evidence:**
  - Blocking Issues: [file:line + problem + spec clause]
  - Non-Blocking Issues: [file:line + problem + spec clause]
- **Out-of-Scope Check:** (did they build excluded features? yes/no + evidence)
- **Constitution Check:** (per-clause pass/fail)
- **Required Changes:** (specific items to fix)

### Machine-Readable Result
status_code: PASS | FAIL | ESCALATE
verdict: PASS | FAIL
blocking_issues_count: 0
non_blocking_issues_count: 0
exclusion_violation: true | false
constitution_violation: true | false
next_action: QUALITY_REVIEW | REWORK | ESCALATE
requires_human: true | false
```

**设计决策：**
- "Do Not Trust the Report" — 借鉴 Superpowers 的核心洞察
- Review 顺序强制：先查排除项（CDRE 特化），再查完整性
- 不给 reviewer 看 implementer 的 prompt（避免认知偏见）
- **v1.1**: machine-readable 区块支持流程自动路由

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
(Severity definitions: see SUBAGENT-PROTOCOL.md §9 — single source of truth)

### 1. Safety Boundaries
- [ ] Float arithmetic for money? (Constitution §13 — P0)
- [ ] Hardcoded secrets/keys? (Constitution §11 — P0)
- [ ] Silent exception swallowing on critical paths? (P0)
- [ ] Direct production environment access? (Constitution §12 — P0)
- [ ] Payment-specific: idempotency? state machine integrity? reconciliation?

### 2. Code Quality
- [ ] Single responsibility per module?
- [ ] Circular dependencies?
- [ ] Import style consistency?
- [ ] Error handling (no bare except, no swallowed errors)?
- [ ] Comments: module header (what/not-what/interactions), key functions (why not what)

### 3. Architecture Health
- [ ] Within Complexity Budget?
- [ ] New modules have Module Spec?
- [ ] CLAUDE.md / ARCHITECTURE.md updated?
- [ ] Irreversible coupling introduced?

### 4. Test Quality
- [ ] Invariant test files modified? (Constitution §5 — P0)
- [ ] Over-mocking?
- [ ] Boundary conditions tested?
- [ ] Error paths tested?
- [ ] Tests independently runnable?

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
- Only P2/P3 → **Approve with debt** (P2 → FPMS backlog)
- Clean → **Approve**

## Report Format (MANDATORY — two sections required)

### Human-Readable Verdict
- **Findings:** [severity + category + file:line + problem + fix]
- **Constitution Compliance:** [per-clause check]
- **Complexity Assessment:** modules / max LOC / dependency depth
- **FPMS Debt Items:** [P2 items for backlog]
- **Required Changes:** [P0/P1 must-fix items]

### Machine-Readable Result
status_code: APPROVE | REJECT | ESCALATE
verdict: Approve | Approve_with_debt | Reject
highest_severity: P0 | P1 | P2 | P3 | CLEAN
p0_count: 0
p1_count: 0
p2_count: 0
p3_count: 0
constitution_violation: true | false
next_action: DONE | REWORK | ESCALATE
requires_human: true | false
fpms_debt_items: [item1, item2]
```

**设计决策：**
- 严重度定义引用 SUBAGENT-PROTOCOL.md（不在模板中重复定义，防漂移）
- **v1.1**: machine-readable 区块含 p0-p3 计数，支持自动 verdict 路由

### 3.4 plan-template.md（v1.1: 分级制）

```markdown
# Plan 文档格式标准

## 头部（所有级别必须）

# [Feature Name] Implementation Plan

**Goal:** 一句话
**Architecture:** 2-3 句话
**Tech Stack:** 关键技术
**FPMS Task:** task-xxxx
**Module Spec:** 路径
**Risk Level:** L1 | L2 | L3 | L4
**Complexity Budget:** 模块数上限 / 最大文件 LOC / 依赖深度上限
**Test Baseline:** `命令` → 预期结果
**Plan Level:** Lite | Standard | Heavy

---

## Plan 分级标准

### Lite Plan（L1 任务）

适用：单文件、边界清晰、无架构影响

每个 task 只需：
- Files（创建/修改/测试）
- Explicit Exclusions
- 验证命令 + 预期结果
- Commit message

不要求：
- ❌ 内联完整实现代码
- ❌ 内联完整测试代码
- ❌ 每步 2-5 分钟拆分

示例：

### Task 1: Add input validation to parse_amount()

**Files:**
- Modify: `spine/tools.py:45-60`
- Test: `tests/test_tools.py`

**Exclusions:** 不改其他 tool handler

**Steps:**
- [ ] Write test for negative amount rejection
- [ ] Write test for non-integer rejection
- [ ] Implement validation in parse_amount()
- [ ] Run: `pytest tests/test_tools.py -v` → all pass
- [ ] Run: `pytest tests/ -q` → no regressions
- [ ] Commit: `fix(fpms): add input validation to parse_amount`

---

### Standard Plan（L2 任务）

适用：跨文件但边界清晰

每个 task 需要：
- Files（精确路径 + 行号范围）
- Explicit Exclusions
- Constitution Constraints
- 测试代码骨架（不需要完整实现代码）
- 每步有验证命令 + 预期输出
- Commit message

示例：

### Task 1: Extract transport layer

**Files:**
- Create: `spine/transport.py`
- Modify: `spine.py:10-30`
- Test: `tests/test_transport.py`

**Exclusions:** 不改 store.py, 不加新依赖
**Constitution:** §6(CLAUDE.md 同步) §22(能删就不加)

- [ ] Step 1: Write failing test
  ```python
  def test_transport_handles_tool_call():
      transport = Transport()
      result = transport.dispatch("create_node", {"title": "test"})
      assert result["status"] == "ok"
  ```

- [ ] Step 2: Run test, verify failure
  Run: `pytest tests/test_transport.py::test_transport_handles_tool_call -v`
  Expected: FAIL — ImportError: cannot import 'Transport'

- [ ] Step 3: Implement transport.py (minimal)
- [ ] Step 4: Run test → PASS
- [ ] Step 5: Full suite → all pass
- [ ] Step 6: Commit: `feat(fpms): extract transport layer`

---

### Heavy Plan（L3/L4 任务）

适用：跨模块、涉及架构决策、支付核心路径

每个 task 需要：
- 完整 File Structure 锁定
- 完整测试代码内联
- 完整实现代码内联
- 每步 2-5 分钟
- 精确验证命令 + 预期输出
- 零上下文 agent 也能执行
- Constitution 条款逐条标注

（格式同 v1.0 plan-template，此处不重复）

---

## 分级选择规则

| Risk Level | Plan Level | 理由 |
|------------|------------|------|
| L1 | Lite | 过度规划的成本 > 收益 |
| L2 | Standard | 需要结构但不需要完整内联代码 |
| L3 | Heavy | 架构决策需要最大确定性 |
| L4 | Heavy | 支付安全零容错 |
```

---

## 4. AGENTS.md Phase 3 改写

（与 v1.0 相同，此处不重复。见 v1.0 §4.2）

---

## 5. 协议一致性约束（v1.1 新增）

### 5.1 唯一定义源规则

防止多文件之间出现术语、枚举、字段名不一致导致系统变脆。

| 定义项 | 唯一来源 | 其他文件 |
|--------|---------|---------|
| 状态码枚举（DONE/BLOCKED/...） | SUBAGENT-PROTOCOL.md §3 | 只引用，不重复定义 |
| Risk Level 枚举（L1-L4） | SUBAGENT-PROTOCOL.md §1 | 只引用 |
| 输入契约字段 | SUBAGENT-PROTOCOL.md §1 | 只引用 |
| 输出报告字段（machine-readable） | SUBAGENT-PROTOCOL.md §4 | 模板中引用格式 |
| Severity 分级（P0-P3）定义 | CODE-REVIEW-STANDARD.md | SUBAGENT-PROTOCOL 引用，不重复 |
| Constitution 条款编号 | CONSTITUTION.md | 所有文件引用原编号 |
| Git 分支命名规则 | GIT-WORKFLOW.md | SUBAGENT-PROTOCOL 引用 |
| Verdict 枚举 | SUBAGENT-PROTOCOL.md §4 | 模板引用 |

### 5.2 一致性检查清单

每次修改协议文件时，必须检查：

- [ ] 状态码枚举是否与 SUBAGENT-PROTOCOL.md 一致？
- [ ] P0-P3 定义是否与 CODE-REVIEW-STANDARD.md 一致？
- [ ] 输出报告的 machine-readable 字段是否匹配 SUBAGENT-PROTOCOL.md §4？
- [ ] Constitution 条款引用是否使用原始编号（不自创别名）？
- [ ] AGENTS.md 是否只引用协议内容，不重复定义？

---

## 6. 关键设计决策（ADR 级别）

### ADR-EE-001: 文档协议 vs 代码实现

**决定**: 执行引擎以 Markdown 文档形式实现，不写代码。

**理由**: CTO Agent 本身是 LLM，文档即执行指令。不引入代码依赖，保持简单。

**后果**: 状态机没有代码级强制力。如果频繁违规，可升级为 Constitution Guard 拦截器。

### ADR-EE-002: Context Handoff Payload 裁剪策略

**决定**: CTO Agent 在 dispatch 时负责裁剪上下文，遵循 NEVER/REQUIRED/OPTIONAL 三级规则。

**理由**: 全量透传导致 token 爆炸和指令失焦。NEEDS_CONTEXT 回路兜底。

### ADR-EE-003: 状态机不替代 FPMS

**决定**: 执行引擎状态机是 FPMS 的细粒度补充，记录在 narrative 中。

**理由**: FPMS 是跨项目管理系统，不应被单个执行引擎污染。

### ADR-EE-004: Reviewer 不看 Implementer 的 Prompt

**决定**: Reviewer 只看 task spec + 结构化报告 + 代码，不看原始 prompt。

**理由**: 避免认知偏见。如果实现需要额外背景才能理解，说明代码不够自解释。

### ADR-EE-005: Machine-Readable 输出区块（v1.1 新增）

**决定**: 每个 subagent 的报告包含 human-readable 和 machine-readable 两部分。

**理由**: Human-readable 给人看，machine-readable 给 CTO Agent 的流程路由消费。关键字段用固定 key-value 格式，降低解析不确定性。

**后果**: 报告略长，但关键决策字段（status_code, next_action, requires_human）可稳定提取。

### ADR-EE-006: Plan 分级制（v1.1 新增）

**决定**: Plan 分三级（Lite / Standard / Heavy），按 Risk Level 选择。

**理由**: 一刀切的 Heavy Plan 对 L1 任务过重，plan 生成和维护成本高，容易与实现漂移。L1 任务只需明确文件范围、排除项和验证方式。

**后果**: L1 任务执行速度显著提升。但 Lite Plan 给 subagent 的确定性较低，需要 subagent 有更强的自主判断。通过 review 循环兜底。

---

## 7. 实现计划

### 7.1 批次划分

| 批次 | 交付物 | 依赖 |
|------|--------|------|
| Batch 1 | SUBAGENT-PROTOCOL.md | 无 |
| Batch 2 | prompts/implementer.md + prompts/plan-template.md | Batch 1 |
| Batch 3 | prompts/spec-reviewer.md + prompts/code-quality-reviewer.md | Batch 1 |
| Batch 4 | AGENTS.md Phase 3 改写 | Batch 1-3 |
| Batch 5 | Dry Run（task-a489） | Batch 1-4 |

### 7.2 验证方式

1. **文档自洽检查** — 模板占位符都有对应组装规则
2. **交叉引用检查** — Constitution 条款、severity 定义引用正确
3. **一致性检查** — 按 §5.2 清单验证
4. **Dry Run** — 真实 FPMS task 端到端验证
5. **Jeff Review** — 最终人工审查

### 7.3 Dry Run 计划与验收标准（v1.1 补充）

**选定任务**: task-a489（接入方式升级为 MCP Server）  
**Risk Level**: L2  
**Plan Level**: Standard

**验收标准（全部通过才算 Dry Run 成功）：**

| # | 验收项 | 通过标准 |
|---|--------|---------|
| 1 | 输入契约完整性 | 所有必填字段能无遗漏填充，无需脑补 |
| 2 | Payload 裁剪有效性 | Implementer 收到的 context ≤ 10k tokens |
| 3 | Implementer 理解度 | Implementer 的 "Understood Objective" 与实际 spec 一致 |
| 4 | Implementer 不越界 | 未实现 Explicit Exclusions 中的任何项 |
| 5 | Spec Reviewer 独立发现问题 | 如有 out-of-scope 修改，reviewer 能发现 |
| 6 | Review 收敛性 | 3 轮内收敛（不触发 ESCALATED） |
| 7 | Machine-readable 可解析 | status_code、next_action 字段能被 CTO Agent 稳定提取 |
| 8 | Narrative 审计完整性 | 每次状态变更都有 narrative 记录，含 rework_round |
| 9 | Token 预算合规 | 全流程（implement + review）≤ 150k tokens |
| 10 | Worktree 生命周期完整 | 创建 → 基线验证 → 工作 → 合并/清理，无残留 |
| 11 | L2 全流程单次运行 | 不需要人工干预即可走完 READY → DONE |

**Dry Run 失败处理：**
- 如果 ≥ 3 项不通过 → 方案需要修订
- 如果 1-2 项不通过 → 针对性修复后重跑
- 全通过 → 方案可以进入正式实现

---

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 模板过长导致 subagent context 不够 | Token 预算分配已定义，implementer 输入 ≤ ~10k |
| CTO Agent 裁剪上下文遗漏关键信息 | NEEDS_CONTEXT 回路兜底 |
| 状态机靠 prompt 约束不够硬 | 先跑通验证，频繁违规再代码化 |
| Plan 中内联代码质量不够 | Plan 由 Opus 生成，实现由 Sonnet 执行 |
| Dry Run 暴露大量问题 | Feature not bug——轻量 task 暴露比支付系统安全 |
| 多文档协议漂移 | §5 一致性约束 + 唯一来源规则 |
| Lite Plan 确定性不够 | Review 循环兜底 + L1 任务本身风险低 |
| Machine-readable 格式被 LLM 输出不稳定破坏 | 固定 key-value 格式降低风险 + CTO Agent 做容错解析 |

---

*本方案基于 PRD-execution-engine-v2.md，定义 CTO Agent 执行引擎的具体实现设计。v1.1 补充了完整状态机表、machine-readable 输出、分级 Plan 模板、协议一致性约束、Dry Run 验收标准。审批后进入实现。*
