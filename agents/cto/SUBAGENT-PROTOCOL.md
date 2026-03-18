# Subagent Protocol — CTO Agent 执行协议

**版本**: v1.0 | **日期**: 2026-03-18  
**上游**: PRD-execution-engine-v2.md, DESIGN-execution-engine-v1.1.md  
**本文件是执行引擎所有枚举、字段、状态定义的唯一来源（Single Source of Truth）。**

---

## 1. 任务接入（Task Intake Contract）

### 1.1 最小输入字段

CTO Agent 只接受满足以下契约的 FPMS task。缺必填字段时不进入实现。

| 字段 | 必填 | 说明 |
|------|------|------|
| `task_id` | ✅ | FPMS node ID |
| `task_type` | ✅ | feat / fix / refactor / hotfix |
| `objective` | ✅ | 这个 task 要达成什么 |
| `acceptance_criteria` | ✅ | 可测试的验收条件 |
| `related_specs` | ✅ | Module Spec / PRD / ARCHITECTURE 路径 |
| `constraints` | ✅ | 适用的 Constitution 条款编号 + 领域约束 |
| `out_of_scope` | ✅ | 显式排除 |
| `touched_modules` | ✅ | 涉及的模块列表 |
| `risk_level` | ✅ | L1-L4（见 §1.2） |
| `deliverable_type` | ✅ | code / doc / config / test |
| `test_baseline` | 选填 | 当前测试命令 + 预期结果 |
| `context` | 选填 | 架构背景、依赖关系 |

### 1.2 不满足契约时的处理

| 缺失字段 | 处理 |
|---------|------|
| `objective` 或 `acceptance_criteria` | 推回 Jeff，要求澄清 |
| `out_of_scope` | CTO Agent 自行补充，提交 Jeff 确认 |
| `risk_level` | CTO Agent 按 §1.3 自动评估 |
| 其他必填字段 | CTO Agent 从 FPMS context / spec 中提取，无法提取则推回 Jeff |

---

## 2. 任务分级（Task Grading）

### 2.1 分级定义

| 级别 | 范围 | 执行方式 | 审查要求 | Plan 级别 |
|------|------|---------|---------|----------|
| **L1** | 单文件，边界清晰 | 自动 dispatch，Sonnet | spec + quality review | Lite |
| **L2** | 跨文件但边界清晰 | 自动 dispatch，Sonnet + 强 review | spec + quality review（Opus） | Standard |
| **L3** | 跨模块 / 涉及架构决策 | Plan 经 Jeff 确认后才 dispatch | spec + quality review + Jeff 抽查 | Heavy |
| **L4** | 支付核心 / 账务 / 状态机 / 密钥 | Jeff approval 后执行，每步人工确认 | 全量审查 + Jeff 逐步验收 | Heavy |

### 2.2 分级判定表

按顺序检查，命中任一条件即确定级别（高级别优先）：

| 条件 | 最低级别 |
|------|---------|
| `touched_modules` 含支付核心模块 | **L4** |
| 涉及密钥、签名、账务、对账、清结算逻辑 | **L4** |
| `constraints` 含 Constitution §3/§5/§13 | **L3** |
| 新增 public interface | **L3** |
| 新增外部依赖 | **L3** |
| 修改状态机 | **L3** |
| 涉及 3+ 模块 | **L2** |
| 跨文件但不跨模块边界 | **L2** |
| 单文件，无 interface 变更 | **L1** |

### 2.3 自动升级规则

- CTO Agent 评估的级别 < 判定表结果 → 自动升级至判定表级别
- 执行过程中发现实际复杂度超出 → CTO Agent 可升级（但不可降级）
- Jeff 可随时手动调整级别

---

## 3. 状态机（Execution State Machine）

### 3.1 状态定义

