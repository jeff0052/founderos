---
name: ai-dev-workflow
description: "AI驱动开发全流程SOP。从idea到代码的标准化流程：Research → PRD → Plan → Build → Verify → Ship。支持多模型交叉审查、TDD、两阶段Review、分块并行编码、精度最大化的任务拆解。"
metadata: {"openclaw":{"requires":{"bins":["bash"]}}}
---

# AI 驱动开发流程 (AI-Driven Development Workflow)

一套从 idea 到可运行代码的标准化 SOP。

**核心理念**：
- 人做决策，AI 做执行
- 先想清楚再动手（Phase 1-3 占 60-70% 时间）
- 精度优先于速度（少而精的 context > 一大坨）
- 测试驱动（先写失败测试，再写实现）
- 证据优先于声明（跑通了才算完成）

## 适用场景

- 从零构建一个新系统/模块
- 项目复杂度中等以上（预估代码量 > 1000 行）
- 有明确的功能需求但尚未设计

## 不适用

- 简单的 one-liner 修改（直接 edit）
- 纯 bug fix（直接定位修复）
- 已有完善设计文档的纯编码任务（直接进 Phase 4）

---

## Phase 1: Research（研究）

**目标**：搞清楚问题是什么、现有方案为什么不行、我们要做什么不做什么。

### 步骤

1. **定义核心问题**
   - 用一句话说清楚要解决什么
   - 列出 3-5 个子问题
   - 问自己："如果不做这个，会怎样？"

2. **调研现有方案**
   - 搜索业界已有的解法
   - 列表对比：方案 / 优点 / 致命缺陷
   - 确认：现有方案真的不够用，才值得自己造

3. **定义边界**
   - 明确 v1 要做什么（Goals）
   - 明确 v1 不做什么（Non-goals）
   - 列出关键约束（技术栈、性能、存储、兼容性）

### 产出
- 问题定义文档（可以是对话记录的摘要）
- Goals / Non-goals 清单
- 核心约束列表

### 时间参考
- 简单项目：1-2 小时
- 复杂项目：1-2 天（可跨多个 session）

---

## Phase 2: PRD（需求文档）

**目标**：把 Research 的结论翻译成精确的、可验收的功能规格。

### 步骤

1. **起草 PRD**
   - 按 FR（功能需求）逐条撰写
   - 每个 FR 包含：定义、规则、约束、边界情况
   - 补充 NFR（非功能需求）：性能、安全、可维护性
   - 补充约束章节
   - 补充验收 checklist（每条可测试）

2. **多模型交叉审查（三省审查法）**
   - 将完整 PRD 分别发给 3 个不同模型审查
   - 每个模型的 prompt：`"找漏洞。只挑架构级会出事故的点，不谈文风。"`
   - 收集反馈，逐条裁决：
     - ✅ 采纳（真 bug / 有效边缘态）
     - ⚠️ 半采纳（方向对但解法不对）
     - ❌ 拒绝（伪问题 / 超出 PRD 范畴）
   - 修订 PRD，发回模型确认
   - 重复直到所有模型签字或开始重复自己

3. **封板信号**
   - 所有 Critical/High 问题已修复
   - 新发现的 bug 严重度持续下降
   - 多个模型开始重复已有反馈
   - 最后一轮反馈中零 Critical = 可封板

### 多模型审查最佳实践

| 做法 | 原因 |
|------|------|
| 每个模型独立审查，不让它们看彼此的反馈 | 避免锚定偏差 |
| 先让自己（主 agent）独立审查一遍 | 自己的发现往往最精准 |
| 逐条裁决并记录理由 | 防止"审查疲劳"导致无脑采纳 |
| 记录每个模型的有效发现率 | 了解各模型的强项，优化后续分工 |
| 当模型开始重复自己时立即停止 | 收益递减信号 |

### 产出
- `PRD-functional-vN.md`（封板版）
- 审查日志（哪个模型发现了什么，采纳/拒绝理由）

### 时间参考
- 起草：2-4 小时
- 每轮审查：30-60 分钟
- 总计：半天到 2 天

