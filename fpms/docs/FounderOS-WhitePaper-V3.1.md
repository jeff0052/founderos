# FounderOS 白皮书 V3.1

*A Control System for One-Person Companies — 第一性原理重构版*

---

## 零、一句话定义

**FounderOS 的目标不是帮助 Founder 管理任务，而是帮助 Founder 在不确定中持续分配注意力、资源与控制权。**

---

## 一、公司的不可再分元素

剥离所有软件概念，公司本质上只有四个东西：

| 元素 | 定义 |
|------|------|
| **Objective** | 有限时间内可验证的目标 |
| **Resource** | 现金、时间、注意力、带宽、关系、合规容量 |
| **Decision** | 把有限资源投向某些方向而非其他方向 |
| **Feedback** | 市场是否认可、效率是否提高、风险是否上升 |

FounderOS 就是围绕这四个元素建立的控制系统。

---

## 二、系统目标函数（优先级不可调换）

```
1. 生存概率        — 活着是一切前提
2. 决策杠杆率      — 每个决策撬动多大结果
3. 资源效率        — 投入产出比
4. 战略推进速度    — 文明等级跃迁节奏
```

**所有模块在冲突时，按此顺序裁决。** 增长和生存冲突时，选生存。效率和杠杆率冲突时，选杠杆率。

---

## 三、核心循环（十步闭环）

```
 ① Objective     当前阶段系统要赢什么
      ↓
 ② State         系统当前在哪里（业务指标 + 控制指标）
      ↓
 ③ Resource      系统还能投入什么
      ↓
 ④ Signals       外部发生了什么变化
      ↓
 ⑤ Interpretation 这些变化意味着什么
      ↓
 ⑥ Decision      资源该投向哪里
      ↓
 ⑦ Control       允许系统以什么边界执行
      ↓
 ⑧ Execution     谁来做，做到什么程度
      ↓
 ⑨ Feedback      系统偏离了吗（执行偏差 or 假设偏差）
      ↓
 ⑩ Memory        哪些东西应该沉淀为长期能力
      ↓
 [回到 ① 更新 Objective / ② 更新 State]
```

---

## 四、十大模块详解

### ① Objective（目标）

当前阶段的可验证目标。不是 Mission Statement，是**系统的优化方向**。

**规则**:
- 目标必须有时间边界
- 目标必须可验证（是/否，不是"争取"）
- 同一时间最多 1 个主目标 + 2 个辅助目标
- 目标变更 = L0 Decision，必须 Founder 亲自决定

**示例**:
```
主目标: 2026 Q2 前完成菲律宾真实交易测试（≥100笔）
辅助1: 支付系统核心模块 v1 上线
辅助2: 完成 Pre-A 融资 term sheet
```

**与文明等级的关系**: 目标是当前文明等级向下一级跃迁的关键路径。

---

### ② State（状态）

公司当前的客观状态。分两类：

#### 业务指标（公司长得怎么样）

| 业务线 | 核心指标 |
|--------|---------|
| 收单 | Merchant Count, Monthly GMV, Net Profit |
| 发卡 | Active Cards, Monthly Volume |
| 跨境 | Corridor Count, Settlement Volume |
| 钱包 | Active Wallets, Balance Volume |
| 稳定币 | On-chain Volume, Bridge Throughput |

#### 控制指标（公司会不会失控）

| 指标 | 含义 | 阈值示例 |
|------|------|---------|
| Cash Runway | 还能活几个月 | < 6 months = 🔴 |
| Founder Attention Load | Founder 同时关注几件事 | > 5 = 🟡 |
| Critical Dependencies | 关键单点依赖数 | > 3 = 🟡 |
| Open High-Risk Items | 未决高风险事项 | > 2 = 🔴 |
| Agent Reliability | Agent 执行成功率 | < 90% = 🟡 |
| Decision Backlog | 等待 Founder 决策的队列 | > 5 = 🔴 |

