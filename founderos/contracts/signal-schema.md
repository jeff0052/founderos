# Signal Schema

_给AI看的：外部信号数据的精确定义_

---

## Signal 定义

Signal 是来自外部世界的重要变化。Signal 帮助 Founder 感知环境变化。

Signal 的特点：
- 不确定
- 不连续
- 可能改变战略

---

## Schema

```yaml
Signal:
  id: string  # format: SIG-YYYY-MM-DD-NNN
  created_at: datetime
  
  # 分类
  source: enum [market, partner, investor, technology, regulation, user_feedback, competitor]
  
  # 内容
  title: string  # max 80 chars，一句话概要
  detail: string  # 详细描述
  
  # 评估（AI初评 + Jeff确认）
  importance: enum [critical, high, medium, low]
  urgency: enum [immediate, this_week, this_month, no_rush]
  
  # 关联
  related_module: enum [uniweb, onta, license, vibecash, general]
  
  # 状态
  status: enum [new, reviewed, acted_on, archived]
  decision_ref: string | null  # 如果触发了Decision，关联ADR编号
  
  # Jeff的判断（人类填写）
  founder_note: string | null
```

## 处理规则

### AI 自动处理
1. 接收到新信号 → 自动分类 source
2. 自动评估 importance 和 urgency
3. critical + immediate → 立即通知 Jeff
4. high + this_week → 写入 Signals 面板，等周度 Review
5. medium/low → 存档，不打扰

### Jeff 处理
1. 查看 AI 筛选出的 critical/high 信号
2. 补充 `founder_note`（人类判断）
3. 决定是否触发新的 Decision
4. 标记 status 为 reviewed 或 acted_on

## Signal 来源定义

| source | 描述 | 典型示例 |
|--------|------|---------|
| market | 市场变化 | 支付行业趋势、用户行为变化 |
| partner | 合作伙伴 | 合作意向、对接进展、需求变化 |
| investor | 投资人 | 融资机会、战略建议 |
| technology | 技术 | 新技术出现、技术标准变化 |
| regulation | 监管政策 | 新法规、牌照要求变化 |
| user_feedback | 用户反馈 | 产品反馈、投诉、需求 |
| competitor | 竞争对手 | 竞品动态、市场格局变化 |

## 显式排除

- **不包含** 内部运营数据（属于 State）
- **不包含** 任务分配信息（属于 Mission）
- **不自动触发** Decision（只有 Jeff 可以做决策）
- **不评估** 信号的真实性（AI只做分类和重要性初评，真伪由人类判断）
