# Constitution 物理拦截器 — Feasibility Check + Design

> **Constitution Guard 不是代码质量工具，而是治理边界的物理执行器。**
> 它保护的是：资金安全边界、不变量完整性、Founder 审批权。

**日期**: 2026-03-18
**Author**: CTO Agent
**Status**: Phase 0 Design Complete — 待 Founder 确认
**Constitution 条款**: 第 3 条（支付核心路径审批）、第 5 条（铁律测试防篡改）、第 13 条（浮点数拦截）

---

## Phase -1: Feasibility Check

### 1. ROI

**做了能带来什么？**

这三个拦截器解决的是同一个核心问题：**AI agent 可以无视文档级规则**。

当前 Constitution 是纯文本约束 — prompt 里写着"不准用浮点数"，但没有任何物理机制阻止 agent 写出 `amount = 0.1 + 0.2`。随着系统规模扩大（尤其是支付系统上线后），这个 gap 从"理论风险"变成"必然事故"。

具体收益：
- **第 13 条（Float Scanner）**：直接防止金额精度 bug — 这类 bug 在支付系统中是 P0 事故，一旦发生可能涉及资金损失
- **第 5 条（Test Lock）**：防止 AI agent "为了让测试通过而修改测试" — 这是 AI coding 最常见的作弊模式
- **第 3 条（Core Path Gate）**：在支付核心路径变更时强制人类审批 — 最后一道防线

**不做会怎样？**

短期（支付系统未上线）：风险低，Constitution 作为 prompt 约束勉强够用。
中期（支付系统开发中）：AI agent 大量写代码时，概率性违反 Constitution 是必然的。一次浮点数 bug 或一次铁律测试被改就可能导致系统性故障。
长期：如果 Constitution 不能物理执行，它就退化为"建议"，整个治理框架失去意义。

**结论：ROI 正向。这是基础设施投资，越早做越好。**

### 2. 资源消耗

| 模块 | 预估工时 | 复杂度 |
|------|---------|--------|
| AST Float Scanner | 2-3h | 中（AST 解析 + 路径识别） |
| Ironclad Test Lock | 1-2h | 低（hash 比对，逻辑简单） |
| Core Path Gate | 2-3h | 中（路径模式匹配 + 审批流） |
| 集成 + CI hook | 1-2h | 低（pre-commit / CI pipeline） |
| 铁律测试 | 2-3h | 低（每个模块 10-15 个 case） |
| **总计** | **8-13h** | — |

这是一个小型项目，不会挤压其他工作。主要消耗在 AST Scanner 的路径识别逻辑上。

### 3. 复杂度影响

**对现有系统的影响：最小。**

三个拦截器是**独立模块**，通过 CI hook（pre-commit + CI pipeline）触发，不侵入业务代码：
- 不修改任何现有模块
- 不引入新的运行时依赖
- 作为开发工具链的一部分存在，不影响生产代码

**复杂度预算：**
- 模块数：+3（scanner, lock, gate）+ 1（共享配置）
- 层级深度：1（全部是顶层工具）
- 依赖边数：各模块独立，仅共享配置

### 4. 稳定性风险

**对现有测试的影响：零。**

拦截器是**静态分析 + 文件校验**工具，运行在 CI/pre-commit 阶段，不参与测试执行。现有 tests 完全不受影响。

唯一的风险点：如果 AST Scanner 的路径识别规则写得太宽，可能产生 false positive（误报非金额代码中的 float 使用）。这通过精确的路径配置和白名单机制解决。

### Verdict: ✅ GO

**理由：**
1. 风险收益比极好 — 小投入防止大事故
2. 资源消耗可控 — 8-13h，不影响主线
3. 零侵入 — 不碰现有代码和测试
4. 支付系统开发前完成 = 从第一行代码就有保护

### Kill Criteria

满足任一则终止：
- [ ] 超过 3 天无实质进展（卡在技术难点上）
- [ ] AST 解析方案无法覆盖 >80% 的 float 使用场景
- [ ] 拦截器引入的 CI 时间增加 >30 秒（影响开发体验）
- [ ] 误报率 >5%（开发者频繁需要手动豁免）

---

## Phase 0: Design

### 系统边界图