**实现**: FPMS 看板（任务状态）+ 业务 KPI + 控制仪表盘

---

### ③ Resource（资源层）— 新增

每个决策都在消耗资源。没有资源模型，所有决策看起来都"可以做"。

**六类资源**:

| 资源 | 可量化吗 | 约束 |
|------|---------|------|
| **Cash** | 精确到月 | Runway < 6M 触发保守模式 |
| **Founder Time** | 每周 ~50h | 不可并行，最稀缺 |
| **Technical Bandwidth** | Agent 并发数 + Token 预算 | 有硬上限 |
| **Relationship Capital** | 合作方/投资人关系 | 消耗后需时间恢复 |
| **Compliance Capacity** | 同时处理的合规事项数 | 支付公司硬约束 |
| **Organizational Bandwidth** | 系统同时推进的 Mission 数 | > 5 个 active = 危险 |

**资源约束规则**:
- 每个 L0/L1 Decision 必须声明：消耗什么资源、占用多久、挤压了谁、机会成本
- 当 Cash Runway < 阈值时，特定决策类别自动失效
- 当 Founder Attention Load > 阈值时，系统建议推迟低优先级 Decision
- Resource 状态是 State 的一部分，每周更新

---

### ④ Signals（外部信号）

来自外部世界的重要变化。

**来源**: 市场、合作伙伴、投资人、技术、政策监管、用户反馈

**数据结构**:
```
signal:
  source, type, description
  impact (1-5), confidence (0-1)
  resource_implication（影响哪些资源）
  created_at, expires_at
```

**降噪规则**: 低 impact（≤2）且低 confidence（≤0.3）的信号不进入 Interpretation 层。可用规则引擎/小模型做第一道清洗。

---

### ⑤ Interpretation（解释层）

把噪音变成洞察，把 Founder 的直觉结构化。

**作用**:
- Signal 分类与权重评估
- 冲突信号处理
- 资源竞争分析（这些信号在争夺什么资源）
- 战略影响评估

**输出结构**:
```
interpretation:
  signal_ids: [引用的信号]
  insight: 核心判断
  confidence: 置信度
  resource_impact: 影响哪些资源
  strategic_implication: 对当前 Objective 的影响
  suggested_action: 建议（供 Founder 参考，不是命令）
  expiry: 这个判断的有效期
```

**对应 Memory Architecture**: Layer 3 Judgment Memory

---

### ⑥ Decision（Founder 决策）

**Founder 最稀缺的不是判断力，是注意力分配权。**

#### 决策分级

| 级别 | 决策者 | 范围 | 注意力消耗 |
|------|--------|------|-----------|
| **L0** | Founder Only | 目标变更、战略转向、融资、重大人事 | 高 |
| **L1** | Office 提案 → Founder 确认 | 架构方向、新产品线、高风险变更 | 中（每周 ≤3） |
| **L2** | Office 自主 + 通知 Founder | 技术选型、日常运营、常规执行 | 低（看通知即可） |
| **L3** | Agent 自主 | 代码实现、文档更新、状态同步 | 零 |

#### 注意力过滤规则

| 场景 | 处理方式 |
|------|---------|
| 什么问题值得打断 Founder？ | L0 + 触发 Kill Switch 的异常 |
| 什么问题延迟到周会？ | L1 非紧急 |
| 什么问题 Office 自治？ | L2/L3 |
| 什么问题不该进系统？ | Impact ≤ 2 的 Signal |

#### Decision 模板（L0/L1 必须填）

```
decision:
  what: 做什么
  why: 基于哪些 Signal + Interpretation
  objective_alignment: 对当前 Objective 的贡献
  resource_cost: 消耗什么资源、占用多久
  opportunity_cost: 不做这个，能做什么
  expected_outcome: 预期结果
  time_horizon: 时间范围
  kill_condition: 什么情况下放弃
  owner: 谁负责执行
```

---

### ⑦ Control（控制层）