---

## Phase 3: Plan（设计）

**目标**：把 PRD 翻译成可执行的实现计划。不写代码，只设计。

### 步骤

1. **生成 CLAUDE.md（速查卡）**
   - 从 PRD 提炼 150-200 行的精简版
   - 包含：架构概览、Schema、状态机、Tool 列表、关键规则
   - 目的：coding agent 30 秒扫完就能开工
   - 控制在 ~2500 tokens

2. **生成 ARCHITECTURE.md（施工图纸）**
   - 模块划分（每个模块一个文件）
   - 模块间依赖关系图
   - 数据流图（写路径 + 读路径）
   - 数据库 Schema（建表语句）
   - 关键设计决策清单

3. **生成架构图**
   - 系统全景图（所有模块位置和关系）
   - 写路径流程（从输入到持久化的每一步）
   - 读路径流程（从触发到输出的每一步）

4. **Task 分解（精度最大化）**

   把系统拆成独立的 task，每个 task 遵循 **TDD 红绿循环**：

   ```
   Task N: {Component Name}

   Files:
   - Create: exact/path/to/file.py
   - Test: tests/exact/path/to/test_file.py

   Step 1: 写失败测试
   Step 2: 跑测试，确认失败
   Step 3: 写最小实现让测试通过
   Step 4: 跑测试，确认通过
   Step 5: Commit
   ```

   **Task 粒度原则**：
   - 每个 task 对应一个文件/模块
   - 每步 2-5 分钟（对 agent 来说）
   - 每个 task 有明确的失败测试 + 通过条件
   - 完整代码写在计划里，不是"添加验证逻辑"这种模糊描述

5. **依赖分层**
   - 按模块间依赖关系分层，同层可并行
   - 每层完成并验收后才启动下一层

   ```
   第1层（无依赖，可并行）: Task A, B, C
   第2层（依赖第1层）: Task D, E, F
   第3层（依赖第2层）: Task G, H, I
   第4层（集成层）: Task J
   ```

6. **精度原则**
   - 每个 coding agent 的 context ≤ 500 行
   - 只给它需要的 PRD 段落 + 上游接口签名
   - 不给它不需要的东西。少即是精度

### Task 定义模板

```markdown
## Task N: {module_name}

**输入 PRD 段落**: FR-X (相关规则摘要)
**依赖上游**: schema.py (接口签名), store.py (接口签名)
**输出文件**: {module_name}.py (~{N}行)

### Steps

- [ ] **Step 1: 写失败测试**
  ```python
  def test_xxx():
      result = function(input)
      assert result == expected
  ```

- [ ] **Step 2: 跑测试确认失败**
  Run: `pytest tests/test_xxx.py -v`
  Expected: FAIL

- [ ] **Step 3: 写最小实现**
  ```python
  def function(input):
      return expected
  ```

- [ ] **Step 4: 跑测试确认通过**
  Run: `pytest tests/test_xxx.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  `git commit -m "feat: add xxx"`
```

### 产出
- `CLAUDE.md`
- `ARCHITECTURE.md`
- `INTERFACES.md`（接口契约）
- 架构图
- Task 分解清单（含依赖关系 + TDD 步骤 + 完整代码）

### 时间参考
- 1-3 小时

---

## Phase 3.5: Scaffold（骨架先行）

**目标**：在 coding agent 动手前，生成全部模块的空壳文件，让 import 和类型检查从第一分钟就打通。

### 为什么需要

并行 agent 写第 2 层模块时，如果第 1 层的文件还不存在，`import` 直接报 `ModuleNotFoundError`，agent 会自我怀疑并乱改代码。骨架先行消除这个问题。

### 步骤

1. 根据 `INTERFACES.md` 的函数签名，生成所有模块文件
2. 每个文件只包含：
   - class / function 签名
   - Type hints
   - Docstring（一行说明）
   - `pass` 或 `raise NotImplementedError`
3. 确认整个项目能 `import` 不报错
4. 确认 `mypy`（如果用）无类型错误

### 示例

```python
# store.py (骨架)
from models import Node, Edge

