---
name: fpms
description: "Fractal Project Management System — 管理项目、任务、依赖关系的确定性引擎。Use when: (1) 创建/更新/查询项目或任务, (2) 用户提到项目进度/状态/下一步, (3) 心跳扫描项目风险, (4) 需要项目上下文来回答问题。NOT for: 普通闲聊、与项目管理无关的操作。"
metadata:
  { "openclaw": { "emoji": "🏗️" } }
---

# FPMS — Fractal Project Management System

## Quick Start

所有操作通过 `spine.py` CLI 执行：

```bash
cd ~/fpms  # 永远在 fpms 目录下执行
python3 spine.py <command> [args]
```

## Commands

### 1. Tool Call（写入/查询）

```bash
python3 spine.py tool <tool_name> '<json_args>'
```

返回 JSON: `{"success": true/false, "data": {...}, "error": "...", "suggestion": "..."}`

### 2. Bootstrap（冷启动上下文）

```bash
python3 spine.py bootstrap [--max-tokens 10000]
```

Session 开始时调用，获取完整认知包（L0 看板 + 告警 + 近景 + 焦点）。

### 3. Heartbeat（心跳扫描）

```bash
python3 spine.py heartbeat
```

输出 `FPMS_HEARTBEAT_OK` 或告警列表。在 HEARTBEAT.md 中定期调用。

### 4. Dashboard（全局看板）

```bash
python3 spine.py dashboard
```

### 5. Status（系统状态）

```bash
python3 spine.py status
```

## Available Tools

### 写入类（改变数据，产生审计记录）

| Tool | 功能 | 必传参数 |
|------|------|---------|
| `create_node` | 创建节点 | `title` (node_type, is_root, summary, deadline 可选) |
| `update_status` | 变更状态 | `node_id`, `new_status` (reason 可选但回退必传) |
| `update_field` | 修改字段 | `node_id`, `field`, `value` |
| `attach_node` | 挂载到父节点 | `node_id`, `parent_id` |
| `detach_node` | 脱离父节点 | `node_id` |
| `add_dependency` | 添加依赖 | `source_id`, `target_id` |
| `remove_dependency` | 移除依赖 | `source_id`, `target_id` |
| `append_log` | 追加叙事 | `node_id`, `content` |
| `unarchive` | 恢复归档 | `node_id` (new_status 可选) |
| `set_persistent` | 常驻/取消 | `node_id`, `value` (true/false) |

### 运行时类（不改数据）

| Tool | 功能 | 参数 |
|------|------|------|
| `shift_focus` | 切换焦点 | `node_id` |
| `expand_context` | 扩展上下文 | `node_id`, `mode` |

### 只读类

| Tool | 功能 | 参数 |
|------|------|------|
| `get_node` | 查询节点 | `node_id` |
| `search_nodes` | 搜索 | `status`, `parent_id`, `limit`, `offset` |

## 行为准则（铁律）

### 你是透明的。用户不需要知道 FPMS 存在。

**自动捕获**：对话中出现待办/任务/承诺 → 静默 create_node 到 inbox，不问用户"要不要记下来"。
  - "明天打电话给会计" → 直接录入
  - "下周要跟 NetStar 开会" → 直接录入
  - 纯闲聊/观点/问题 → 不录入

**自动匹配**：用户提到已有项目关键词 → 静默拉出上下文，自然融入回答。
  - 匹配规则：用户说的词命中已有节点的 title/summary/id
  - 不需要用户说"打开项目"或"查一下 FPMS"

**自动更新**：用户陈述了状态变化 → 静默更新，回复时顺带确认。
  - "法务审核搞完了" → update_status done + 回复"好的，法务审核标完成了"
  - "那个先不做了" → update_status dropped

**主动提醒**：心跳发现风险 → 主动告诉用户，不等他问。

**唯一需要问用户的场景**：
  - 新建正式项目（goal/project 级）→ 确认名称和范围
  - 歧义：无法确定指的是哪个节点
  - 删除/归档恢复等不可逆操作

### Session 启动

1. 运行 `python3 spine.py bootstrap`
2. 如果有告警 → 开场时主动告知
3. 如果有 inbox 积压 → 适时建议整理

### 心跳

运行 `python3 spine.py heartbeat`，有告警则推送给用户。

## 操作参考

### 快速捕获
```bash
python3 spine.py tool create_node '{"title":"明天打电话给会计"}'
```

### 建项目层级
```bash
python3 spine.py tool create_node '{"title":"Anext信贷","node_type":"goal","is_root":true,"summary":"700万信贷额度"}'
python3 spine.py tool create_node '{"title":"法务审核","node_type":"task","summary":"审核担保条款"}'
python3 spine.py tool attach_node '{"node_id":"task-xxxx","parent_id":"goal-xxxx"}'
python3 spine.py tool update_status '{"node_id":"goal-xxxx","new_status":"active"}'
```

## 状态机

```
inbox → active, waiting, dropped
active → waiting, done, dropped
waiting → active, done, dropped
done → active (需要 reason)
dropped → inbox (需要 reason)
```

**前置条件**:
- inbox → active: 必须有 summary + (parent 或 is_root)
- → done: 所有子节点必须是终态
- done → active: 必须传 reason
- dropped → inbox: 必须传 reason

## 风险标记（自动计算）

- 🚫 **blocked**: 有未完成的依赖
- 🚨 **at-risk**: deadline < 48h
- 💤 **stale**: 7 天没动静

## 注意事项

- **不要直接修改** fpms/db/fpms.db 或 narratives/ 文件
- 所有写操作必须通过 `spine.py tool` 命令
- 每次 Tool Call 自动幂等（相同 command_id 不重复执行）
- 错误信息包含 suggestion，告诉你下一步该调什么
