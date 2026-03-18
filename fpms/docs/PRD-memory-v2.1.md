# PRD: FPMS 记忆层 v2.1

**状态**: Draft  
**日期**: 2026-03-18  
**基于**: FounderOS Memory Architecture V1 + Knowledge System v1  
**Scope**: 单用户 + 单 Agent，架构预留企业级扩展  
**变更**: v2.0 → v2.1，修复 5 个架构问题

---

## 1. 定位

FPMS 是最小可迭代结构的一部分：

```
记忆（知道什么）→ FPMS（决定做什么）→ CTO Agent（去做）→ 记忆（记住结果）
```

本 PRD 补上记忆这条缺失的边，让循环闭合。

**职责边界**：
- **FPMS**：提供记忆存储 + 检索 + 衰减 + 注入 API
- **Agent**（调用者）：负责提取触发、对话中动态检索、写入调用
- FPMS 不控制对话流程，不决定"什么时候提取"

---

## 2. 记忆模型

### 2.1 三层记忆

| 层 | 存什么 | 示例 | 可写者 |
|---|---|---|---|
| **Fact** | 客观事实，可验证 | "公司在新加坡"、"node ID 用 6 位 hex" | auto + 人类 |
| **Judgment** | 对事实的判断/偏好/决策/教训/模式 | "Linear 比 GitHub Issues 好"、"subagent 必须 commit" | auto + 人类 |
| **Scratch** | 临时上下文，默认不入库 | "Jeff 在飞行中"、"今天在讨论记忆架构" | auto，确认后沉淀 |

**为什么没有 Constitution 层**：SOUL.md / AGENTS.md 本身就是 constitution，每次 session 必读。再入库是重复存储，还要维护一致性。

**Judgment sub-type**（可选标注，不影响层级）：

| sub_type | 说明 | 示例 |
|----------|------|------|
| `preference` | 偏好/习惯 | "不喜欢冗长回复" |
| `decision` | 明确选择 | "选 6 位 hex 做 node ID" |
| `lesson` | 踩坑教训 | "subagent 必须 commit" |
| `pattern` | 经验模式 | "日本合作伙伴重视正式流程" |

**预留**：layer 字段用 enum，未来加 `office` / `narrative` 零改动。

### 2.2 核心原则

1. **事实优先** — 长期记忆底座是客观事实
2. **事实与判断分离** — "发生了什么" ≠ "我们怎么看"
3. **临时上下文默认不入库** — scratch 先缓存，确认后沉淀
4. **所有记忆可追溯** — 谁写的、什么时候、基于什么
5. **Append-first** — 自动流程只追加，不覆盖旧记忆
6. **FPMS 只管存取，Agent 管触发** — 职责清晰

### 2.3 记忆字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 系统 | `mem-{6hex}` |
| `layer` | enum | ✅ | `fact` / `judgment` / `scratch` |
| `sub_type` | enum | ❌ | judgment 专用：`preference` / `decision` / `lesson` / `pattern` |
| `content` | string | ✅ | 记忆内容（≤200 字） |
| `tags` | string[] | ❌ | 检索标签 |
| `node_id` | string | ❌ | 关联 FPMS 节点 |
| `based_on` | string[] | ❌ | judgment 引用的 fact（ID 或文字描述均可） |
| `confidence` | float | ✅ | 0.0-1.0 |
| `verification` | enum | ✅ | `user_confirmed` / `auto_extracted` |
| `source` | enum | ✅ | `auto` / `manual` / `system` |
| `priority` | enum | ✅ | `P0`（永久）/ `P1`（90天）/ `P2`（30天） |
| `created_at` | datetime | 系统 | |
| `last_accessed_at` | datetime | 系统 | |
| `access_count` | int | 系统 | |
| `conflict_count` | int | 系统 | |
| `similar_to` | string | ❌ | 疑似重复记忆 ID |
| `archived_at` | datetime | ❌ | |

### 2.4 层间规则