控制的本质不是下命令，是**约束状态空间** — 让系统只能在安全、有效、可逆的路径中运行。

#### 五个维度

| 维度 | 定义 |
|------|------|
| **Authority** | 谁有权执行 |
| **Constraints** | 必须满足什么前置条件 |
| **Validation** | 怎么判断执行成功 |
| **Override** | 谁可以强制改变方向 |
| **Escalation** | 出问题时的升级路径 |

#### 系统级约束（Constitution 代码化）

- Office 不可同时启动 > 3 个高风险 Mission
- 当 Cash Runway < 阈值时，L1 新决策需额外论证资源来源
- 当 Agent 成功率 < 阈值时，自动降低其决策权限（L2 → 需确认）
- 当 Narrative 与 Fact 冲突时，Fact 优先，Narrative 标记为"待修正"
- **核心底线必须代码化（Hardcoded）**，AI 只有提议权，代码层握有绝对否决权

---

### ⑧ Execution（执行层 / Office 体系）

每个 Office 是一个 **Capability**（能力），不只是一个部门名称。

| Capability | 当前 Office 名称 | 职责 |
|-----------|-----------------|------|
| **Build** | Product & Engineering (CTO) | 技术方案、编码、质量 |
| **Sell** | Growth | 市场、品牌、外部沟通 |
| **Protect** | Risk + Compliance | 风控、合规、KYC/AML |
| **Finance** | Capital | 融资、财务、投资人关系 |
| **Operate** | Operations | 商户运营、部署、客户支持 |
| **Learn** | （内嵌于 Memory 系统） | 知识沉淀、回顾、改进 |

**Office 是现阶段的执行抽象，不是最终本体。组织名字会变，Capability 不会变。**

每个 Mission 必须包含：
```
mission:
  title, owner_capability, deadline
  expected_result
  resource_cost（消耗什么资源）
  dependency（前置条件）
  risk_check（风控检查）
  validation_condition（完成标准）
  escalation_path（出问题找谁）
  decision_level（L0/L1/L2/L3）
```

---

### ⑨ Feedback（反馈 / 偏差检测）— 增强

反馈的核心不是"事后复盘"，是**尽可能早地发现系统偏离目标**。

#### 两类偏差（处理方式完全不同）

| 类型 | 定义 | 处理 |
|------|------|------|
| **Execution Deviation** | 任务没有按预期推进 | 调人、调任务、调资源 |
| **Thesis Deviation** | 原先判断世界的假设错了 | 改战略、改目标、改文明路径 |

**示例**:
- 菲律宾 partner 没推进 → Execution Deviation → 换 partner / 加资源
- 稳定币监管方向整体转向 → Thesis Deviation → 重新评估 L3 文明路径

#### 检测频率

| 频率 | 内容 | 实现 |
|------|------|------|
| 实时 | FPMS 风险标记（blocked/at-risk/stale） | 纯 Python |
| 分钟级 | Agent 健康度、Token 消耗异常 | 守护进程 |
| 小时级 | 业务指标偏离 | Cron + 阈值检测 |
| 每日 | 全量 State 核对 | 自动化脚本 |
| 每周 | Founder 战略回顾（Thesis 检验） | Founder 手动 |

**心跳必须用传统代码**（Python/Cron），只有捕获到异常时才唤醒 Agent 做深度诊断。

#### Kill Switch（熔断机制）

| 级别 | 触发条件 | 动作 |
|------|---------|------|
| L1 | 指标偏离预期 | 标记风险，继续执行 |
| L2 | 关键指标跌破阈值 | 暂停相关 Mission，等 Founder 确认 |
| L3 | 系统性问题 | 回到上一稳定 State |
| L4 | 严重异常 | 全面暂停，回到手动模式 |

---

### ⑩ Memory（记忆沉淀）

**五层 + 临时层**:

