# Daily Check Prompt Template

_给AI看的：每日状态检查工作指令_

---

## 上下文注入

读取以下文件：
1. `founderos/missions/*.md` — 所有模块的任务状态
2. `founderos/world/payment-map.md` — 外部世界地图
3. `memory/YYYY-MM-DD.md` — 今日记忆

## 执行任务

### 1. 检查 Waiting 状态
扫描所有 status=waiting 的 Mission：
- waiting_since 超过 3 天 → 提醒 Owner
- waiting_since 超过 7 天 → 上报 Jeff
- 输出格式：`⏳ {mission_title} - 等待 {waiting_for} 已 {days} 天`

### 2. 检查 Deadline
扫描所有有 deadline 的 Mission：
- deadline 在 3 天内 → 提醒
- deadline 已过 → 红色警告
- 输出格式：`📅 {mission_title} - {deadline} ({status})`

### 3. 检查 Blocked 状态
扫描所有 status=blocked 的 Mission：
- 自动上报 Jeff
- 输出格式：`🚫 {mission_title} - 被 {blocked_by} 阻塞`

### 4. 生成每日摘要
```
📊 FounderOS Daily Check
日期：YYYY-MM-DD

Active: N 个任务正在推进
Waiting: N 个任务等待外部
Blocked: N 个任务被阻塞
Done (本周): N 个任务完成

⚠️ 需要关注：
- {列出需要Jeff判断的事项}

📅 近期节点：
- {列出3天内的deadline}
```

## 输出要求

- 简洁，不超过 20 行
- 只输出异常和需要关注的内容
- 一切正常时只输出摘要数据
- 不输出已完成的任务详情

## 显式排除

- 不做决策建议（只报告状态）
- 不修改任何文件（只读检查）
- 不分析 Signal（那是另一个 prompt）