| 规则 | 说明 |
|------|------|
| Fact 不引用 Judgment | 事实不依赖判断 |
| Judgment 的 `based_on` 建议填写 | 手动创建建议引用 fact ID；auto 提取允许填文字描述或留空 |
| Scratch 默认 P2 | 7 天未 promote 自动归档 |
| Scratch → Fact/Judgment | 人类确认后升层（`promote_memory`） |

---

## 3. 事实源架构

```
memory_events (append-only) ← Source of Truth
        ↓ projection
memories 表 ← 物化视图，可重建
```

| 事件类型 | 说明 |
|----------|------|
| `memory_created` | 新记忆写入 |
| `memory_updated` | 字段修改（记录 old/new） |
| `memory_archived` | 归档 |
| `memory_accessed` | 被召回 |
| `memory_promoted` | scratch 升层 |

---

## 4. 功能需求

### FR-1: 记忆写入 API

FPMS 提供写入接口，**不负责触发提取**。

| Tool | 功能 | 约束 |
|------|------|------|
| `add_memory` | 写入一条记忆 | 校验 layer/字段/禁止清单 |
| `add_memories` | 批量写入 | 同上，批量版 |

**写入禁止清单（FPMS 侧校验）**：
- `content` 为空或超 200 字 → 拒绝
- `layer=fact` + `confidence < 0.5` → 拒绝
- `source=auto` + `content` 含"可能/也许/大概/推测/应该" → 拒绝（防 Agent 推断入库）

**写入流程**：
1. 校验字段 + 禁止清单
2. 相似检查 → 命中时标记 `similar_to`（不覆盖）
3. 写入 memory_events
4. 投影到 memories 表

### FR-2: 记忆管理 API

| Tool | 功能 | 约束 |
|------|------|------|
| `search_memories` | 检索 | layer/tags/node_id/keyword/sub_type/priority/verification，分页（limit+offset） |
| `update_memory` | 修改 | auto_extracted 记忆必须先 promote/confirm 才能改 |
| `forget` | 归档 | 产生审计事件，不物理删除 |
| `promote_memory` | scratch 升层 | 指定目标层 + 可选改 priority |
| `confirm_memory` | auto → user_confirmed | 升级验证状态 |

### FR-3: 记忆检索排序

**确定性检索**（无向量搜索）。

**排序规则**（可信度优先）：
1. layer 权重（fact > judgment > scratch）
2. verification（user_confirmed > auto_extracted）
3. confidence 降序
4. conflict_count 升序（冲突少的更可信）
5. last_accessed_at 降序

**负反馈**：
- 用户纠正记忆 → 旧记忆 conflict_count +1
- `forget` 后 → similar_to 链上的记忆 conflict_count +1

### FR-4: 记忆注入认知包

扩展 Context Bundle，在 L_Alert 和 L1 之间新增 L_Memory。

**常驻层（bootstrap 注入）— ≤ 200 tokens，≤ 5 条**：
- `fact` + `user_confirmed` + `P0`，按 access_count 降序取 Top 3
- `judgment` + `user_confirmed` + `P0` + `sub_type=preference`，按 access_count 降序取 Top 2

**按需层（Agent 对话中主动调用 `search_memories`）**：
- FPMS 不主动注入，Agent 按需检索
- 避免在 bootstrap 时猜"这轮对话会聊什么"

**不注入**：
- scratch 层
- auto_extracted + conflict_count > 0
- archived

**L_Memory 常驻层预算 ≤ 200 tokens**

### FR-5: 衰减

| 条件 | 动作 |
|------|------|
| P2 + 30 天 + access_count < 3 | 归档 |
| P1 + 90 天 + access_count < 5 | 归档 |
| P0 | 永不自动归档 |
| scratch + 未 promote + 7 天 | 归档 |
| conflict_count > 3 | 归档 |

**衰减只看 priority，不看 layer。** 唯一规则源：本表。

### FR-6: MEMORY.md 迁移

一次性迁移：
1. Agent 用 LLM 解析 MEMORY.md
2. 按三层分类 + 打标签
3. 调用 `add_memories` 批量写入，source = `system`，verification = `auto_extracted`
4. MEMORY.md 标记为 legacy

---

## 5. Agent 侧职责（不在 FPMS 代码内，在 AGENTS.md / HEARTBEAT.md 定义）

