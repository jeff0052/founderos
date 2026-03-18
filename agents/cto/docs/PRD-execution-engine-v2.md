# PRD: CTO Agent 执行引擎补全

**版本**: v2.0 | **日期**: 2026-03-18  
**产品负责人**: Jeff | **执行者**: CTO Agent  
**上游文档**: CTO-AGENT-PRD-V2.md, CDRE Methodology, Superpowers (obra/superpowers)  
**变更记录**: v1→v2: 增加输入/输出契约、状态机、任务分级、升级边界、证据要求、模型降级策略

---

## 0. 定位

**本 PRD 交付的不是"几个 prompt 模板"，而是一个可治理的 CTO Agent 执行协议层。**

四个核心问题：
1. 怎么接任务（输入契约 + 任务分级）
2. 怎么派任务（prompt 模板 + worktree 隔离 + 模型选择）
3. 怎么审任务（审查循环 + 证据要求 + 结构化输出）
4. 怎么在失败时收回来（状态机 + 升级边界）

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
| 无输入/输出契约 | subagent 输入不稳定，输出无法接入流程 |
| 无状态机 | 只有状态码枚举，无流程控制 |
| 无任务分级 | 所有任务一视同仁，高风险任务缺少保护 |
| 无 plan 文档格式 | plan 粒度不可控，subagent 无法直接执行 |
| 无模型选择策略 | 所有任务用同一模型，浪费或不足 |
| 无物理隔离机制 | subagent 直接改 main，失败无法回滚 |
| 无证据要求 | review 沦为主观判断 |
| AGENTS.md Phase 3 是空壳 | 写了"spawn coding agents"但没有具体执行协议 |

### 1.2 参考

业界最佳实践 **Superpowers** (github.com/obra/superpowers) 在执行引擎层面的做法：
- 具体的 prompt 模板（implementer / spec-reviewer / code-quality-reviewer）
- 4 种状态码（DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED）+ 处理策略
- Plan 文档含完整代码、文件路径、运行命令、预期输出
- 模型分级使用（机械任务用便宜模型，架构/审查用强模型）
- Git worktree 物理隔离

Superpowers 的弱项（我们已有的）：无领域约束、无项目管理、无记忆系统、无治理体系、无任务分级、无输入/输出契约。

### 1.3 目标

**给 CTO Agent 的管理手册装上可治理的执行引擎。** 补全输入契约、任务分级、subagent 调度、审查循环、状态机、升级边界、plan 格式、物理隔离，使 CTO Agent 能端到端执行 CDRE Phase 3（AI 实现），且在失败时能可控地收回。

---

## 2. 做什么

### 2.1 输入契约（Task Intake Contract）

CTO Agent 只接受满足最小输入契约的 FPMS task。输入不完整时，不进入实现，而是进入 clarification / escalation。

**FPMS Task 最小输入字段：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `task_id` | ✅ | FPMS node ID |
| `task_type` | ✅ | feat / fix / refactor / hotfix |
| `objective` | ✅ | 这个 task 要达成什么 |
| `acceptance_criteria` | ✅ | 验收条件（可测试的） |
| `related_specs` | ✅ | 引用的 Module Spec / PRD / ARCHITECTURE 路径 |
| `constraints` | ✅ | 适用的 Constitution 条款编号 + 领域约束 |
| `out_of_scope` | ✅ | 显式排除 |
| `touched_modules` | ✅ | 涉及的模块列表 |
| `risk_level` | ✅ | L1-L4（见 2.3 任务分级） |
| `deliverable_type` | ✅ | code / doc / config / test |
| `context` | 选填 | 架构背景、依赖关系、前置任务 |
| `test_baseline` | 选填 | 当前测试命令 + 预期结果 |

**不满足契约时的处理：**
- 缺 `objective` 或 `acceptance_criteria` → 推回给 Jeff，要求澄清
- 缺 `out_of_scope` → CTO Agent 自行补充后提交 Jeff 确认
- 缺 `risk_level` → CTO Agent 根据 `touched_modules` 和 `constraints` 自动评估，支付核心路径自动标 L4

### 2.2 任务分级（Task Grading）

不是所有 FPMS task 都允许 dispatch subagent 自动实现。

