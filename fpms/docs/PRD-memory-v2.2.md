# PRD: FPMS 记忆层 v2.2

**状态**: Approved  
**日期**: 2026-03-18  
**基于**: FounderOS Memory Architecture V1 + Knowledge System v1  
**Scope**: 单用户 + 单 Agent，架构预留企业级扩展  
**变更**: v2.1 → v2.2，补 5 项协议硬化

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
| **Judgment** | 对事实的判断/偏好/决策/教训/模式 | "Linear 比 GitHub Issues 好"、"日本伙伴重视正式流程" | auto + 人类 |
| **Scratch** | 临时上下文，默认不入库 | "Jeff 在飞行中"、"今天在讨论记忆架构" | auto，确认后沉淀 |

**Judgment sub-type**（可选标注）：

| sub_type | 说明 | 示例 |
|----------|------|------|
| `preference` | 偏好/习惯 | "不喜欢冗长回复" |
| `decision` | 明确选择 | "选 6 位 hex 做 node ID" |
| `lesson` | 踩坑教训 | "subagent 必须 commit" |
| `pattern` | 经验模式 | "日本合作伙伴重视正式流程" |

**Judgment 不得承载全局强制协议**：跨节点、违反即报错的硬规则属于 SOUL.md / AGENTS.md / SUBAGENT-PROTOCOL，不入 judgment。

**预留**：layer 字段用 enum，未来加 `office` / `narrative` 零改动。

### 2.2 Layer 判定表（准入规则）

**判定顺序：从上到下匹配第一个命中的。**

| 条件 | → Layer | 说明 |
|------|---------|------|
| 依赖当前时段/当前任务/当前状态 | Scratch | 含"今天/这轮/当前/正在"默认 Scratch |
| 含"更好/更适合/通常/倾向于/应该" | Judgment | 带比较级/倾向性 = 判断 |
| 有明确"选 A 不选 B"结构 | Judgment.decision | |
| 有错误 + 修正动作 | Judgment.lesson | |
| 表达偏好/喜好/习惯 | Judgment.preference | |
| 多次观察总结的经验 | Judgment.pattern | |
| 可外部验证、时效 > 30 天、与观点无关 | Fact | 纯客观陈述 |
| 用户说"记住这个"但不确定分类 | Scratch | 保守先缓存，后续 promote |

**Fact 准入硬规则**：
- 必须是可验证陈述
- 不得含比较级、倾向性、解释性结论
- confidence ≥ 0.5

**唯一来源**：本表。Schema、提取 prompt、Agent 逻辑必须引用此表。

### 2.3 核心原则

1. **事实优先** — 长期记忆底座是客观事实
2. **事实与判断分离** — "发生了什么" ≠ "我们怎么看"
3. **临时上下文默认不入库** — scratch 先缓存，确认后沉淀
4. **所有记忆可追溯** — 谁写的、什么时候、基于什么
5. **Append-first** — 自动流程只追加，不覆盖旧记忆
6. **FPMS 只管存取，Agent 管触发** — 职责清晰

### 2.4 记忆字段

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
| `verification` | enum | ✅ | `user_confirmed` / `system_verified` / `auto_extracted` |
| `source` | enum | ✅ | `auto` / `manual` / `system` |
| `priority` | enum | ✅ | `P0`（永久）/ `P1`（90天）/ `P2`（30天） |
| `needs_review` | bool | 系统 | 默认 false，冲突多时标记 true |
| `created_at` | datetime | 系统 | |
| `last_accessed_at` | datetime | 系统 | |
| `access_count` | int | 系统 | |
| `conflict_count` | int | 系统 | |
| `similar_to` | string | ❌ | 疑似重复记忆 ID（Phase 0 单值，后续扩展为多对多） |
| `archived_at` | datetime | ❌ | |

### 2.5 source × verification 合法组合表

| source | 初始 verification | 说明 |
|--------|-------------------|------|
| `auto` | `auto_extracted` | 自动提取，未确认 |
| `manual` | `user_confirmed` | 人类手动创建，天然已确认 |
| `system` | `system_verified` | 系统事件产生（task 完成等） |

