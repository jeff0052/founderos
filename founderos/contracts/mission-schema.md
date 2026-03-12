# Mission Schema

_给AI看的：任务数据的精确定义_

---

## Mission 定义

Mission 是 Decision 的执行层。每个 Mission 由 AI/团队基于 Key Results 拆解而来。

Mission 只有四个核心要素：
1. **Mission** — 做什么
2. **Owner** — 谁负责
3. **Deadline** — 什么时候完成
4. **Result** — 结果是什么

---

## Schema

```yaml
Mission:
  id: string  # format: M-{module}-NNN (e.g., M-ONTA-001)
  created_at: datetime
  updated_at: datetime
  
  # 归属（挂在战略地图上，不挂在组织结构上）
  module: enum [uniweb, onta, license, vibecash]
  kr_ref: string | null  # 关联的 Key Result ID
  
  # 核心四要素
  title: string  # max 50 chars
  owner: string  # 负责人姓名
  deadline: date | null
  result: string | null  # 完成后填写
  
  # 状态机
  status: enum [pending, active, waiting, blocked, done, cancelled]
  
  # 等待管理（球在谁那里）
  waiting_for: string | null  # 等待谁/什么
  waiting_since: date | null  # 从什么时候开始等
  
  # 阻塞管理
  blocked_by: string | null  # 被什么阻塞
  escalated: boolean  # 是否已上报Jeff
  
  # 备注
  notes: string | null
```

## 状态机定义

```
pending → active → done
              ↓
          waiting → active（对方回复后）
              ↓
          blocked → active（阻塞解除后）
                  → escalated（上报Jeff）

任何状态 → cancelled
```

### 状态说明

| 状态 | 含义 | 触发条件 |
|------|------|---------|
| pending | 等待启动 | 新建任务，尚未开始 |
| active | 正在执行 | 有人在推进 |
| waiting | 等待外部 | 球在对方手里（合作伙伴回复、文件审核等） |
| blocked | 被阻塞 | 有依赖未解决 |
| done | 已完成 | result 已填写 |
| cancelled | 已取消 | 不再需要 |

## 自动化规则

### AI 负责
- 从 KR 自动拆解为 Missions
- 追踪每个 Mission 的 waiting_for 状态
- waiting 超过 3 天自动提醒 Owner
- waiting 超过 7 天自动上报 Jeff
- blocked 状态自动上报 Jeff
- 每日生成 Mission 状态摘要

### Jeff 需要关注的
- blocked + escalated 的 Mission
- 超期 Mission（deadline 已过）
- 需要战略决策才能推进的 Mission

## 显式排除

- **不包含** 子任务分解（保持扁平，一个 Mission 一件事）
- **不包含** 优先级字段（优先级由 Decisions 层决定，不在 Mission 层管理）
- **不自动关联** Signal（人工判断信号与任务的关系）
- **不记录** 执行过程细节（只记录四要素 + 状态）
- **不跨模块** 一个 Mission 只属于一个 module