| 级别 | 范围 | 执行方式 | 审查要求 |
|------|------|---------|---------|
| **L1** | 局部实现，单文件，边界清晰 | 自动 dispatch，Sonnet | spec review + quality review |
| **L2** | 跨文件但边界清晰，不涉核心路径 | 自动 dispatch，Sonnet + 强 review | spec review + quality review（Opus） |
| **L3** | 跨模块 / 涉及架构决策 | 只允许先出 plan，plan 经 Jeff 确认后才 dispatch | spec review + quality review + Jeff 抽查 |
| **L4** | 支付核心路径 / 账务 / 状态机 / 密钥 | Jeff approval 后才执行，每步人工确认 | 全量审查 + Jeff 逐步验收 |

**自动升级规则：**
- `touched_modules` 包含支付核心模块 → 自动升至 L4
- `constraints` 包含 Constitution §3/§5/§13 → 至少 L3
- 涉及 3+ 模块 → 至少 L2

### 2.3 Subagent Prompt 模板

**三个模板文件**，每个模板融入 CDRE + Constitution 体系：

#### 2.3.1 implementer.md（实现者模板）

给 subagent 的完整指令，包含：

- **任务描述** — 从 plan 中提取的完整任务文本（不让 subagent 自己去读文件）
- **上下文** — 这个任务在整体架构中的位置、依赖关系
- **Module Spec 约束** — 职责、行为规则、**显式排除**（防止过度工程化）
- **Constitution 约束** — 适用于本任务的铁律子集（如支付任务必须包含浮点数禁令、幂等要求）
- **TDD 要求** — 先写测试、看到失败、再写实现
- **提问许可** — 明确允许 subagent 在开始前和执行中提问
- **升级许可** — 明确允许 subagent 说"这个太难了，我做不了"
- **Self-review 清单** — 完成前自查：完整性、质量、是否越界
- **范围锁定** — subagent 不能自行扩大任务范围，不能自行做架构裁决

#### 2.3.2 spec-reviewer.md（规约审查者模板）

- **输入** — 任务的 Module Spec + implementer 的结构化报告 + 实际代码
- **核心原则** — "不要信 implementer 的报告，自己读代码验证"
- **审查顺序**（CDRE 特化）：
  1. **反向阻断（最先查）** — 有没有实现"显式排除"中禁止的功能？有就直接 REJECT
  2. **完整性** — 所有 spec 要求是否都实现了？
  3. **过度工程化** — 有没有加 spec 之外的功能？
  4. **Constitution 合规** — 适用铁律是否遵守？

#### 2.3.3 code-quality-reviewer.md（质量审查者模板）

- **前置条件** — 只有 spec review 通过后才 dispatch
- **输入** — 任务描述 + 变更的 git diff（BASE_SHA → HEAD_SHA）
- **审查维度** — 对接 CODE-REVIEW-STANDARD.md 的五维（跳过 Spec 合规，已由 spec-reviewer 覆盖）
- **输出** — P0-P3 分级 findings + Approve / Approve with debt / Reject
- **P0 = 阻断**，P1 = 修完再审，P2 = 录入 FPMS backlog

### 2.4 Subagent 输出契约（Output Contract）

每个 subagent 的输出必须结构化，包含固定 section。

#### 2.4.1 Implementer 输出

```
## Report
- **Status:** DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- **Understood Objective:** 我理解的目标（用自己的话复述）
- **Change Scope:** 修改了哪些文件（精确路径 + 行号范围）
- **Explicit Non-Changes:** 我明确没做什么
- **Risk Flags:** 发现的风险点
- **Change Summary:** 改动摘要（每个文件一句话）
- **Test Results:** 测试命令 + 输出 + 通过/失败数
- **Reviewer Attention:** 请 reviewer 重点检查的地方
- **Self-Review Findings:** 自查发现的问题（已修复/未修复）
- **Unfinished Items:** 未完成项（如有）
- **Next Action Recommendation:** 建议下一步
```

#### 2.4.2 Spec Reviewer 输出

```
## Spec Review Verdict
- **Verdict:** PASS | FAIL
- **Spec Reference:** 审查依据的文档路径
- **Evidence:**
  - Blocking Issues: [具体文件:行号 + 问题描述 + spec 条款引用]
  - Non-Blocking Issues: [同上]
- **Out-of-Scope Check:** 是否实现了显式排除中的功能？
- **Constitution Check:** 适用铁律是否遵守？[逐条列出]
- **Required Changes:** 必须修改的具体项
- **Status:** PASS | FAIL | ESCALATE
- **Next Action Recommendation:** 建议下一步
```