| 状态 | 含义 | 终态 | 需 narrative | 需 Jeff |
|------|------|------|-------------|---------|
| **READY** | task 满足输入契约，等待执行 | 否 | 是 | 否 |
| **PLANNING** | 正在生成 plan | 否 | 否 | L3/L4: 是 |
| **IMPLEMENTING** | subagent 正在实现 | 否 | 是 | 否 |
| **SPEC_REVIEW** | spec reviewer 正在审查 | 否 | 是 | 否 |
| **QUALITY_REVIEW** | quality reviewer 正在审查 | 否 | 是 | 否 |
| **REWORK** | implementer 修复 reviewer 问题 | 否 | 是 | 否 |
| **BLOCKED** | subagent 卡住，等 CTO Agent 干预 | 否 | 是 | 否 |
| **ESCALATED** | 已升级给 Jeff | 否 | 是 | 是 |
| **DONE** | 完成，已合并 main | ✅ | 是 | 否 |
| **ABORTED** | 放弃，worktree 已清理 | ✅ | 是 | 是 |

### 3.2 允许的流转

| From | To | Trigger | Judge | Required Evidence | Auto/Human |
|------|----|---------|-------|-------------------|------------|
| (入口) | READY | task 满足 §1.1 输入契约 | CTO Agent | 字段完整性检查 | Auto |
| READY | PLANNING | CTO Agent 开始生成 plan | CTO Agent | risk_level 已确认 | Auto |
| PLANNING | IMPLEMENTING | plan 完成（L3/L4: Jeff 已确认） | CTO Agent / Jeff | plan 文件 + Jeff ACK(L3/L4) | L1/L2: Auto, L3/L4: Human |
| IMPLEMENTING | SPEC_REVIEW | implementer 报告 status_code=DONE 或 DONE_WITH_CONCERNS | CTO Agent | implementer machine-readable result | Auto |
| IMPLEMENTING | BLOCKED | implementer 报告 status_code=BLOCKED 或 NEEDS_CONTEXT | CTO Agent | implementer machine-readable result + blocking_reason | Auto |
| SPEC_REVIEW | QUALITY_REVIEW | spec reviewer 报告 verdict=PASS | CTO Agent | spec reviewer machine-readable result | Auto |
| SPEC_REVIEW | REWORK | spec reviewer 报告 verdict=FAIL | CTO Agent | spec reviewer findings | Auto |
| SPEC_REVIEW | ESCALATED | spec reviewer 报告 status_code=ESCALATE | CTO Agent | reviewer findings + escalation reason | Auto → Jeff |
| QUALITY_REVIEW | DONE | quality reviewer 报告 verdict=Approve 或 Approve_with_debt | CTO Agent | quality reviewer machine-readable result + merge 成功 | Auto |
| QUALITY_REVIEW | REWORK | quality reviewer 报告 verdict=Reject | CTO Agent | quality reviewer findings | Auto |
| QUALITY_REVIEW | ESCALATED | P0 found 或 constitution_violation=true | CTO Agent | P0 evidence | Auto → Jeff |
| REWORK | SPEC_REVIEW | 修复完成，spec 需重审 | CTO Agent | new implementer report + rework_round < 3 | Auto |
| REWORK | QUALITY_REVIEW | 修复完成，spec 已通过，quality 需重审 | CTO Agent | new implementer report + rework_round < 3 | Auto |
| REWORK | ESCALATED | rework_round ≥ 3 | CTO Agent | 3 轮 findings 汇总 | Auto → Jeff |
| BLOCKED | IMPLEMENTING | CTO Agent 补充 context / 换模型 | CTO Agent | 补充的 context 或模型变更说明 | Auto |
| BLOCKED | ESCALATED | 补 context + 换模型都失败，或同原因连续 blocked 2 次 | CTO Agent | 失败记录 | Auto → Jeff |
| ESCALATED | IMPLEMENTING | Jeff 给出指示 | Jeff | Jeff 的指示内容 | Human |
| ESCALATED | ABORTED | Jeff 决定放弃 | Jeff | Jeff 的决定 | Human |
| 任何状态 | ABORTED | Jeff 强制终止 | Jeff | Jeff 的决定 | Human |

### 3.3 禁止的流转

