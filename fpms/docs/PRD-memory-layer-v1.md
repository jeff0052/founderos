# PRD: FPMS 内建记忆层 v1

**状态**: Draft  
**日期**: 2026-03-18  
**作者**: Jeff + AI  

---

## 1. 背景

### 1.1 问题

AI Agent 每次 session 启动时完全失忆。当前的记忆方案是 `MEMORY.md` + `memory/*.md`，存在以下致命问题：

1. **靠自觉** — Agent 忘了写就丢了，没有系统保证
2. **扁平无结构** — 所有记忆混在一起，没有分类、没有权重
3. **无衰减** — 去年的信息和今天的权重一样
4. **无去重** — 同一件事可能被记录多次
5. **检索靠全文扫** — 内容多了 token 爆炸，或者根本找不到
6. **无关联** — 不知道哪条记忆和哪个项目/人/决策有关

### 1.2 目标

在 FPMS 内部新增记忆层，使 Agent 具备：

- **自动记忆** — 对话中的关键信息自动提取入库，不靠自觉
- **结构化存储** — 分类、标签、关联、权重，不是一坨文本
- **智能衰减** — 旧记忆自动降权，重要的永不丢
- **精准召回** — 按需注入相关记忆到认知包，高信噪比
- **零新增基础设施** — 不需要向量数据库、本地 LLM 或外部服务

### 1.3 设计原则

1. **内建不外挂** — 记忆是 FPMS 核心能力，不是第三方插件
2. **借用现有模型** — 记忆提取借用当前对话的 LLM（已付费），零新增成本
3. **确定性优先** — 检索用标签 + 时间 + 关联，不用向量搜索
4. **与项目管理互补** — 记忆层管"知道什么"，项目层管"要做什么"

---

## 2. 记忆模型

### 2.1 记忆分类

| 类型 | 说明 | 示例 | 默认 TTL |
|------|------|------|----------|
| `fact` | 客观事实 | "Jeff 的公司在新加坡" | 永久 |
| `preference` | 用户偏好 | "Jeff 不喜欢冗长的回复" | 永久 |
| `relationship` | 人际关系 | "Charles 是 Anext 的联系人" | 永久 |
| `decision` | 决策记录 | "选择 6 位 hex 作为 node ID 格式" | 永久 |
| `lesson` | 经验教训 | "subagent 必须 commit 否则 worktree 改动丢失" | 永久 |
| `context` | 临时上下文 | "Jeff 今天在飞行中，2 小时后回来" | 7 天 |
| `event` | 事件记录 | "2026-03-18 完成了 6 个 M 系列 task" | 30 天 |

### 2.2 记忆字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 系统生成 | `mem-{6hex}` |
| `category` | enum | ✅ | 2.1 中的 7 种分类 |
| `content` | string | ✅ | 记忆内容（一句话，不超过 200 字） |
| `tags` | string[] | ❌ | 检索标签（人名、项目、技术等） |
| `node_id` | string | ❌ | 关联的 FPMS 节点（项目/任务） |
| `confidence` | float | ❌ | 0.0-1.0，提取时的置信度 |
| `source` | enum | ✅ | `auto`（自动提取）/ `manual`（手动创建）/ `system`（系统生成） |
| `priority` | enum | ✅ | `P0`（永久）/ `P1`（90天）/ `P2`（30天），对齐 SOUL.md TTL 标签 |
| `created_at` | datetime | 系统生成 | 创建时间 |
| `last_accessed_at` | datetime | 系统维护 | 最近一次被召回的时间 |
| `access_count` | int | 系统维护 | 被召回次数（衡量重要性） |
| `superseded_by` | string | ❌ | 被哪条新记忆取代（去重用） |
| `archived_at` | datetime | ❌ | 归档时间（衰减后归档） |

### 2.3 与项目节点的关系

- 记忆可以通过 `node_id` 关联到 FPMS 节点
- 当焦点切换到某个项目时，关联记忆自动注入认知包
- 记忆不是节点的子对象，是独立实体——项目删了记忆还在

---

## 3. 功能需求

### FR-1: 自动记忆提取

**触发时机**：对话结束前（session compaction 或 heartbeat 时）

**提取方式**：利用当前对话 LLM，在对话末尾追加一个提取指令：

```
请从本次对话中提取值得长期记忆的信息，按以下 JSON 格式输出：
[{category, content, tags, node_id?, priority}]

提取规则：
- fact: 用户提到的客观事实（公司、地点、身份等）
- preference: 用户表达的偏好或习惯
- relationship: 提到的人际关系
- decision: 做出的决策和选择
- lesson: 踩坑和经验教训
- context: 临时但近期重要的信息
- event: 值得记录的事件

不要提取：
- 闲聊、问候
- 已经存在的记忆（重复的）
- 过于琐碎的信息
```