| 职责 | 触发时机 | 说明 |
|------|---------|------|
| 自动提取 | Heartbeat / compaction / Agent 自觉 | Agent 从对话中提取记忆，调用 `add_memory` |
| 按需检索 | 对话中提到相关话题时 | Agent 调用 `search_memories` 召回相关记忆 |
| 确认/升层 | Jeff 说"记住这个" | Agent 调用 `confirm_memory` / `promote_memory` |
| 纠正 | Jeff 说"这不对" | Agent 调用 `forget` + `add_memory` 写新版本 |

**提取 prompt 模板**（Agent 使用，非 FPMS 代码）：
```
从本次对话中提取值得长期记忆的信息，按 JSON 输出：
[{layer, sub_type?, content, tags, node_id?, based_on?, confidence, priority}]

规则：
- 用户明确陈述的事实 → layer=fact
- 用户明确的决策/偏好/教训 → layer=judgment + 对应 sub_type
- 临时状态 → layer=scratch
- 推断/猜测 → 不提取
- 未确认的关系/隐私 → 不提取
```

---

## 6. 协议一致性

| 定义 | 唯一来源 |
|------|---------|
| Layer 枚举 | 本 PRD §2.1 |
| Sub-type 枚举 | 本 PRD §2.1 |
| 衰减规则 | 本 PRD §FR-5 |
| 写入禁止清单 | 本 PRD §FR-1 |
| 注入策略 | 本 PRD §FR-4 |
| 事实源架构 | 本 PRD §3 |
| Agent 提取 prompt | 本 PRD §5（Agent 侧可迭代，但须兼容 FPMS schema） |

---

## 7. 非目标（Phase 0 不做）

| 非目标 | 何时做 |
|--------|--------|
| 信号检测引擎 | Phase 1 |
| 关系图谱 | Phase 1 |
| 概念蒸馏 | Phase 1 |
| 邮件采集 | Phase 1 |
| 向量语义检索 | Phase 2 |
| 多 Agent 共享记忆 | Phase 2 |
| Office / Narrative 层 | Phase 2+ |

---

## 8. 实现估算

| 模块 | 预估 | 说明 |
|------|------|------|
| Schema（memories + memory_events） | ~120 行 | 两张表 + 索引 |
| Memory Store（CRUD + 事件流 + 投影） | ~350 行 | add/search/update/forget/promote/confirm + 衰减 |
| Bundle 集成（L_Memory 常驻层） | ~80 行 | bootstrap 时查询注入 |
| MCP Tools（6 个 Tool） | ~150 行 | add/search/update/forget/promote/confirm |
| Tests | ~400 行 | |
| **总计** | **~1100 行** | |

---

## 9. 验收清单

- [ ] 三层记忆可用（fact / judgment / scratch）
- [ ] judgment sub_type 可选标注
- [ ] auto source + 含"可能/也许" → 拦截
- [ ] fact + confidence < 0.5 → 拦截
- [ ] scratch 7 天未 promote → 自动归档
- [ ] promote_memory 可将 scratch 升层
- [ ] confirm_memory 可将 auto → user_confirmed
- [ ] L_Memory 常驻层注入 bootstrap，≤ 200 tokens
- [ ] scratch 不进认知包
- [ ] memories 可从 memory_events 重建
- [ ] search_memories 支持分页 + 多维筛选
- [ ] 所有操作产生 memory_events 审计事件

---

## 10. v2.0 → v2.1 变更摘要

| # | 问题 | 修复 |
|---|------|------|
| 1 | Judgment based_on 强制要 fact ID，auto 提取时不可行 | based_on 允许文字描述或留空 |
| 2 | Constitution 层和 SOUL.md 重复 | 去掉，三层模型 |
| 3 | 程序性记忆无对应 | judgment 加 sub_type（preference/decision/lesson/pattern） |
| 4 | 提取触发者不明 | 明确 FPMS 只管存取，Agent 管触发（§5） |
| 5 | 按需层在 bootstrap 时不可行 | bootstrap 只注入常驻层，按需层由 Agent 主动调用 search |