class Store:
    def __init__(self, db_path: str, events_path: str) -> None:
        raise NotImplementedError

    def create_node(self, node: Node) -> Node:
        """插入新节点。自动生成 id/timestamps。"""
        raise NotImplementedError

    def get_node(self, node_id: str) -> Node | None:
        """按 id 查询单个节点。"""
        raise NotImplementedError
    # ... 其余签名
```

### 产出
- 全部模块的 `.py` 骨架文件（可 import，不可运行）

### 时间参考
- 10-15 分钟（主 agent 或脚本自动生成）

---

## Phase 3.6: Invariant Tests（铁律测试先行）

**目标**：把 PRD 中不可违背的系统不变量编译成自动化测试。在任何 coding agent 写实现之前，这些测试必须存在。

### 为什么需要

Agent 写代码时可能"看起来一致"但悄悄破坏边界条件。如果不变量只存在于文档里，漂移是不可避免的。把铁律变成测试 = 用机器守护文档。

### 步骤

1. 从 PRD 的约束章节和验收 checklist 中提取**系统级不变量**
2. 每条不变量写成独立的测试文件 `test_invariant_{name}.py`
3. 这些测试不是某个模块的单元测试，而是**跨模块的系统约束**
4. 所有 coding agent 的代码必须在铁律全绿的前提下才算完成

### 不变量识别模板

```markdown
不变量: {一句话描述}
来源: PRD FR-X / 约束 #N
测试: test_invariant_{name}.py
场景:
  - 正常路径: {怎样操作不违反}
  - 违反路径: {怎样操作触发违反，期望被拒绝}
  - 边界路径: {极端情况下仍不违反}
```

### 示例

```python
# test_invariant_dag.py
def test_parent_cycle_rejected():
    """A→B→C, 试图让 C 成为 A 的 parent → 必须拒绝"""

def test_cross_dimension_deadlock_rejected():
    """child depends_on ancestor → 必须拒绝"""

# test_invariant_xor.py
def test_root_and_parent_mutually_exclusive():
    """is_root=True 的节点不能有 parent_id"""

# test_invariant_atomic_commit.py
def test_crash_after_commit_no_data_loss():
    """DB commit 后进程崩溃 → 重启后数据完整"""

# test_invariant_derived_isolation.py
def test_write_path_never_reads_derived():
    """写路径中的代码不引用任何 derived_*/cache 表"""