| 禁止 | 原因 |
|------|------|
| IMPLEMENTING → DONE | 不能跳过 review |
| SPEC_REVIEW → DONE | 不能跳过 quality review |
| PLANNING → SPEC_REVIEW | 不能跳过实现 |
| REWORK(round=3) → REWORK | 连续 3 次 rework 必须 ESCALATED |
| BLOCKED(同原因×2) → IMPLEMENTING | 同原因连续 2 次 blocked 必须 ESCALATED |
| 任何状态 → 降级 risk_level | 级别只升不降 |

### 3.4 FPMS 状态映射

| 执行引擎状态 | FPMS task 状态 |
|-------------|---------------|
| READY, PLANNING, IMPLEMENTING, SPEC_REVIEW, QUALITY_REVIEW, REWORK | active |
| BLOCKED, ESCALATED | waiting |
| DONE | done |
| ABORTED | dropped |

### 3.5 Narrative 记录格式

每次状态变更，记录到 FPMS task narrative：

```
[YYYY-MM-DD HH:MM] STATE: {from} → {to}
  trigger: {触发原因}
  judge: {CTO Agent | Jeff}
  rework_round: {N}/3
  model: {使用的模型}
  evidence: {关键证据摘要}
  next: {下一步操作}
```

---

## 4. 输出契约（Output Contracts）

所有 subagent 输出**必须**包含 human-readable 和 machine-readable 两部分。

### 4.1 Machine-Readable 格式规范

使用固定 sentinel 包裹，固定字段顺序，固定枚举值：

```
=== RESULT START ===
status_code=<枚举值>
next_action=<枚举值>
requires_human=<true|false>
rework_round=<整数>
<角色特定字段>
=== RESULT END ===
```

**解析规则：**
- CTO Agent 提取 `=== RESULT START ===` 和 `=== RESULT END ===` 之间的内容
- 每行一个 key=value，key 不含空格
- 值为枚举时必须使用本文件定义的枚举值（见 §4.5）
- 值为列表时使用 JSON 数组语法：`["a.py","b.py"]`
- 空值使用 `null`

### 4.2 Implementer 输出

**Machine-Readable:**

```
=== RESULT START ===
status_code=DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED
next_action=SPEC_REVIEW|PROVIDE_CONTEXT|ESCALATE
requires_human=true|false
rework_round=0
touched_files=["file1.py","file2.py"]
tests_passed=42
tests_failed=0
blocking_reason=null
concerns=null
=== RESULT END ===
```

**Human-Readable:** (自由格式，至少包含)
- Understood Objective
- Change Scope（file:line）
- Explicit Non-Changes
- Risk Flags
- Change Summary
- Test Results（command + output）
- Self-Review Findings

### 4.3 Spec Reviewer 输出

**Machine-Readable:**

```
=== RESULT START ===
status_code=PASS|FAIL|ESCALATE
verdict=PASS|FAIL
blocking_issues_count=0
non_blocking_issues_count=0
exclusion_violation=true|false
constitution_violation=true|false
next_action=QUALITY_REVIEW|REWORK|ESCALATE
requires_human=true|false
=== RESULT END ===
```

**Human-Readable:** (至少包含)
- Evidence（per finding: file:line + problem + spec clause）
- Out-of-Scope Check
- Constitution Check
- Required Changes

### 4.4 Code Quality Reviewer 输出

**Machine-Readable:**

```
=== RESULT START ===
status_code=APPROVE|REJECT|ESCALATE
verdict=Approve|Approve_with_debt|Reject
highest_severity=P0|P1|P2|P3|CLEAN
p0_count=0
p1_count=0
p2_count=0
p3_count=0
constitution_violation=true|false
next_action=DONE|REWORK|ESCALATE
requires_human=true|false
fpms_debt_items=[]
=== RESULT END ===
```

**Human-Readable:** (至少包含)
- Findings（per finding: severity + category + file:line + problem + fix suggestion）
- Constitution Compliance
- Complexity Assessment
- Required Changes

### 4.5 枚举值定义（唯一来源）

