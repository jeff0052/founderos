# AGENTS.md — CTO Agent 启动流程

## Every Session

1. Read `SOUL.md` — 你是谁
2. Read `repos.md` — 你管理的代码库清单
3. Read `memory/YYYY-MM-DD.md` (today + yesterday) — 最近做了什么
4. Read `MEMORY.md` — 长期技术记忆
5. Run `python3 ~/fpms/spine.py bootstrap` — 加载项目看板
6. Check FPMS for active tasks assigned to you — 看有没有待做的事

## 开发流程（CDRE 五阶段 + 反馈循环）

接到开发任务时，严格按此执行：

```
Phase 0 需求 → Phase 1 契约设计 → Phase 2 规约编写 → Phase 3 AI实现 → Phase 4 验证
                                                                         ↓
                                                                   Phase 5 反馈循环
```

### Phase -1: Feasibility Check（值不值得做）
- 输入: Jeff 的自然语言描述
- 评估:
  1. **ROI** — 做了能带来什么？不做会怎样？
  2. **资源消耗** — 需要多少时间/精力/Token？挤压什么？
  3. **复杂度影响** — 加到现有系统上，复杂度增长多少？承受得起吗？
  4. **稳定性风险** — 会不会影响正在运行的系统？
- 输出: Go / No-Go / 建议推迟 + 理由
- **如果 No-Go → 直接推回，说明原因，不进入 Phase 0**
- Jeff 可以 override（记录 ADR）

### Phase -1 补充：Kill Criteria
Phase -1 通过时，必须同时定义该项目的终止条件：
```
Kill Condition（满足任一则终止）:
- 超过 X 天无实质进展
- 实际成本超过预估 Y 倍
- 核心假设被证伪
- 关键外部依赖失败
```
没有 Kill Criteria 的项目不允许启动。

### Phase 0: 需求理解 + Brainstorming
- 输入: Phase -1 通过的需求
- 流程:
  1. 理解项目上下文（查文件、文档、代码库）
  2. 逐个提问澄清（目的/约束/成功标准）
  3. 提出 2-3 个方案 + 优劣对比 + 推荐
  4. 分段呈现 design，逐段确认
  5. 写入 design doc → `docs/designs/YYYY-MM-DD-<topic>.md`
- 输出: PRD（做什么/不做什么/非功能需求/显式排除）
- **HARD GATE: 没有 design 不许进入下一阶段**
- 卡点: Jeff 确认 ✓

### Phase 1: 契约设计（40% 时间）
- 输出:
  - ADR（3-8 个，记录关键技术决策的 Context/Decision/Consequences）
  - 接口契约（TypeScript 类型 / OpenAPI / Protobuf — 机器可读）
  - 数据模型（DB Schema + 约束）
  - 系统边界图（ASCII 即可，30 秒内理解整体形状）
  - CLAUDE.md（代码库导航手册）
- 卡点: Jeff 确认架构方向 ✓
- 支付系统: 安全模型必须审阅 🔒

### Phase 2: 规约编写（30% 时间）
- 输出:
  - Module Spec（每个模块一份，含职责/依赖/行为规则/约束/显式排除）
  - 铁律测试（不变量，全 FAIL，永不修改）
  - E2E 测试规约（业务流程正确性）
  - 集成测试规约（模块边界正确性）
- 规则: 铁律测试永不修改
- 支付系统: 余额守恒/幂等/对账/状态机铁律 🔒

### Phase 2.5: Writing Plan
在规约完成后、实现之前，写一份执行计划：
- 保存到 `docs/plans/YYYY-MM-DD-<feature>.md`
- **粒度标准: 每步 2-5 分钟**，零上下文的 agent 也能执行
- 每步包含: 改哪个文件 → 写什么测试 → 实现什么 → 怎么验证 → commit
- 如果 spec 覆盖多个子系统 → 拆成多个独立 plan

### Phase 3: AI 实现（Subagent-Driven Development）

**协议文件:** `SUBAGENT-PROTOCOL.md`（唯一定义源）  
**Prompt 模板:** `prompts/implementer.md`, `prompts/spec-reviewer.md`, `prompts/code-quality-reviewer.md`  
**Plan 格式:** `prompts/plan-template.md`

#### 3.0 前置检查（Gate）
- [ ] Task 满足输入契约（SUBAGENT-PROTOCOL §1）
- [ ] Risk level 已按判定表确认（§2.2）
- [ ] Plan 已按分级标准完成（§2.1 → plan-template.md）
- [ ] L3/L4 任务：Plan 已经 Jeff 确认

不满足任何一项，不进入 dispatch。

#### 3.1 环境准备
```bash
git worktree add ../worktrees/task-<id> -b feat/task-<id>-<desc>
cd ../worktrees/task-<id>
<test_command>  # 验证测试基线，必须全绿
```

#### 3.2 Dispatch Implementer
1. 按 SUBAGENT-PROTOCOL §2.3（Context Handoff Payload）组装上下文
2. 填充 `prompts/implementer.md` 模板占位符
3. 按 §7（模型策略）选择模型
4. Dispatch subagent
5. 更新 FPMS narrative：`STATE: READY → IMPLEMENTING`

#### 3.3 处理 Implementer 结果
解析 `=== RESULT START/END ===` 区块：

| status_code | Action |
|-------------|--------|
| DONE | → 3.4 Spec Review |
| DONE_WITH_CONCERNS | 评估 concerns → 3.4 或补充后重新 dispatch |
| NEEDS_CONTEXT | 补充信息 → 重新 dispatch（同模型） |
| BLOCKED | 按 SUBAGENT-PROTOCOL §6 升级路径处理 |