```

### 产出
- `tests/invariants/` 目录下的测试文件
- 每个不变量有正常 + 违反 + 边界三类场景

### 时间参考
- 30-60 分钟（主 agent 写，或 spawn 一个 Test Writer agent）

### 关键原则
- **这些测试在 Phase 4 之前就必须存在**
- coding agent 写实现时，铁律测试是它的"红绿灯"
- 铁律测试**永远不允许被 coding agent 修改**（和 RFC 协议一样，改铁律需人类审批）

---

## Phase 4: Build（编码）

**目标**：按 Plan 分批 spawn coding agent 执行 task。

### 模型分级策略

不是所有 task 都需要最强模型。按复杂度选模型，节省成本提高速度：

| 任务类型 | 信号 | 推荐模型 |
|---------|------|---------|
| 机械实现 | 改 1-2 个文件，spec 完整，纯逻辑 | Sonnet / 便宜模型 |
| 集成任务 | 跨多文件，需要理解上下文关系 | Sonnet / 标准模型 |
| 架构/Review | 设计判断，全局理解 | Opus / 最强模型 |

### 执行流程

1. **为每个 Task 准备 context 包**
   - CLAUDE.md（全文，每个 agent 都给）
   - 从 PRD 中抽出只属于该 task 的段落
   - 上游模块的接口签名（不给实现）
   - 该 task 的验收 checklist

2. **按依赖层级分批启动**
   - 第 1 批：所有无依赖的 task，并行 spawn
   - 等第 1 批全部完成并通过两阶段 review
   - 第 2 批：依赖第 1 层的 task，并行 spawn
   - 依此类推

3. **AI-TDD 分离（防止"自己出题自己答"）**

   每个 task 分两个独立 agent：

   **Agent A: Test Writer（只写测试）**
   - 输入：接口签名 + PRD checklist
   - 输出：`test_{module}.py`（覆盖正常路径 + 边界 + 异常）
   - 约束：不写任何实现代码
   - 验证：测试文件语法正确，所有 test 应该 FAIL（因为实现不存在）

   **Agent B: Implementer（只写实现）**
   - 输入：骨架文件 + 测试文件（Agent A 的产出）+ PRD 片段
   - 输出：`{module}.py` 实现
   - 约束：**不准修改测试文件**
   - 目标：让所有红灯变绿
   - 报错栈是最好的导航仪

4. **接口防篡改协议（RFC Protocol）**

   Coding Agent 的 System Prompt 中加入铁律：

   > *"你必须严格遵循 INTERFACES.md 的函数签名，严禁私自修改参数、返回类型或方法名。*
   > *如果发现现有签名无法实现业务需求，立即停止编码，输出 `[RFC: 接口变更提议]` 并说明原因。*
   > *架构修改的决定权在人类手里。"*

5. **两阶段 Review（每个 Task 完成后）**

   **Stage 1: Spec Review（规格符合）**
   - 对照 PRD 相关段落逐条检查
   - 是否缺失功能？是否添加了规格外的东西？
   - 接口签名是否被篡改？
   - ❌ 不通过 → 修复后重新 review
   - ✅ 通过 → 进入 Stage 2

   **Stage 2: Code Quality Review（代码质量）**
   - Type hints 完整？
   - 边界情况处理？
   - 命名清晰？
   - 不必要的复杂度？
   - 错误消息是否 actionable（告诉 LLM 下一步该做什么）？
   - ❌ 不通过 → 修复后重新 review
   - ✅ 通过 → 标记 task 完成

4. **处理失败的 agent**

   Agent 完成后会报告四种状态之一：

   | 状态 | 含义 | 处理 |
   |------|------|------|
   | DONE | 完成 | 进入两阶段 review |
   | DONE_WITH_CONCERNS | 完成但有疑虑 | 先看疑虑再 review |
   | NEEDS_CONTEXT | 缺少信息 | 补充 context 重新派发 |
   | BLOCKED | 无法完成 | 换更强模型 / 拆更小 task / 上报人类 |

   - 10-20% 的 session 失败是正常的
   - 失败了重新 spawn 比在原 session 纠正更快
   - 连续 3 次失败同一 task → 上报人类决策

### Prompt 模板

**Test Writer Agent:**
```
你是一个测试工程师。根据接口签名和验收标准，为 {module_name} 编写完整的测试用例。

## 项目速查
{CLAUDE.md 全文}

## 接口签名
{从 INTERFACES.md 抽出的该模块签名}

## 验收标准
{从 PRD 抽出的 checklist}

## 约束
- 只输出 test_{module_name}.py
- 不写任何实现代码
- 覆盖：正常路径 + 边界条件 + 异常路径
- 所有测试现在应该 FAIL（实现还不存在）
- 错误场景要验证具体的错误消息内容
```

**Implementer Agent:**
```
你是一个 Python 开发者。实现 {module_name}.py，让所有测试通过。

## 项目速查
{CLAUDE.md 全文}

## 你的任务
{从 PRD 抽出的相关段落}

## 你依赖的接口
{上游模块的函数签名，不含实现}

## 测试文件
{Agent A 写的 test_{module_name}.py 全文}

