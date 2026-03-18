# PRD: FPMS 记忆层 v2

**状态**: Draft  
**日期**: 2026-03-18  
**基于**: FounderOS Memory Architecture V1 + Knowledge System v1  
**Scope**: 单用户 + 单 Agent，架构预留企业级扩展

---

## 1. 定位

FPMS 当前是项目管理引擎（骨架）。本 PRD 补上记忆系统（大脑）。

```
FPMS 完整体
├── 项目管理层（已有）— 管"要做什么"
│   ├── DAG 节点、状态机、叙事、风险、焦点、Bundle
│   └── CTO Agent 执行引擎
└── 记忆层（本 PRD）— 管"知道什么"
    ├── 事实记忆 — 发生了什么
    ├── 判断记忆 — 我们怎么看
    ├── 临时上下文 — 现在这轮对话的
    └── 程序性记忆 — 怎么做（模式/教训）
```

---

## 2. 记忆模型

### 2.1 四层记忆（从原始六层裁剪）

原始 Memory Architecture V1 有六层。单用户场景裁剪为四层：

| 层 | 原始对应 | 存什么 | 示例 | 可写者 |
|---|---|---|---|---|
| **Constitution** | Layer 1 | 不变的规则和原则 | SOUL.md 铁律、CDRE 方法论 | 仅人类确认 |
| **Fact** | Layer 2 | 客观事实，可验证 | "公司在新加坡"、"node ID 用 6 位 hex" | auto + 人类 |
| **Judgment** | Layer 3 | 对事实的判断/偏好/教训 | "Linear 比 GitHub Issues 好"、"subagent 必须 commit" | auto + 人类 |
| **Scratch** | Layer 6 | 临时上下文，默认不入库 | "Jeff 在飞行中"、"今天在讨论记忆架构" | auto，确认后沉淀 |

**裁剪掉的：**
- Layer 4 (Office Memory) — 单用户无 Office 分域需求
- Layer 5 (Narrative Memory) — 单用户无内外口径分离需求

**预留**：schema 设计 layer 字段用 enum，未来加回 Layer 4/5 零改动。

### 2.2 核心原则（继承原始六条）

1. **事实优先** — 长期记忆底座是客观事实
2. **事实与判断分离** — "发生了什么" ≠ "我们怎么看"
3. **临时上下文默认不入库** — 先缓存，确认后沉淀到 Fact/Judgment
4. **所有关键记忆可追溯** — 谁写的、什么时候、基于什么
5. **层间单向依赖** — Constitution 约束所有层，Judgment 必须引用 Fact，不可反向
6. **Append-first** — 自动流程只追加，不覆盖旧记忆

### 2.3 记忆字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 系统 | `mem-{6hex}` |
| `layer` | enum | ✅ | `constitution` / `fact` / `judgment` / `scratch` |
| `content` | string | ✅ | 记忆内容（≤200 字） |
| `tags` | string[] | ❌ | 检索标签 |
| `node_id` | string | ❌ | 关联 FPMS 节点 |
| `based_on` | string[] | ❌ | judgment 引用的 fact ID 列表 |
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
| Constitution 不可 auto 写入 | 只能人类通过 `add_memory` 手动创建 |
| Judgment 必须有 `based_on` | 引用至少一条 Fact 的 ID |
| Scratch 默认 P2 | 30 天后自动归档 |
| Scratch → Fact/Judgment | 人类确认后升层（调用 `promote_memory`） |
| Fact 不引用 Judgment | 事实不依赖判断 |

---

## 3. 事实源架构

```
memory_events (append-only) ← Source of Truth
        ↓ projection
memories 表 ← 物化视图，可重建
```

memory_events 记录：`memory_created` / `memory_updated` / `memory_archived` / `memory_accessed` / `memory_promoted`（scratch 升层）

---

## 4. 功能需求

### FR-1: 自动记忆提取

**触发时机**：Heartbeat 周期 或 session compaction 时

**提取方式**：借用当前对话 LLM，追加提取 prompt

**提取规则**：
- 用户明确陈述的事实 → `fact`，confidence 0.8+
- 用户明确做出的决策/偏好/教训 → `judgment`，必须关联 fact
- 临时状态 → `scratch`，P2
- 推断/猜测/含"可能/也许" → **不入库**
- 未确认的关系/隐私信息 → **不入库**

**所有 auto 提取的记忆 verification = `auto_extracted`**

### FR-2: 手动记忆管理

| Tool | 功能 | 约束 |
|------|------|------|
| `add_memory` | 手动添加 | constitution 层只能通过此 Tool |
| `search_memories` | 检索 | 支持 layer/tags/node_id/keyword/priority，分页 |
| `update_memory` | 修改 | auto_extracted 记忆必须先 promote/confirm |
| `forget` | 归档 | 产生审计事件，不物理删除 |
| `promote_memory` | scratch 升层到 fact/judgment | 需指定目标层 |

### FR-3: 记忆检索

**确定性检索**（无向量搜索）：
- 按 layer / tags / node_id / keyword / priority / verification
- 分页：limit + offset

**排序**（可信度优先）：
1. layer 权重（constitution > fact > judgment > scratch）
2. verification（user_confirmed > auto_extracted）
3. confidence 降序
4. conflict_count 升序
5. last_accessed_at 降序

### FR-4: 记忆注入认知包

扩展 Context Bundle，在 L_Alert 和 L1 之间新增 L_Memory：

**常驻层（Bootstrap 必注入）— ≤ 150 tokens，≤ 3 条**：
- constitution 层全部（通常很少）
- fact + user_confirmed + P0 + 高 access_count

**按需层（焦点切换时）— ≤ 350 tokens，≤ 5 条**：
- 焦点 node_id 关联的 fact/judgment
- 当前对话 tags 匹配的记忆
- 仅 confidence > 0.7

**不注入**：
- scratch 层（临时的，不污染认知包）
- auto_extracted + conflict_count > 0
- archived

**L_Memory 总预算 ≤ 500 tokens**

### FR-5: 衰减

| 条件 | 动作 |
|------|------|
| P2 + 30 天 + access_count < 3 | 归档 |
| P1 + 90 天 + access_count < 5 | 归档 |
| P0 | 永不自动归档 |
| scratch + 未 promote + 7 天 | 归档 |
| conflict_count > 3 | 归档 |

### FR-6: MEMORY.md 迁移

一次性迁移：
1. LLM 解析 MEMORY.md 内容
2. 按四层分类 + 打标签
3. 导入 memories 表，source = `system`，verification = `auto_extracted`
4. MEMORY.md 标记为 legacy

---

## 5. 非目标（v2 Phase 0 不做）

| 非目标 | 何时做 |
|--------|--------|
| 信号检测引擎 | Phase 1 |
| 关系图谱 | Phase 1 |
| 概念蒸馏 | Phase 1 |
| 邮件采集 | Phase 1 |
| 向量语义检索 | Phase 2 |
| 多 Agent 共享记忆 | Phase 2 |
| Office 分域 / Narrative 层 | Phase 2+ |

---

## 6. 验收清单

- [ ] 四层记忆模型可用（constitution / fact / judgment / scratch）
- [ ] auto 提取推断类内容 → 拦截
- [ ] judgment 必须有 based_on → 无则拒绝
- [ ] scratch 7 天未 promote → 自动归档
- [ ] constitution 只能手动创建
- [ ] promote_memory 可将 scratch 升层
- [ ] L_Memory 注入认知包 ≤ 500 tokens
- [ ] scratch 层不进认知包
- [ ] memories 可从 memory_events 重建
- [ ] MEMORY.md 迁移成功
- [ ] 所有操作产生审计事件