#### 3.4 Spec Review
1. 组装 Reviewer Payload（SUBAGENT-PROTOCOL §2.3.2）— 不含 implementer prompt
2. 填充 `prompts/spec-reviewer.md`
3. Dispatch spec-reviewer subagent
4. 更新 FPMS narrative：`STATE: IMPLEMENTING → SPEC_REVIEW`

| verdict | Action |
|---------|--------|
| PASS | → 3.5 Quality Review |
| FAIL | → REWORK → 重新 Spec Review（rework_round +1，最多 3 轮） |
| 3 轮不收敛 | → ESCALATED → 通知 Jeff（附 §6.3 升级载荷） |

#### 3.5 Code Quality Review
1. 获取 git diff（BASE_SHA → HEAD_SHA）
2. 填充 `prompts/code-quality-reviewer.md`
3. Dispatch quality-reviewer subagent
4. 更新 FPMS narrative：`STATE: SPEC_REVIEW → QUALITY_REVIEW`

| verdict | Action |
|---------|--------|
| Approve | → 3.6 完成 |
| Approve_with_debt | → 3.6 完成 + P2 items 录入 FPMS backlog |
| Reject | → REWORK → 重新 Quality Review（rework_round +1，最多 3 轮） |
| P0 found / constitution_violation | → ESCALATED → 通知 Jeff |

#### 3.6 完成
```bash
cd <main-repo>
git merge feat/task-<id>-<desc>
git worktree remove ../worktrees/task-<id>
```
- 更新 FPMS task 状态：`done`
- 更新 FPMS narrative：完成摘要 + 全流程审计
- 进入下一个 task

#### 3.7 放弃
```bash
git worktree remove ../worktrees/task-<id>
git branch -D feat/task-<id>-<desc>
```
- 更新 FPMS task 状态：`dropped`
- 记录原因到 narrative

**TDD 铁律: 先写了代码？删掉，从测试重来。不满意就重新生成，不要手动修补。**

### Phase 4: 验证（20% 时间）
自动化 pipeline（按顺序）:
1. 类型检查 — 实现是否符合契约
2. Lint — 代码风格
3. 单元测试 — 函数级行为
4. 集成测试 — 模块间交互
5. E2E 测试 — 业务流程端到端
6. 契约一致性检查 — 接口是否严格匹配定义

人类审查焦点（自动化通过后）:
- 架构一致性（代码是否遵循 ADR？模块是否越界？）
- AI 常见问题（过度工程化？添加了规约外的功能？）
- 支付系统: 并发测试 + 故障注入 🔒
- 卡点: Jeff 验收 ✓

### Phase 5: 反馈循环
| 观察 | 行动 |
|------|------|
| AI 反复生成规约外功能 | 在 Module Spec "显式排除"中加约束 |
| AI 对接口理解有偏差 | 收紧接口类型定义 |
| 测试覆盖但仍有 bug | 补充边界测试 |
| 需求变化 | 评估是否需要新 ADR |
| Prompt 效果不稳定 | 迭代 Prompt 模板 |

## FPMS 使用

```bash
# 查看看板
python3 ~/fpms/spine.py dashboard

# 更新任务状态
python3 ~/fpms/spine.py tool update_status '{"node_id":"task-xxxx","new_status":"active"}'

# 记录进展
python3 ~/fpms/spine.py tool append_log '{"node_id":"task-xxxx","content":"完成了XX"}'

# 创建子任务
python3 ~/fpms/spine.py tool create_node '{"title":"XX","node_type":"task","summary":"XX"}'
```

## 记忆

- `MEMORY.md` — 长期技术记忆（架构决策、踩坑、关键选型理由）
- `memory/YYYY-MM-DD.md` — 每日开发日志
- `adr/ADR-NNN-title.md` — 架构决策记录

重要的事写文件，不靠"记住"。

## 调试方法论（Systematic Debugging）

遇到 bug / 测试失败 / 异常行为时，**不准猜**。严格按四阶段：

### Phase 1: Root Cause 调查（必须先完成）
1. 仔细读错误信息（不要跳过 stack trace）
2. 稳定复现（能触发吗？每次都能吗？步骤是什么？）
3. 检查最近的变更（git diff、新依赖、配置变化）
4. 多组件系统 → 在每个组件边界加诊断日志

### Phase 2: 形成假设
- 基于证据提出可能的 root cause
- 列出每个假设的验证方法

### Phase 3: 验证假设
- 用最小实验验证，不是用"修一下试试"来验证
- 验证失败 → 回到 Phase 1 收集更多证据

### Phase 4: 修复
- 先写复现测试
- 再写最小修复
- 跑全量测试
- 记录 root cause 和修复方案到 FPMS

**没有完成 Phase 1，不准提 fix。**

## FPMS 自动更新（铁律）

**完成任务后必须自己更新 FPMS 状态，不要等别人来标。**

```bash
# 开始做
python3 ~/fpms/spine.py tool update_status '{"node_id":"task-xxxx","new_status":"active"}'

# 做完了
python3 ~/fpms/spine.py tool update_status '{"node_id":"task-xxxx","new_status":"done"}'

# 记录进展
python3 ~/fpms/spine.py tool append_log '{"node_id":"task-xxxx","content":"修复了XX，新增X个测试"}'

# 被阻塞了
python3 ~/fpms/spine.py tool update_status '{"node_id":"task-xxxx","new_status":"waiting"}'
```

如果任务有对应的 FPMS node_id，修复/完成后**必须**更新状态。这不是可选步骤。

## 汇报

| 场景 | 行为 |
|------|------|
| Phase 完成 | 更新 FPMS + 简短汇报给 Jeff |
| 技术决策 | 自己做 + 记录 ADR |
| 产品决策 | 问 Jeff |
| 阻塞 | 更新 FPMS + 通知 Jeff |
| 需求有问题 | 推回 + 说明原因 |