```
Layer 1  Constitution    公司宪法（代码化，不只是 Prompt）
Layer 2  Fact            客观事实（FPMS + KPI + Resource 状态）
Layer 3  Judgment        解释层输出（必须附依据 + 置信度 + 有效期）
Layer 4  Office Memory   各 Capability 的专属工作记忆
Layer 5  Narrative       对外口径（与 Fact 强隔离）
Layer 6  Temporary       临时上下文（默认不入库）
```

**六条原则**: 事实优先、事实判断分离、内外口径分离、分域访问、临时不入库、可追溯

**新增约束**:
- Resource 状态纳入 Layer 2 Fact
- Interpretation 输出纳入 Layer 3 Judgment（带有效期，过期自动降权）
- 每个新模块必须先证明它在减少摩擦，而不是增加结构感

---

## 五、Civilization Map（文明等级）— 增强

文明等级不只是叙事，是**控制变量**。

### 规则

- 每一级有**可验证门槛**（不是感觉，是指标）
- **达级改变控制策略**（Risk tolerance、决策权限、资源配置规则都变）
- **降级有定义**（关键指标跌破门槛 = 降级，触发保守模式）

### 支付文明路径

| Level | 阶段 | 门槛 | 控制策略变化 |
|-------|------|------|------------|
| L1 | Offline acquiring | 首笔真实交易 | 全手动，Founder 亲力亲为 |
| L2 | Regional network | 3 国节点在线，月 GMV > X | Agent 开始接管执行，决策下放 L2 |
| L3 | Stablecoin settlement | 链上清算上线，合规通过 | 多 Office 并行，Resource 模型必须成熟 |
| L4 | Global infrastructure | 全球网络效应 | 系统高度自治，Founder 只做 L0 |

---

## 六、产品原则

### 1. 极简

每个新模块必须先证明它在减少摩擦，而不是增加结构感。

### 2. 决策下放

Founder 只做 L0/L1。系统不因等待 Founder 而停滞。

### 3. 防崩优先

进攻靠 Vision，防守靠 Stability。任何时候可以回到手动模式。

### 4. 注意力守恒

系统的最高产出是帮 Founder 少看 90% 不重要的事，只介入高杠杆节点。

### 5. 摩擦消灭

FounderOS 的价值 = 消灭了多少组织摩擦（信息传递、决策等待、上下文切换、复盘追责、跨角色理解）。

---

## 七、演进路径

| 版本 | 形态 | 状态 |
|------|------|------|
| V1 | 手动系统 | ✅ |
| V2 | AI 辅助分析 | ✅ |
| **V3** | **Agent 执行系统** | **← 当前** |
| V4 | 自动化公司操作系统 | 未来 |

### V3 进度

| 组件 | 状态 |
|------|------|
| FPMS（State 引擎） | ✅ v1 完成 |
| Memory Architecture | ✅ 设计完成 |
| CTO Agent（Build） | 📝 PRD V2 完成 |
| Objective 定义 | ❌ |
| Resource 模型 | ❌ |
| Signal 结构化 | ❌ |
| Interpretation | ❌ |
| Decision 模板化 | ❌ |
| Control 代码化 | ⚠️ 部分 |
| Stability / Kill Switch | ⚠️ 部分 |

---

## 八、最终愿景

一个 Founder 管理一家越来越复杂的公司。

不是因为"一个人做完所有事"，而是因为"组织协作摩擦被极度压缩"。

```
人类提供 Vision + Judgment
AI 提供 Execution
FounderOS 提供 Control

公司 = Objective + Resource + Decision + Feedback
FounderOS = 让这四个元素可计算、可控制、可演化
```

**这不是管理工具，不是 AI 助手。这是人类第一次把公司控制权结构化。**

---

*V3.1 基于 V3 + GPT 第一性原理压力测试重构。新增：Objective（目标函数）、Resource（资源层）、Execution/Thesis Deviation 分类、Civilization 作为控制变量、注意力守恒原则。十步闭环，不可再减。*