```
┌─────────────────────────────────────────────┐
│                 CI Pipeline                  │
│                                              │
│  ┌──────────────┐  ┌──────────────────────┐  │
│  │  pre-commit   │  │   CI check (GitHub)  │  │
│  │  hook         │  │                      │  │
│  └──────┬───────┘  └──────────┬───────────┘  │
│         │                     │               │
│         └────────┬────────────┘               │
│                  ▼                             │
│  ┌───────────────────────────────┐            │
│  │     constitution_guard.py      │            │
│  │     (统一入口 / CLI)           │            │
│  └──────────┬────────────────────┘            │
│             │                                 │
│    ┌────────┼────────┐                        │
│    ▼        ▼        ▼                        │
│ ┌──────┐┌──────┐┌──────┐                     │
│ │Float ││Test  ││Core  │                     │
│ │Scan  ││Lock  ││Gate  │                     │
│ └──┬───┘└──┬───┘└──┬───┘                     │
│    │       │       │                          │
│    ▼       ▼       ▼                          │
│ [BLOCK] [BLOCK] [FLAG for Founder Review]     │
└─────────────────────────────────────────────┘

数据流：
  Git diff / staged files → constitution_guard → Pass / Block / Flag

配置：
  constitution_guard.yaml
    ├── float_scanner:
    │     paths: [src/payments/**, src/wallet/**, ...]
    │     whitelist: [tests/**, scripts/**, ...]
    ├── test_lock:
    │     protected_dir: tests/invariants/
    │     hash_file: .invariant_hashes.json
    └── core_path_gate:
          core_paths: [src/payments/core/**, src/settlement/**, ...]
          approvers: [jeff]
```

### 设计决策

**为什么用统一入口而不是三个独立工具？**
- 一个 CLI、一个配置文件、一次 CI 调用
- 减少维护负担，统一报告格式
- 每个 scanner 仍然是独立模块，可单独测试

**为什么基于 Git diff 而不是全量扫描？**
- 全量扫描太慢（违反 Kill Criteria 的 30 秒限制）
- 增量扫描只检查变更的文件，开发体验好
- Test Lock 除外：它需要校验整个 `tests/invariants/` 目录的 hash

**为什么 Core Path Gate 是 "Flag" 而不是 "Block"？**
- Block 会阻止所有支付相关变更，包括 bug fix
- Flag + 审批流更灵活：标记为需要 Founder 审批，但不阻止提交
- 在 CI 中体现为：check 标红 + 自动创建审批 comment

---

### Module Spec 1: AST Float Scanner

```
模块名: ast_float_scanner
  
  职责: 
    扫描 Python 源码的 AST，检测金额相关代码路径中的浮点数使用。
    包括：float 字面量、float() 调用、float 类型注解、
    math 库浮点函数、除法运算符（/）在金额上下文中的使用。
  
  依赖: 
    - Python ast 模块（标准库）
    - constitution_guard.yaml（路径配置）
    - Git（获取 staged/diff 文件列表）
  
  行为规则: 
    1. 从 Git diff 获取变更的 .py 文件列表
    2. 过滤：只检查 constitution_guard.yaml 中配置的 paths（支付/金额相关路径）
    3. 对每个文件进行 AST 解析
    4. 遍历 AST 节点，检测以下模式：
       a. ast.Constant 节点中 type(value) == float
       b. ast.Call 节点中 func.id == 'float'
       c. ast.AnnAssign / ast.arg 中类型注解为 'float'
       d. ast.BinOp 中 op == ast.Div（在金额上下文中）
    5. 检查白名单：如果文件在 whitelist 路径中，跳过
    6. 检查行内豁免注释：`# noqa: float-ok <reason>` — 必须带原因，必须 Founder 审批，30 天后自动失效需续期
    7. 发现违规 → 输出文件名、行号、违规类型、代码片段
    8. 任何违规 → 返回非零退出码（阻止提交）
  
  约束: 
    - 单文件扫描 < 100ms
    - 零运行时依赖（只用标准库）
    - 误报可通过白名单或行内注释豁免，但豁免必须有理由
    - AST 解析失败：pre-commit → warning 跳过；CI → fail 阻止（本地宽松，远端严格）
  
  显式排除: 
    - 不检查非 Python 文件
    - 不检查第三方库代码（vendor/、.venv/）
    - 不做运行时类型推断（只做静态 AST 分析）
    - 不做语义级"金额上下文"推断 — 这是路径级 float 禁令，不是语义检查器
    - 不检查测试文件中的 float（测试可能需要 float 做断言）
    - 不自动修复，只报告
  
  Kill Criteria:
    - 无法覆盖 >80% 的 float 使用模式 → 方案无效
    - 单次扫描 >10 秒 → 开发体验不可接受
    - 误报率 >5% → 开发者会绕过它