**状态转移**：
- `auto_extracted` → `user_confirmed`（通过 `confirm_memory`）
- `auto_extracted` → `system_verified`（通过系统事件交叉验证）
- 其他方向 **禁止**（user_confirmed 不可降级）

### 2.6 层间规则

| 规则 | 说明 |
|------|------|
| Fact 不引用 Judgment | 事实不依赖判断 |
| Judgment 的 `based_on` 建议填写 | 手动创建建议引用 fact ID；auto 允许文字描述或留空 |
| Scratch 默认 P2 | 7 天未 promote 自动归档 |
| Scratch → Fact/Judgment | 通过 `promote_memory`，**必须重新校验目标层准入规则** |
| Fact 不引用 Judgment | 事实不依赖判断 |

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
| `memory_confirmed` | verification 升级 |

---

## 4. 状态转移表

### 4.1 记忆生命周期

```
                 add_memory
                     │
                     ▼
              ┌─── active ───┐
              │              │
         confirm_memory   promote_memory
         (verification↑)  (scratch→fact/judgment)
              │              │
              ▼              ▼
           active          active（新层，重新校验准入）
              │
         forget / 衰减
              │
              ▼
           archived
```

### 4.2 操作权限矩阵

| 操作 | active | archived | 约束 |
|------|--------|----------|------|
| `confirm_memory` | ✅ | ❌ | 仅 auto_extracted 可 confirm |
| `promote_memory` | ✅ | ❌ | 仅 scratch 可 promote；目标层须过准入校验 |
| `update_memory` | ✅ | ❌ | auto_extracted 须先 confirm 才能 update |
| `forget` | ✅ | ❌ | 产生审计事件 |
| `search_memories` | ✅ | 可选 | 默认不含 archived，可指定 include_archived |

### 4.3 字段可变性

| 字段 | 可通过 update 修改 | 说明 |
|------|-------------------|------|
| content | ✅ | 须 user_confirmed |
| tags | ✅ | |
| node_id | ✅ | |
| based_on | ✅ | |
| priority | ✅ | |
| sub_type | ✅ | |
| layer | ❌ | 只能通过 promote_memory |
| verification | ❌ | 只能通过 confirm_memory |
| source | ❌ | 不可变 |
| id / created_at | ❌ | 不可变 |

---

## 5. 功能需求

### FR-1: 记忆写入 API

| Tool | 功能 | 约束 |
|------|------|------|
| `add_memory` | 写入一条记忆 | 校验 layer 准入 + 字段 + 禁止清单 + source×verification 合法组合 |
| `add_memories` | 批量写入 | 同上，批量版 |

**写入禁止清单（FPMS 侧校验，第一层防线）**：
- `content` 为空或超 200 字 → 拒绝
- `layer=fact` + `confidence < 0.5` → 拒绝
- `source=auto` + `content` 含"可能/也许/大概/推测/应该/似乎/看起来/大概率" → 拒绝
- `source=auto` + `layer=fact` + content 含比较级/倾向性词 → 拒绝

**第二层防线（结构性准入）**：
- Fact 必须是可验证陈述，不得含解释性结论
- source=auto 的 judgment，content 须能对应"用户本轮明确陈述过"（由 Agent 保证，FPMS 不校验自然语言语义）

**写入流程**：
1. 校验字段 + 合法组合 + 禁止清单 + layer 准入
2. 相似检查 → 命中时标记 `similar_to`（不覆盖）
3. 写入 memory_events
4. 投影到 memories 表

### FR-2: 记忆管理 API

| Tool | 功能 | 约束 |
|------|------|------|
| `search_memories` | 检索 | layer/tags/node_id/keyword/sub_type/priority/verification/needs_review，分页 |
| `update_memory` | 修改 | auto_extracted 须先 confirm；字段可变性见 §4.3 |
| `forget` | 归档 | 产生审计事件，不物理删除 |
| `promote_memory` | scratch 升层 | 指定目标层 + 重新校验准入规则 + 可选重设 confidence/priority |
| `confirm_memory` | auto → user_confirmed | 仅 auto_extracted 可操作 |

