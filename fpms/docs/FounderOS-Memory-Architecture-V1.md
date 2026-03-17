# FounderOS Memory Architecture V1

*公司的可计算记忆*

---

## 一、使命

1. 让公司拥有持续性的认知
2. 让不同 Office 在统一事实上协作
3. 让 Founder 不再手动搬运上下文
4. 让治理可以嵌入记忆系统

---

## 二、六条原则

1. **事实优先** — 长期记忆底座是客观事实
2. **事实与判断分离** — "发生了什么" ≠ "我们怎么看"
3. **内部状态与外部口径分离** — 支付/融资/监管场景不能混
4. **分域访问** — 不同 Office 读写不同内容
5. **临时上下文默认不入库** — 先缓存，确认后再沉淀
6. **所有关键记忆可追溯** — 谁写的、什么时候、基于什么、谁批准

---

## 三、五层记忆模型（+临时层）

### Layer 1: Constitution Memory（宪法层）

公司的"基本法"，最稳定、最高级。

**存什么**: Mission/Vision/价值观、组织结构定义、Office 定义、风险原则、审批原则、业务术语、长期目标

**特点**: 变化少、权限高、全局共享、多数只读

**可写**: Founder、Governance Node

**作用**: 系统所有推理的最高约束

---

### Layer 2: Fact Memory（事实层）

最核心的底座 — 公司当前和历史的客观状态。

**存什么**: 商户状态、国家节点状态、产品版本状态、任务状态、指标数据、人员角色、审批结果、关键事件时间线、系统配置

**示例**:
- 菲律宾节点当前状态 = 可测试
- 某商户 KYC 状态 = 待补资料
- Webcash V1 完成度 = 42%
- 本月现金 runway = 5.2 months

**可写**: 对应 Office 在职责范围内可写，高风险事实需审批

**作用**: 所有 Office 共享的现实基础

---

### Layer 3: Judgment Memory（判断层）

对事实的解释。

**存什么**: 优先级判断、可靠性评价、方向建议、重要性判断、风险标签、融资窗口判断

**必须记录**: judgment, reason, based_on_facts, created_by, confidence, timestamp, expiry/review_date

**为什么单独一层**: 判断不是永恒真理。不分层就会把阶段性策略误认为长期事实。

---

### Layer 4: Office Memory（Office 专属记忆）

各 Office 的工作记忆与专业语境。

| Office | 存什么 |
|--------|--------|
| Operations | 商户 onboarding 历史、客户支持记录、部署经验 |
| Capital | 投资人偏好、路演版本、融资状态、财务模型 |
| Compliance | 合规风险备注、监管解读、KYC/KYT 异常案例 |
| Risk | 风险模式、异常案例、欺诈规则、冻结逻辑 |
| Product & Engineering | PRD 历史、技术债、架构判断、bug pattern |
| Growth / External Comms | 外部内容风格、市场反馈、品牌表述 |

**特点**: 专业密度高、不适合全员共享、读写需权限控制

---

### Layer 5: Narrative Memory（叙事层/对外口径）

**为什么必须有**: 公司存在两种真相 —

| 内部运行真相 | 外部叙事口径 |
|-------------|-------------|
| 节点可测试但不可规模化 | 已建立基础节点能力 |
| 产品只有 demo | 已完成初步打通 |
| 融资进度并不稳 | 正在推进新一轮融资 |

两者都合法，但不能混。

**可写**: Capital / Growth / Founder，高敏感项需审批

---

### Layer 6: Temporary Context（临时上下文）

**用途**: 单次任务推理、会话临时上下文、草稿、分析缓存

**写回长期 memory 的条件**:
1. 被 Founder 确认
2. 被审批通过
3. 被系统标记为高价值且人工复核通过

---

## 四、层间关系

```
Constitution → 限制所有层（最高约束）
     ↓
Fact → 是 Judgment 的基础（判断必须引用事实）
     ↓
Judgment → 为 Office 提供建议
     ↓
Office Memory → 为 Office 压缩上下文
     ↓
Narrative → 必须基于 Facts/Judgments，不能覆盖 Facts
     ↓
Temporary Context → 默认只读，不直接入库
```

---

## 五、读取逻辑（按角色裁剪）

| 角色 | 优先读取 | 不需要读 |
|------|---------|---------|
| **Founder** | Constitution + 全局 Fact + 高层 Judgment + Office 摘要 + Narrative + 审批历史 | — |
| **Operations** | Constitution(精简) + 商户 Fact + Ops Memory + 风险 Judgment | 融资 Narrative、董事会材料 |
| **Capital** | 财务融资 Fact + Investor Judgment + Narrative + 业务里程碑 | 客服记录、商户支持日志 |
| **Compliance** | Constitution + 合规 Fact + Compliance Memory + 风险 Judgment + 审批记录 | — |

---

## 六、写入规则

| 层 | 可写 | 不可写 |
|----|------|--------|
| Constitution | Founder, Governance Node | 普通 Office, 自动执行器 |
| Fact | 对应 Office 在职责范围内; 高风险需审批 | 跨 Office 随意改; Narrative 覆盖 |
| Judgment | 各 Office 写自己的(必须附依据+置信度) | 直接改变 Fact |
| Office Memory | 对应 Office + 被授权 Agent | — |
| Narrative | Capital / Growth / Founder; 高敏感需审批 | — |
| Temporary | 当前任务运行系统 | 默认不持久化 |

---

## 七、最小数据结构

### memory_fact
id, entity_type, entity_id, key, value, source, created_by, updated_by, timestamp, confidence, visibility_scope

### memory_judgment
id, subject_type, subject_id, judgment_type, judgment, reason, based_on_fact_ids, created_by, office, confidence, created_at, review_at, visibility_scope

### office_memory_entry
id, office_name, title, content, tags, related_entities, author, created_at, sensitivity_level

### narrative_entry
id, narrative_type, audience, title, content, based_on_fact_ids, approved_by, version, created_at, status

### memory_event_log
id, action, actor, target_memory_type, target_id, before, after, timestamp, approval_id

---

## 八、支付公司特别要求

1. **合规事实硬隔离** — KYC/可疑交易/监管沟通不能被普通 Office 读取
2. **资金与节点状态审批写入** — 节点状态变更(测试→live)、商户风险调整、通道开放都需审批
3. **Narrative 和 Fact 强隔离** — 支付行业最怕自我叙事覆盖真实状态

---

## 九、MVP 范围

**先做 4 层**: Constitution + Facts + Office Memory + Temporary Context

**先支持 3 个 Office**: Chief of Staff / Operations / Capital (或 Compliance)

**先支持 3 个实体**: Tasks / Nodes / Metrics

---

## 十、设计原则（一句话）

**FounderOS 的 Memory 不是"把所有东西记住"，而是"把公司最重要的事实、判断、边界和叙事，按层次和权限组织起来"。**

它是公司的可计算记忆。