#### 2.4.3 Code Quality Reviewer 输出

```
## Quality Review Verdict
- **Verdict:** Approve | Approve with debt | Reject
- **Highest Severity:** P0 / P1 / P2 / P3
- **Evidence:**
  - Findings: [每条: 级别 + 类别 + 文件:行号 + 问题 + 修复建议]
- **Constitution Compliance:** [逐条检查结果]
- **Complexity Assessment:** 模块数 / 最大文件行数 / 依赖深度
- **FPMS Debt Items:** 需录入 FPMS backlog 的 P2 项
- **Required Changes:** P0/P1 必须修改的具体项
- **Status:** APPROVE | REJECT | ESCALATE
- **Next Action Recommendation:** 建议下一步
```

### 2.5 状态机（Execution State Machine）

不是只有状态码枚举，而是完整的流转规则。

#### 2.5.1 状态定义

```
READY           → task 满足输入契约，等待执行
PLANNING        → 正在生成 implementation plan
IMPLEMENTING    → subagent 正在实现
SPEC_REVIEW     → spec reviewer 正在审查
QUALITY_REVIEW  → code quality reviewer 正在审查
REWORK          → implementer 正在修复 reviewer 发现的问题
BLOCKED         → subagent 卡住，等待 CTO Agent 干预
ESCALATED       → 已升级给 Jeff
DONE            → 任务完成，已合并 main
ABORTED         → 任务放弃，worktree 已清理
```

#### 2.5.2 流转规则（铁律）

```
READY → PLANNING                      （CTO Agent 开始为 task 生成 plan）
PLANNING → IMPLEMENTING               （plan 完成，dispatch implementer）
IMPLEMENTING → SPEC_REVIEW            （implementer 报告 DONE/DONE_WITH_CONCERNS）
IMPLEMENTING → BLOCKED                （implementer 报告 BLOCKED/NEEDS_CONTEXT）
SPEC_REVIEW → QUALITY_REVIEW          （spec reviewer 报告 PASS）
SPEC_REVIEW → REWORK                  （spec reviewer 报告 FAIL）
QUALITY_REVIEW → DONE                 （quality reviewer 报告 APPROVE）
QUALITY_REVIEW → REWORK               （quality reviewer 报告 REJECT）
REWORK → SPEC_REVIEW                  （修复后重新 spec review）
REWORK → QUALITY_REVIEW               （仅限 spec 已通过、quality 打回的情况）
BLOCKED → IMPLEMENTING                （CTO Agent 补充 context 后重新 dispatch）
BLOCKED → ESCALATED                   （升级路径用尽）
ESCALATED → IMPLEMENTING              （Jeff 指示后重新执行）
ESCALATED → ABORTED                   （Jeff 决定放弃）
任何状态 → ABORTED                     （Jeff 可随时终止）
```

**禁止的流转（硬约束）：**
- ❌ IMPLEMENTING → DONE（不能跳过 review）
- ❌ SPEC_REVIEW → DONE（不能跳过 quality review）
- ❌ REWORK 连续 3 次 → 必须进入 ESCALATED
- ❌ BLOCKED 连续 2 次同原因 → 必须进入 ESCALATED

#### 2.5.3 与 FPMS 状态映射

| 执行引擎状态 | FPMS task 状态 |
|-------------|---------------|
| READY | active |
| PLANNING / IMPLEMENTING / SPEC_REVIEW / QUALITY_REVIEW / REWORK | active |
| BLOCKED / ESCALATED | waiting |
| DONE | done |
| ABORTED | dropped |

执行引擎状态是 FPMS 状态的细粒度补充，不替代 FPMS。细粒度状态记录在 FPMS task 的 narrative 中。

### 2.6 升级边界（Escalation Boundaries）

#### 2.6.1 BLOCKED vs FAILED 语义

| 状态 | 含义 | 处理 |
|------|------|------|
| **BLOCKED** | 缺信息或能力不足，任务本身没问题 | 补 context / 换模型 / 拆任务 |
| **FAILED** | 任务本身有问题（spec 冲突、架构不支持） | 升级给 CTO Agent 重新评估 |

#### 2.6.2 升级到 CTO Agent 的条件

- Implementer 报告 NEEDS_CONTEXT
- Implementer 报告 BLOCKED
- Spec reviewer 连续 2 轮 FAIL（同一问题）
- Quality reviewer 发现 P0 问题

