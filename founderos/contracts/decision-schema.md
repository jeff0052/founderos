# Decision Schema

_给AI看的：战略决策数据的精确定义_

---

## Decision 定义

Decision 是 Founder 基于 State + Signals 做出的关键决策。

Founder 每周只做少量决策。Decision 以 ADR（Architecture Decision Record）形式记录。

---

## Schema

```yaml
Decision:
  id: string  # format: ADR-YYYY-MM-DD-NNN
  created_at: datetime
  
  # ADR 三要素
  context: string    # 为什么要做这个决策（背景、约束、信号）
  decision: string   # 选了什么
  consequences:
    positive: string[]  # ✅ 正面后果
    negative: string[]  # ⚠️ 负面后果/代价
  
  # 关联
  triggered_by: string[]  # Signal IDs 或 State 变化
  related_module: enum [uniweb, onta, license, vibecash, general]
  resulting_missions: string[]  # 由此产生的 Mission IDs
  
  # 状态
  status: enum [active, superseded, reversed]
  superseded_by: string | null  # 如果被新决策替代
```

## 决策规则

1. **每周 ≤ 3 个战略决策** — 防止决策疲劳
2. **每个 Decision 必须记录 Context** — 不只记录"选了什么"，更记录"为什么选"
3. **必须记录 Consequences** — 包含正面和负面
4. **Decision 不可轻易删除** — 只能被新 Decision supersede
5. **只有 Jeff 可以创建 Decision** — AI 可以建议，但不能决策

## 存档规则

- 所有 Decision 存放在 `decisions/` 目录
- 文件名格式：`ADR-YYYY-MM-DD-NNN.md`
- 每个 Decision 一个文件
- 包含完整的 ADR 三要素

## 显式排除

- **不包含** Mission 级别细节（Decision 只定方向，不管执行）
- **不包含** 执行计划（由 AI/团队基于 Decision 自行拆解）
- **不自动生成** Decision（AI 只能建议，Jeff 做决策）
- **不评估** Decision 的正确性（没有"对错"，只有"consequences"）