#### Implementer status_code
`DONE` | `DONE_WITH_CONCERNS` | `NEEDS_CONTEXT` | `BLOCKED`

#### Implementer next_action
`SPEC_REVIEW` | `PROVIDE_CONTEXT` | `ESCALATE`

#### Spec Reviewer status_code
`PASS` | `FAIL` | `ESCALATE`

#### Quality Reviewer status_code
`APPROVE` | `REJECT` | `ESCALATE`

#### Quality Reviewer verdict
`Approve` | `Approve_with_debt` | `Reject`

#### Severity（引用自 CODE-REVIEW-STANDARD.md）
`P0` | `P1` | `P2` | `P3` | `CLEAN`

---

## 5. 审查循环（Review Loop）

### 5.1 流程

```
Implementer 完成
  → Spec Review
    → PASS → Quality Review
               → Approve → DONE
               → Approve_with_debt → DONE + FPMS backlog
               → Reject → REWORK → Quality Review（round +1）
    → FAIL → REWORK → Spec Review（round +1）
    → ESCALATE → Jeff
```

### 5.2 熔断规则

| 条件 | 动作 |
|------|------|
| Spec FAIL → REWORK → Spec FAIL → REWORK → Spec FAIL | rework_round=3 → 强制 ESCALATED |
| Quality REJECT → REWORK → Quality REJECT → REWORK → Quality REJECT | rework_round=3 → 强制 ESCALATED |
| Spec FAIL + Quality REJECT 交叉累计 ≥ 3 轮 | 强制 ESCALATED |

### 5.3 REWORK 传递规则

- Spec FAIL 后 REWORK → 回到 Spec Review（不跳到 Quality Review）
- Quality REJECT 后 REWORK → 如果修复不涉及 spec 变更，直接回 Quality Review；否则回 Spec Review
- REWORK 时 implementer 只修复 reviewer 指出的问题，不扩大范围

---

## 6. 升级边界（Escalation Boundaries）

### 6.1 升级到 CTO Agent 的条件

- Implementer 报告 NEEDS_CONTEXT
- Implementer 报告 BLOCKED
- Spec reviewer 连续 2 轮 FAIL（同一问题）
- Quality reviewer 发现 P0

### 6.2 必须升级到 Jeff 的条件

以下任何一条触发，CTO Agent **不得**自行解决：

- 支付资金流 / 状态机核心路径改动（Constitution §3）
- 涉及密钥、签名、账务、对账
- Spec 冲突且无法从现有文档判定
- 跨模块重构超出 task 边界
- Reviewer 与 implementer 连续 2 轮无法收敛
- REWORK 达 3 次上限
- 升级路径用尽（补 context + 换模型 + 拆任务都失败）
- Constitution 违规（铁律测试被修改、浮点数算金额）

### 6.3 升级载荷（Escalation Payload）

升级时必须附带：

```
=== ESCALATION START ===
task_id=<FPMS task ID>
current_state=<当前执行状态>
rework_round=<N>/3
blocking_reason=<具体原因>
attempts=[{"action":"补context","result":"仍缺X"},{"action":"换Opus","result":"同问题"}]
impacted_files=["file1.py","file2.py"]
risk_flags=["涉及支付路径","Constitution §13 相关"]
recommended_decision=<CTO Agent 的建议>
minimal_context=<Jeff 做决策所需的最小信息>
=== ESCALATION END ===
```

---

## 7. 模型选择与降级（Model Strategy）

### 7.1 默认选择表

| 角色 | 默认模型 | 备注 |
|------|---------|------|
| Plan 编写 | Opus | 需要全局视角 |
| Implementer (L1/L2) | Sonnet | 快且便宜 |
| Implementer (L3/L4) | Opus | 高风险需要强推理 |
| Spec Reviewer | Sonnet | 对照检查为主 |
| Quality Reviewer (L1/L2) | Sonnet | 模式匹配为主 |
| Quality Reviewer (L3/L4) | Opus | 需要架构判断 |

### 7.2 Fallback 顺序