```

### Module Spec 2: Ironclad Test Lock

```
模块名: ironclad_test_lock

  职责: 
    校验 tests/invariants/ 目录下的铁律测试文件是否被篡改。
    基于文件内容 hash 比对，任何修改（包括新增、删除、重命名、内容变更）
    都会被检测并阻止。

  依赖: 
    - hashlib（标准库，SHA-256）
    - .invariant_hashes.json（基线 hash 文件，存储在 repo 根目录）
    - Git（检测 staged changes）

  行为规则: 
    1. 从 Git staged files 中过滤 tests/invariants/ 路径下的文件
    2. 如果无相关文件变更 → Pass（快速路径）
    3. 如果有变更：
       a. 计算变更文件的 SHA-256 hash
       b. 与 .invariant_hashes.json 中的基线 hash 比对
       c. 检测四种违规：
          - MODIFIED: 文件内容 hash 不匹配
          - DELETED: 基线中有但 staged 中删除了
          - RENAMED: 文件名变更（通过 Git rename detection）
          - 注意：新增文件不是违规（新铁律测试是允许的）
       d. 任何违规 → 输出详情 + 返回非零退出码
    4. 基线更新流程（系统最危险的后门，必须最严格管控）：
       a. 运行 `constitution_guard update-hashes` 生成新的 hash 文件
       b. 此操作只应在 Founder 审批后执行
       c. 更新 hash 的 commit 必须包含审批记录（commit message 中注明）
       d. .invariant_hashes.json 自身纳入 core_path_gate 审批范围
       e. 新增铁律测试后必须立即更新基线并通过审批流

  约束: 
    - 检查速度 < 1 秒（hash 计算很快）
    - .invariant_hashes.json 本身受 Git 追踪，其变更也需要审批
    - 零容忍：没有白名单、没有豁免机制

  显式排除: 
    - 不检查 tests/invariants/ 以外的测试文件
    - 不检查测试内容的正确性（那是测试框架的事）
    - 不阻止新增铁律测试文件（只阻止修改和删除现有的）
    - 不负责执行测试，只负责文件完整性校验
    - 不做 hash 自动更新（必须显式命令 + 审批流）

  Kill Criteria:
    - Git rename detection 无法可靠工作 → 降级为只检查 modified/deleted
    - hash 冲突（SHA-256 下概率为零，但如果换算法需要评估）