### FR-3: 记忆检索排序

**确定性检索**（无向量搜索）。

**排序规则**（可信度优先）：
1. layer 权重（fact > judgment > scratch）
2. verification（user_confirmed > system_verified > auto_extracted）
3. confidence 降序
4. conflict_count 升序
5. last_accessed_at 降序

**负反馈**：
- 用户纠正记忆 → 旧记忆 conflict_count +1
- `forget` 后 → similar_to 链上的记忆 conflict_count +1
- conflict_count > 3 → `needs_review = true`，从常驻注入排除，检索降权

### FR-4: 记忆注入认知包

扩展 Context Bundle，在 L_Alert 和 L1 之间新增 L_Memory。

**常驻层（bootstrap 注入）— ≤ 200 tokens，≤ 5 条**：
- `fact` + `user_confirmed` + `P0`，按 access_count 降序取 Top 3
- `judgment` + `user_confirmed` + `P0` + `sub_type=preference`，取 Top 2
- 排除 `needs_review = true`

**按需层**：Agent 对话中主动调用 `search_memories`。FPMS 不主动注入。

**不注入**：
- scratch 层
- needs_review = true
- archived

**L_Memory 常驻层预算 ≤ 200 tokens**

### FR-5: 衰减

| 条件 | 动作 |
|------|------|
| P2 + 30 天 + access_count < 3 | 归档 |
| P1 + 90 天 + access_count < 5 | 归档 |
| P0 | 永不自动归档 |
| scratch + 未 promote + 7 天 | 归档 |
| conflict_count > 3 | 标记 needs_review（不自动归档） |

**衰减只看 priority，不看 layer。** 唯一规则源：本表。

### FR-6: MEMORY.md 迁移

一次性迁移：
1. Agent 用 LLM 解析 MEMORY.md
2. 按三层分类 + 打标签
3. 迁移范围：fact + judgment（preference/decision）优先；lesson/pattern/scratch 保守处理
4. 调用 `add_memories` 批量写入，source = `system`，verification = `auto_extracted`
5. 迁移记忆默认不进常驻层（需后续 confirm 或高频 access 才进）
6. MEMORY.md 标记为 legacy

---

## 6. Agent 侧职责（AGENTS.md / HEARTBEAT.md 定义，非 FPMS 代码）

| 职责 | 触发时机 | 说明 |
|------|---------|------|
| 自动提取 | Heartbeat / compaction / Agent 自觉 | Agent 从对话中提取记忆，调用 `add_memory` |
| 按需检索 | 对话中提到相关话题时 | Agent 调用 `search_memories` 召回记忆 |
| 确认/升层 | Jeff 说"记住这个" | **优先直接写目标层**（不先写 scratch）；scratch promote 用于系统先缓存后确认 |
| 纠正 | Jeff 说"这不对" | Agent 调用 `forget` + `add_memory` 写新版本 |

**提取 prompt 模板**：
```
从本次对话中提取值得长期记忆的信息，按 JSON 输出：
[{layer, sub_type?, content, tags, node_id?, based_on?, confidence, priority}]

判定规则（严格按此顺序）：
1. 依赖当前时段/任务/状态 → scratch
2. 含比较/倾向/选择/教训/模式 → judgment + 对应 sub_type
3. 可验证的客观事实 → fact
4. 推断/猜测/不确定 → 不提取

禁止提取：
- 含"可能/也许/大概/推测"的内容
- 未确认的关系或隐私信息
- 模型自己的归纳总结
```

**提取 prompt 迭代约束**：措辞可优化，但不得改变 layer 判定规则、禁止清单、priority 语义。

---

## 7. 协议一致性