```
Sonnet 失败（BLOCKED）
  → 补 context 重试（Sonnet）
  → 升级 Opus 重试
  → 拆 task 重试
  → ESCALATED（Jeff）

Opus 失败
  → 拆 task 重试
  → ESCALATED（Jeff）
```

### 7.3 Token Budget

| 维度 | 上限 |
|------|------|
| 单个 implementer subagent | ≤ 50k tokens |
| 单个 reviewer subagent | ≤ 20k tokens |
| 单 task 全流程（implement + review 循环） | ≤ 150k tokens |
| 超预算 | 暂停 + 通知 CTO Agent 评估 |

### 7.4 重试上限

- 同模型同 task：最多重试 2 次
- 升级模型后：再重试 2 次
- 总计 ≤ 4 次 dispatch，仍失败 → ESCALATED

---

## 8. Git Worktree

### 8.1 生命周期

```bash
# 创建
git worktree add ../worktrees/task-<id> -b feat/task-<id>-<desc>
cd ../worktrees/task-<id>

# 验证基线（必须全绿才继续）
<test_command>

# subagent 工作...

# 成功：合并 + 清理
cd <main-repo>
git merge feat/task-<id>-<desc>
git worktree remove ../worktrees/task-<id>

# 失败：清理
git worktree remove ../worktrees/task-<id>
git branch -D feat/task-<id>-<desc>
```

### 8.2 命名规则

- Branch: `feat/task-<fpms-id>-<short-description>`
- Worktree 目录: `../worktrees/task-<fpms-id>`

### 8.3 清理规则

- DONE → 合并后立即删除 worktree + 保留 branch（merged）
- ABORTED → 立即删除 worktree + 删除 branch
- ESCALATED → 保留 worktree 直到 Jeff 决定

---

## 9. 协议一致性约束（Consistency Rules）

### 9.1 唯一定义源

| 定义项 | 唯一来源 | 其他文件规则 |
|--------|---------|-------------|
| 执行状态枚举 | 本文件 §3.1 | 只引用 |
| 状态流转规则 | 本文件 §3.2 | 只引用 |
| Risk Level 枚举 (L1-L4) | 本文件 §2.1 | 只引用 |
| 分级判定条件 | 本文件 §2.2 | 只引用 |
| 输入契约字段 | 本文件 §1.1 | 只引用 |
| Machine-readable 字段 | 本文件 §4 | 模板引用格式 |
| 枚举值 | 本文件 §4.5 | 模板使用相同枚举 |
| Severity (P0-P3) 定义 | CODE-REVIEW-STANDARD.md | 本文件引用，不重复 |
| Constitution 条款编号 | CONSTITUTION.md | 所有文件引用原编号 |
| Git 分支命名 | GIT-WORKFLOW.md | 本文件引用 |

### 9.2 修改检查清单

修改本文件或模板时必须检查：

- [ ] 状态枚举是否与 §3.1 一致？
- [ ] Machine-readable 字段是否与 §4 一致？
- [ ] 枚举值是否与 §4.5 一致？
- [ ] Severity 定义是否与 CODE-REVIEW-STANDARD.md 一致？
- [ ] Constitution 引用是否使用原始编号？
- [ ] AGENTS.md Phase 3 是否只引用本文件，不重复定义？

---

## 10. 文档协议升级门槛

本执行引擎以文档协议形式运行（ADR-EE-001）。当以下任一条件满足时，必须启动代码化（Constitution Guard 扩展）：

| 门槛条件 | 量化标准 |
|---------|---------|
| 非法状态流转 | 30 个 task 内出现 ≥ 3 次 |
| Machine-readable 解析失败 | 10 个 task 内出现 ≥ 2 次 |
| 协议漂移导致路由错误 | 连续 2 次 |
| Constitution 违规未被 review 拦截 | 任何 1 次 |

统计来源：FPMS task narrative 审计记录。

---

*本文件是 CTO Agent 执行引擎的唯一协议源。Prompt 模板、AGENTS.md Phase 3、review 流程均引用本文件，不重复定义。*