## 铁律
- 严禁修改测试文件
- 严格遵循 INTERFACES.md 的函数签名，严禁私自修改
- 如果发现签名无法实现业务，停止编码，输出 [RFC: 接口变更提议]
- 所有函数加 type hints
- 错误消息必须 actionable：告诉调用者哪里错了、下一步该调什么工具修复
- 每步完成后 commit
```

### 产出
- 所有 task 的源代码 + 测试文件
- 每个 task 通过两阶段 review

### 时间参考
- 每批 20-45 分钟（含 review）
- 总计 2-4 小时

---

## Phase 5: Verify（验证）

**目标**：确保所有 task 组合在一起能正确工作。

### 步骤

1. **单元测试全跑**
   - 运行所有 task 自带的测试
   - 修复失败项

2. **集成测试**
   - 对照 PRD 验收 checklist 逐条跑
   - 重点测试跨模块边界：
     - 写路径端到端
     - 读路径端到端
     - 异常路径（故障注入）

3. **最终 Code Review**
   - 用最强模型对整个实现做一次全局 review
   - 检查跨模块的一致性
   - 确认 PRD 不变量逐条满足

4. **证据优先**
   - 不是"我觉得对了"，是"测试全绿了"
   - 截图/日志证明关键路径可用

### 产出
- 所有测试通过
- 全局 review 通过
- 已知问题清单（如有）

### 时间参考
- 1-2 小时

---

## Phase 6: Ship（交付）

**目标**：集成到宿主系统，可实际使用。

### 步骤

1. **集成**
   - 接入宿主框架
   - 端到端冒烟测试

2. **文档更新**
   - 更新 CLAUDE.md 反映最终实现
   - 更新 ARCHITECTURE.md 反映实际结构
   - 记录已知限制和 v2 待办

3. **发布**
   - git commit + tag
   - 通知相关人员

### 产出
- 可运行的集成系统
- 最终文档

---

## 流程总览

```
Phase 1: Research (1-2天)
  问题定义 → 方案调研 → 边界确定
    ↓
Phase 2: PRD + 三方审查 (0.5-2天)
  起草 → 独立审查 → 三模型交叉审查 → 迭代修订 → 封板
    ↓
Phase 3: Plan (1-3小时)
  CLAUDE.md → ARCHITECTURE.md → 架构图 → Task 分解(TDD) → 依赖分层
    ↓
Phase 4: Build (2-4小时)
  分批 spawn → TDD 红绿循环 → 两阶段 Review → 下一批
    ↓
Phase 5: Verify (1-2小时)
  单元测试 → 集成测试 → 全局 Review → 证据确认
    ↓
Phase 6: Ship (1-2小时)
  集成 → 文档 → 发布
```

**典型项目总时间**：3-5 天（中等复杂度）

---

## 核心原则

1. **人做决策，AI 做执行** — 你决定做什么，AI 决定怎么写
2. **先想清楚再动手** — Phase 1-3 占总时间的 60-70%，这是对的
3. **精度优先于速度** — 给 agent 少而精的 context，比给一大坨好
4. **测试驱动（TDD）** — 先写失败测试，再写最小实现。没有测试的代码不算完成
5. **两阶段 Review** — 先查规格符合，再查代码质量。不是一次笼统的"看看行不行"
6. **多模型交叉验证** — 单一模型有盲区，三方审查发现更多
7. **模型分级** — 机械任务用便宜模型，架构任务用最强模型
8. **失败是正常的** — 10-20% 的 agent session 失败，重开比纠正快
9. **证据优先于声明** — 跑通了才算完成，不是"我觉得对了"
10. **流程沉淀** — 每次项目结束更新这份 SOP，复利积累

---

## 致谢

本 SOP 融合了以下实战经验：
- Boris Cherny（Claude Code 创始人）的并行 session + CLAUDE.md 工作流
- Jesse Vincent（obra/superpowers）的 TDD + 两阶段 Review + subagent-driven-development
- FPMS 项目的多模型交叉审查实战

---

## 版本历史

- v1.0 (2026-03-17): 首版，基于 FPMS 项目实战经验提炼
- v1.1 (2026-03-17): 融入 Superpowers 框架的 TDD、两阶段 Review、Task 粒度细化、模型分级策略
- v1.2 (2026-03-17): Gemini Deep Think 审查反馈 — Phase 3.5 骨架先行、AI-TDD 分离（测试与实现分 agent）、RFC 接口防篡改协议、Actionable Errors
- v1.3 (2026-03-17): GPT 审查反馈 — Phase 3.6 Invariant Tests 先行（把 PRD 铁律编译成自动化测试，在 coding 之前就存在）