**写入流程**：
1. LLM 返回 JSON 数组
2. 脊髓引擎校验格式和字段
3. 去重检查（content 相似度 > 90% 的标记为 superseded）
4. 写入 SQLite memories 表
5. 生成审计事件

### FR-2: 手动记忆管理

通过 Tool Call 手动管理记忆：

| Tool | 功能 |
|------|------|
| `add_memory` | 手动添加一条记忆 |
| `search_memories` | 按 category/tags/node_id/关键词 检索 |
| `update_memory` | 修改记忆内容或元数据 |
| `forget` | 归档一条记忆（不删除，标记 archived_at） |

### FR-3: 记忆召回（检索）

**确定性检索**（不依赖向量搜索）：

| 检索维度 | 说明 |
|----------|------|
| `category` | 按记忆类型筛选 |
| `tags` | 标签交集匹配 |
| `node_id` | 关联节点 |
| `keyword` | content 全文 LIKE 搜索 |
| `time_range` | 时间窗口 |
| `priority` | P0/P1/P2 |

**排序规则**（默认）：
1. priority 降序（P0 > P1 > P2）
2. access_count 降序（被召回越多越重要）
3. last_accessed_at 降序（最近用过的更相关）

### FR-4: 记忆注入认知包

**扩展 Context Bundle（FR-10）**：

在现有 L0 → L_Alert → L1 → L2 之间，新增 **L_Memory 记忆区**：

```
L0 全局看板
L_Alert 系统告警
L_Memory 相关记忆（新增）
L1 近景关联
L2 焦点区
```

**L_Memory 装载规则**：
- 焦点节点有 `node_id` 关联的记忆 → 自动注入
- 当前对话提到的 tags 匹配的记忆 → 自动注入
- P0 记忆中最近 accessed 的 Top 5 → 常驻注入（核心偏好/事实）
- **预算**：≤ 500 tokens

### FR-5: 记忆衰减与维护

**自动衰减**（Heartbeat 或 Cron 触发）：

| 条件 | 动作 |
|------|------|
| P2 + created_at > 30 天 + access_count < 3 | 归档 |
| P1 + created_at > 90 天 + access_count < 5 | 归档 |
| P0 | 永不自动归档 |
| superseded_by 不为空 + 超过 7 天 | 归档旧版本 |

**去重**：
- 新记忆写入时，检查同 category 下 content 相似的已有记忆
- 相似度判断用简单规则：关键词重叠率 > 80%
- 命中时：更新已有记忆的 content + 标记旧版本 superseded_by

### FR-6: 记忆迁移

**从 MEMORY.md 冷启动**：
- 提供一次性迁移工具，解析现有 MEMORY.md
- 按内容自动分类 + 打标签
- 导入到 memories 表
- 迁移后 MEMORY.md 标记为 legacy，不再使用

---

## 4. 非功能需求

| NFR | 要求 |
|-----|------|
| **存储** | 复用 FPMS 的 SQLite，新增 memories 表 |
| **成本** | 零新增模型费用（借用对话 LLM） |
| **性能** | 记忆检索 < 50ms（SQLite 索引查询） |
| **容量** | 支持 10,000+ 条记忆（SQLite 轻松承载） |
| **隐私** | 全本地，不外传 |
| **可恢复** | memories 表是事实源，可从审计日志重建 |

---

## 5. 非目标（v1 不做）

| 非目标 | 原因 |
|--------|------|
| 向量语义检索 | 确定性检索够用，不引入额外依赖 |
| 跨用户记忆 | 单用户场景 |
| 记忆推理 | 不做"基于记忆 A 和 B 推导出 C"，留给 LLM |
| 记忆可视化 UI | v1 通过 Tool Call 查询 |
| 自动关联发现 | 不自动推断记忆之间的关系 |

---

## 6. 实现估算

| 模块 | 预估 | 等级 |
|------|------|------|
| Schema（memories 表） | ~100 行 | L1 |
| Memory Store（CRUD + 检索 + 衰减） | ~300 行 | L2 |
| Memory 提取（对话结束时提取） | ~200 行 | L2 |
| Bundle 集成（L_Memory 注入） | ~150 行 | L2 |
| 迁移工具（MEMORY.md → DB） | ~100 行 | L1 |
| Tests | ~500 行 | — |
| **总计** | **~1350 行** | **L3 项目** |

预计 **3-5 个子 task**，CTO Agent 执行引擎交付。

---

## 7. 验收清单

- [ ] 对话结束时自动提取记忆，写入 DB
- [ ] `add_memory` / `search_memories` / `update_memory` / `forget` 四个 Tool 可用
- [ ] 记忆按 priority 自动衰减归档
- [ ] 新记忆写入时自动去重
- [ ] 认知包 Bootstrap 时注入 L_Memory 相关记忆
- [ ] 焦点切换时重新装载关联记忆
- [ ] MEMORY.md 一次性迁移成功
- [ ] 全部在 SQLite 内，无外部依赖
- [ ] 零额外模型调用费用