```

### Module Spec 3: Core Path Gate

```
模块名: core_path_gate

  职责: 
    检测涉及支付核心路径（资金流向/费率/清结算）的代码变更，
    标记为需要 Founder 审批。不阻止提交，但在 CI 中标红。

  依赖: 
    - constitution_guard.yaml（核心路径配置）
    - Git（获取 diff 文件列表）
    - CI 系统（GitHub Actions / 其他，用于创建审批标记）

  行为规则: 
    1. 从 Git diff 获取变更文件列表
    2. 匹配 core_paths 配置（glob 模式）：
       - src/payments/core/**
       - src/settlement/**
       - src/wallet/core/**
       - src/fees/**
       - 以及其他 constitution_guard.yaml 中配置的路径
    3. 如果无匹配 → Pass
    4. 如果有匹配：
       a. 收集所有匹配的文件和变更摘要
       b. 生成审批请求报告：
          - 变更的文件列表
          - 每个文件的 diff 摘要（增/删/改行数）
          - 变更涉及的模块
       c. 在 CI 中：
          - 设置 check 状态为 "action_required"
          - 创建 PR comment 标注需要 Founder 审批
          - 添加 label: "needs-founder-approval"
       d. 在 pre-commit 中：
          - 输出 WARNING（不阻止提交）
          - 提醒开发者此变更需要 Founder 审批
    5. **硬门禁**：没有 Founder approval，PR 不可 merge（不只是 warning）
    6. 审批通过后：
       - Founder 在 PR 中 approve
       - CI re-run 时检测到 approval → Pass

  约束: 
    - 路径匹配必须精确，不能过宽（避免所有 PR 都被标记）
    - 审批状态持久化：approval 记录在 PR 中，不依赖外部存储
    - CI 集成必须是可选的（本地开发时 pre-commit 只做 warning）
    - 支持 dry-run 模式（开发者可以提前检查哪些文件会被标记）

  显式排除: 
    - 不检查文件内容（只看路径，内容审查是 code review 的事）
    - 不阻止本地提交（只在 CI 中强制审批）
    - 不处理审批流的细节（依赖 Git 平台的 review 机制）
    - 不做自动回滚或自动合并
    - 不替代 code review — 它只确保 Founder 知道并审批

  Kill Criteria:
    - 路径匹配误报率 >10%（太多 PR 被标记，审批疲劳）
    - CI 集成复杂度过高（需要 >2h 适配特定 CI 系统）
    - Founder 审批流程拖慢开发速度 >1 天（需要调整流程，不是工具的问题）
```

---

### 统一入口: constitution_guard CLI

```
模块名: constitution_guard

  职责:
    统一入口 CLI，协调三个拦截器模块的执行、配置加载和报告输出。

  依赖:
    - ast_float_scanner
    - ironclad_test_lock
    - core_path_gate
    - constitution_guard.yaml（配置文件）
    - Git

  行为规则:
    1. CLI 接口：
       - `constitution_guard check` — 运行所有拦截器（pre-commit / CI 默认命令）
       - `constitution_guard check --only float` — 只运行 Float Scanner
       - `constitution_guard check --only testlock` — 只运行 Test Lock
       - `constitution_guard check --only corepath` — 只运行 Core Path Gate
       - `constitution_guard update-hashes` — 更新铁律测试 hash 基线（需审批）
       - `constitution_guard status` — 显示当前配置和上次检查结果
    2. 配置加载：从 repo 根目录读取 constitution_guard.yaml
    3. 报告格式：
       - 终端输出：彩色 + emoji，一眼看懂
       - CI 输出：结构化 JSON（供 CI 系统解析）
    4. 退出码：
       - 0: 全部通过
       - 1: Float Scanner 或 Test Lock 发现违规（硬阻止）
       - 2: Core Path Gate 标记需要审批（软标记）

  约束:
    - 总执行时间 < 30 秒
    - 零外部依赖（只用 Python 标准库）
    - 配置文件格式简单（YAML，人类可读）

  显式排除:
    - 不做自动修复
    - 不与特定 IDE 集成（只做 CLI + CI）
    - 不做跨语言支持（当前只支持 Python）
    - 不管理 Git hooks 的安装（由项目的 Makefile/setup 负责）

  Kill Criteria:
    - 三个模块中任意两个被判定无效 → 统一入口失去意义
```

---

## 实施路径

```
Phase 1: 契约设计      → 本文档（已完成）
Phase 2: 规约编写      → 铁律测试 + 单元测试规约
Phase 2.5: Writing Plan → 详细实施步骤
Phase 3: AI 实现       → spawn coding agent
Phase 4: 验证          → 全量测试 + 集成到 CI

预计总时间: 8-13h（分 2-3 天完成）
```

## 复杂度预算

| 指标 | 上限 | 说明 |
|------|------|------|
| 模块数 | 4 | 3 scanner + 1 CLI 入口 |
| 层级深度 | 1 | 全部平铺，无嵌套 |
| 依赖边数 | 3 | CLI → 3 个 scanner，scanner 之间无依赖 |
| 外部依赖 | 0 | 全部标准库 |
| 配置文件 | 2 | constitution_guard.yaml + .invariant_hashes.json |

---

## 附录：constitution_guard.yaml 示例

```yaml
# Constitution Guard 配置
# 对应 Constitution 第 3、5、13 条

float_scanner:
  enabled: true
  # 需要检查浮点数使用的路径（glob 模式）
  paths:
    - "src/payments/**/*.py"
    - "src/wallet/**/*.py"
    - "src/settlement/**/*.py"
    - "src/fees/**/*.py"
  # 豁免路径（不检查）
  whitelist:
    - "tests/**"
    - "scripts/**"
    - "docs/**"
    - ".venv/**"
    - "vendor/**"

test_lock:
  enabled: true
  # 受保护的目录
  protected_dir: "tests/invariants/"
  # hash 基线文件
  hash_file: ".invariant_hashes.json"

core_path_gate:
  enabled: true
  # 核心路径（变更需要 Founder 审批）
  core_paths:
    - "src/payments/core/**"
    - "src/settlement/**"
    - "src/wallet/core/**"
    - "src/fees/**"
  # 审批人
  approvers:
    - "jeff"
  # CI 标签
  label: "needs-founder-approval"
```