#### 2.6.3 必须升级到 Jeff（人类）的条件

以下任何一条触发，**不允许 CTO Agent 自行解决**：

- 支付资金流 / 状态机核心路径改动（Constitution §3）
- 涉及密钥、签名、账务、对账逻辑
- 发现 spec 冲突且无法从现有文档判定
- 需要跨模块重构超出 task 边界
- Reviewer 与 implementer 连续 2 轮无法收敛
- REWORK 达到 3 次上限
- 升级路径用尽（补 context + 换模型 + 拆任务都失败）
- 发现 Constitution 违规（铁律测试被修改、浮点数计算金额）

#### 2.6.4 升级时必须附带的上下文

```
- task_id
- 当前状态机状态
- 已尝试的处理步骤
- 失败原因（具体错误/reviewer findings）
- 相关代码变更（git diff 或 SHA 范围）
- CTO Agent 的判断和建议
```

### 2.7 证据要求（Evidence Requirements）

Review 结论必须基于显式证据，不允许纯印象式 verdict。

#### 2.7.1 Implementer 必须提供的自证材料

- touched files 列表（精确路径）
- 相关 spec 引用（哪份 Module Spec 的哪个条款）
- 测试命令 + 完整输出
- 未覆盖风险说明
- 明确未完成项

#### 2.7.2 Spec Reviewer 必须引用的文档

- Module Spec（职责/行为规则/显式排除）
- 任务的 acceptance_criteria
- 适用的 Constitution 条款

每条 finding 必须包含：**spec 条款编号 + 代码文件:行号 + 偏差描述**

#### 2.7.3 Code Quality Reviewer 必须检查的证据

- Git diff（BASE_SHA → HEAD_SHA）
- 测试通过率（命令 + 输出）
- 铁律测试文件是否被修改（hash 校验）
- 新增文件是否有模块头部注释

每条 finding 必须包含：**P0-P3 级别 + 审查维度 + 代码文件:行号 + 问题描述 + 修复建议**

### 2.8 Plan 文档格式标准

#### 2.8.1 Plan 头部（必须）

```markdown
# [Feature Name] Implementation Plan

**Goal:** 一句话描述
**Architecture:** 2-3 句话描述方案
**Tech Stack:** 关键技术
**FPMS Task:** task-xxxx
**Module Spec:** 引用路径
**Complexity Budget:** 模块数上限 / 最大文件行数 / 依赖深度上限
**Risk Level:** L1-L4

---
```

#### 2.8.2 Task 格式（每个 task 必须包含）

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

#### 2.8.3 粒度标准

- 每步 2-5 分钟
- 零上下文的 agent 也能执行
- 代码内联在 plan 中，不是"实现 XX 功能"
- 每步有精确的验证命令和预期输出

### 2.9 模型选择与降级策略

#### 2.9.1 默认选择

| 任务类型 | 默认模型 | 理由 |
|----------|---------|------|
| 机械实现（1-2 文件，spec 完整） | Sonnet | 快、便宜、spec 完整时够用 |
| 集成任务（多文件协调） | Sonnet | 标准推理即可 |
| 架构设计、Brainstorming | Opus | 需要深度推理 |
| Spec Review | Sonnet | 对照检查，不需要创造力 |
| Code Quality Review | Sonnet | 模式匹配为主 |
| 复杂调试（3+ 次修复失败） | Opus | 需要架构级思考 |
| Plan 编写 | Opus | 需要全局视角 |

#### 2.9.2 高风险任务强制模型

- L3 任务：plan 用 Opus，实现可用 Sonnet
- L4 任务：全链路 Opus

#### 2.9.3 降级与 Fallback

| 场景 | 处理 |
|------|------|
| Sonnet 实现失败（BLOCKED） | 升级 Opus 重试 |
| Opus 实现失败 | 拆任务或升级人类 |
| 模型超时 | 重试 1 次，仍超时则换模型 |
| Token 预算耗尽 | 暂停当前 task，通知 Jeff |

#### 2.9.4 Token Budget 约束

- 单个 implementer subagent：≤ 50k tokens（含输入输出）
- 单个 reviewer subagent：≤ 20k tokens
- 单个 task 全流程（implement + review 循环）：≤ 150k tokens
- 超预算 → 暂停 + 通知 CTO Agent 评估

#### 2.9.5 重试上限