| 定义 | 唯一来源 |
|------|---------|
| Layer 枚举 + 判定表 | 本 PRD §2.1 + §2.2 |
| Sub-type 枚举 | 本 PRD §2.1 |
| source × verification 合法组合 | 本 PRD §2.5 |
| 状态转移 + 操作权限 | 本 PRD §4 |
| 衰减规则 | 本 PRD §FR-5 |
| 写入禁止清单 | 本 PRD §FR-1 |
| 注入策略 | 本 PRD §FR-4 |
| 事实源架构 | 本 PRD §3 |

---

## 8. 非目标（Phase 0 不做）

| 非目标 | 何时做 |
|--------|--------|
| 信号检测引擎 | Phase 1 |
| 关系图谱 | Phase 1 |
| 概念蒸馏 | Phase 1 |
| 邮件采集 | Phase 1 |
| similar_to 多对多 | Phase 1 |
| 向量语义检索 | Phase 2 |
| 多 Agent 共享记忆 | Phase 2 |
| Office / Narrative 层 | Phase 2+ |

---

## 9. 实现估算

| 模块 | 预估 | 说明 |
|------|------|------|
| Schema（memories + memory_events） | ~130 行 | 两张表 + 索引 |
| Memory Store（CRUD + 事件流 + 投影 + 衰减） | ~400 行 | 含状态转移校验 |
| Bundle 集成（L_Memory 常驻层） | ~80 行 | bootstrap 查询注入 |
| MCP Tools（7 个 Tool） | ~180 行 | add/batch-add/search/update/forget/promote/confirm |
| Tests | ~450 行 | 覆盖验收清单全部项 |
| **总计** | **~1240 行** | |

---

## 10. 验收清单

### 模型与准入
- [ ] 三层记忆可用（fact / judgment / scratch）
- [ ] judgment sub_type 可选标注
- [ ] Layer 判定表校验生效（fact 不接受比较级/倾向性内容）
- [ ] source × verification 合法组合校验
- [ ] auto source + 禁止词 → 拒绝

### 状态转移
- [ ] confirm_memory：仅 auto_extracted → user_confirmed
- [ ] promote_memory：仅 scratch 可升层，重新校验目标层准入
- [ ] update_memory：auto_extracted 须先 confirm
- [ ] forget：产生审计事件，archived 后不可 confirm/promote/update
- [ ] layer / verification / source 不可通过 update 修改

### 检索与注入
- [ ] search_memories 支持多维筛选 + 分页
- [ ] L_Memory 常驻层 ≤ 200 tokens
- [ ] scratch / needs_review / archived 不进常驻层
- [ ] conflict_count > 3 → needs_review = true

### 事实源与衰减
- [ ] 所有操作产生 memory_events 审计事件
- [ ] memories 可从 memory_events 重建
- [ ] P2 + 30天 + access_count < 3 → 归档
- [ ] scratch + 7天未 promote → 归档
- [ ] P0 永不自动归档

### 迁移
- [ ] MEMORY.md 一键迁移成功
- [ ] 迁移记忆默认不进常驻层

---

## 11. v2.1 → v2.2 变更摘要

| # | 问题 | 修复 |
|---|------|------|
| 1 | Layer 边界不够硬 | §2.2 新增 Layer 判定表（准入规则，按顺序匹配） |
| 2 | source × verification 可能出现脏状态 | §2.5 新增合法组合表 + 转移规则 |
| 3 | conflict > 3 自动归档太危险 | FR-5 改为标记 needs_review，不自动归档 |
| 4 | promote 可能绕过准入 | §2.6 + FR-2 明确 promote 必须重新校验目标层 |
| 5 | 缺状态转移表 | §4 新增完整状态转移 + 操作权限矩阵 + 字段可变性 |
| 6 | verification 只有两档 | 新增 system_verified |
| 7 | Judgment 可能变影子 Constitution | §2.1 新增约束：Judgment 不得承载全局强制协议 |
| 8 | 迁移可能灌入脏数据 | FR-6 新增范围控制 + 默认不进常驻层 |
