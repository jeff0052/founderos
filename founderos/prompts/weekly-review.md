# Weekly Review Prompt Template

_给AI看的：周度Review辅助工作指令_

---

## 上下文注入

读取以下文件：
1. `founderos/contracts/state-schema.md` — State 定义
2. `founderos/missions/*.md` — 所有模块任务
3. `founderos/world/payment-map.md` — 外部世界地图
4. `founderos/decisions/` — 历史决策
5. `memory/` — 本周所有日记

## 执行任务（按顺序）

### Step 1: State Update 报告
为 Jeff 准备 State 更新建议：
- 列出上周各模块核心指标变化
- 标注哪些数据需要 Jeff 确认/更新
- 格式：表格形式

### Step 2: Signal 汇总
汇总本周重要信号：
- 从本周日记中提取外部信号
- 按 importance 排序
- 标注哪些可能改变战略优先级
- 格式：编号列表，每条一行

### Step 3: Decision 辅助
基于 State + Signals，辅助 Jeff 做决策：
- 列出本周需要 Jeff 判断的事项
- 每项给出 2-3 个选项（不做推荐）
- Jeff 选择后，AI 记录为 ADR

### Step 4: Mission Review
生成任务进展报告：
- 按模块分组
- 每个 Mission 一行：title + status + next
- 红色标注 blocked 和超期任务
- 建议是否需要新增/取消 Mission

## 输出格式

```
🗓️ FounderOS Weekly Review
周期：MM/DD - MM/DD

━━━ STATE UPDATE ━━━
[State 数据表格]

━━━ SIGNALS ━━━
[本周重要信号列表]

━━━ DECISIONS NEEDED ━━━
[需要Jeff判断的事项]

━━━ MISSION PROGRESS ━━━
[按模块的任务进展]
```

## 显式排除

- 不替 Jeff 做决策（只提供选项）
- 不自动创建新 Mission（建议后等 Jeff 确认）
- 不删除或修改历史 Decision
- 不评估团队绩效（不是绩效工具）