- 同模型同任务：最多重试 2 次
- 升级模型后：再重试 2 次
- 总计 ≤ 4 次 dispatch，仍失败 → ESCALATED

### 2.10 Git Worktree 集成

#### 2.10.1 生命周期

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

#### 2.10.2 规则

- 每个 FPMS task 一个 worktree + 一个 branch
- Branch 命名：`feat/task-<fpms-id>-<short-description>`
- Subagent 只在 worktree 中操作，不碰 main
- 合并前必须通过全量测试
- 失败的 worktree 可以干净丢弃

### 2.11 AGENTS.md Phase 3 改写

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
| 不引入自动任务拆分器 | 任务拆解是 CTO Agent 的人工判断，不自动化 |
| 不赋予 subagent 独立架构裁决权 | subagent 只执行，架构决策归 CTO Agent |

---

## 4. 成功标准

1. CTO Agent 对一个满足输入契约的 FPMS task，能生成结构化 plan 并 dispatch implementer
2. Implementer 输出符合标准结构（2.4.1），且显式声明范围、排除项、风险、测试结果与状态码
3. Spec-reviewer 与 code-quality-reviewer 基于统一协议返回 verdict、问题列表（含文件:行号 + spec 条款引用）、修复建议与状态码
4. 当出现 BLOCKED / FAILED / 连续 REWORK / 高风险变更时，系统进入定义好的升级路径
5. 所有工作在 git worktree 中隔离，不污染 main
6. 所有模板融入 CDRE 体系（Module Spec、显式排除、Constitution 约束）
7. 状态机流转可追溯（记录在 FPMS task narrative 中）
8. 更新后的 AGENTS.md Phase 3 完整描述 dispatch、review loop、状态流转与升级边界

---

## 5. 交付物

| 文件 | 类型 | 说明 |
|------|------|------|
| `agents/cto/prompts/implementer.md` | 新建 | 实现者 subagent 指令模板 |
| `agents/cto/prompts/spec-reviewer.md` | 新建 | 规约审查 subagent 指令模板 |
| `agents/cto/prompts/code-quality-reviewer.md` | 新建 | 质量审查 subagent 指令模板 |
| `agents/cto/prompts/plan-template.md` | 新建 | Plan 文档格式标准 + 示例 |
| `agents/cto/SUBAGENT-PROTOCOL.md` | 新建 | 状态机 + 输入/输出契约 + 任务分级 + 升级边界 + 证据要求 + 模型策略 + worktree 流程 |
| `agents/cto/AGENTS.md` | 修改 | Phase 3 接入执行引擎 |

---

## 6. 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 模板太重，subagent context 爆炸 | 中 | 执行质量下降 | 模板只包含当前任务相关的约束子集，不全量塞入 |
| Worktree 操作出错（merge 冲突等） | 低 | 代码丢失 | 合并前全量测试 + main 永远可回退 |
| 审查循环卡在第 3 轮 | 中 | 任务停滞 | 超限自动升级人类 |
| Sonnet 能力不足以执行复杂实现 | 低 | 任务失败 | 升级路径已定义（→ Opus → 拆任务 → 人类） |
| 状态机过重导致执行摩擦 | 中 | 简单任务变慢 | L1 任务走轻量流程，状态记录可简化 |
| 输入契约门槛过高导致 task 积压 | 低 | 任务入口瓶颈 | CTO Agent 可自行补充 out_of_scope 等非核心字段 |

---

## 7. 约束与执行边界

### 7.1 系统约束

- 所有新文件必须纳入 git 版本控制
- 模板内容不得违反现有 Constitution 任何条款
- 不引入外部依赖（纯 Markdown 文档）
- 与现有 CODE-REVIEW-STANDARD.md 和 GIT-WORKFLOW.md 保持一致，不重复不矛盾

### 7.2 执行边界（铁律）

- CTO Agent 不能让 subagent 绕过 Constitution / SOUL / spec hierarchy
- Subagent 不能自行扩大任务范围
- Subagent 不能自行做架构裁决（只能升级）
- 涉及支付核心路径、账务、密钥、状态机的任务必须升级或人工确认
- Review 结论必须基于显式证据，不允许纯印象式 verdict
- 任何 subagent 输出都必须带 status code 与 next action recommendation
- 状态机流转必须可审计（记录在 FPMS narrative）

---

*本 PRD 定义 CTO Agent 可治理执行协议层的完整范围。审批后进入方案设计。*
