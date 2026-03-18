# PRD: FPMS 内建记忆层 v1.1

**状态**: Draft  
**日期**: 2026-03-18  
**作者**: Jeff + AI  
**变更**: v1.0 → v1.1，基于架构评审补充 10 项边界定义

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
2. **借用现有模型** — 记忆提取借用当前对话的 LLM（已付费），不新增独立模型与基础设施成本，但会增加单次对话 token 消耗（约 200-500 tokens/次）
3. **确定性优先** — 检索用标签 + 时间 + 关联，不用向量搜索
4. **与项目管理互补** — 记忆层管"知道什么"，项目层管"要做什么"
5. **治理优先** — 记忆系统的核心难题不是存储，是防止错误记忆稳定地写入并反复喂回系统

---

## 2. 记忆模型

### 2.1 记忆分类

| 类型 | 判定规则（可判定，非描述性） | 示例 | 推荐 priority |
|------|--------------------------|------|--------------|
| `fact` | 用户**明确陈述**的客观事实，可验证 | "Jeff 的公司在新加坡" | P0 |
| `preference` | 用户**明确表达**的偏好或习惯 | "Jeff 不喜欢冗长的回复" | P0 |
| `relationship` | 用户**明确确认**的人际/组织关系 | "Charles 是 Anext 的联系人" | P0 |
| `decision` | 用户**明确做出**的选择，有明确的"选 A 不选 B" | "选择 6 位 hex 作为 node ID 格式" | P0 |
| `lesson` | 实际发生的错误/踩坑 + 明确的修正动作 | "subagent 必须 commit 否则 worktree 改动丢失" | P0 |
| `context` | 有明确时效的临时状态 | "Jeff 今天在飞行中，2 小时后回来" | P2 |
| `event` | 已发生的具体事件，有时间戳 | "2026-03-18 完成了 6 个 M 系列 task" | P1 |

**分类边界判定规则（冲突时从上到下匹配第一个命中的）**：
1. 有"选 A 不选 B"结构 → `decision`
2. 有错误 + 修正动作 → `lesson`
3. 有明确时效且会过期 → `context`
4. 是已发生事件的记录 → `event`
5. 描述人与人/组织的关系 → `relationship`
6. 表达偏好/喜好/习惯 → `preference`
7. 以上都不是但可验证 → `fact`

**category 枚举唯一来源**：本 PRD §2.1。Schema、提取 prompt、检索逻辑必须引用此定义，不得各自硬编码。

### 2.2 记忆字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 系统生成 | `mem-{6hex}` |
| `category` | enum | ✅ | 2.1 中的 7 种分类 |
| `content` | string | ✅ | 记忆内容（一句话，不超过 200 字） |
| `tags` | string[] | ❌ | 检索标签（人名、项目、技术等） |
| `node_id` | string | ❌ | 关联的 FPMS 节点（项目/任务） |
| `confidence` | float | ✅ | 0.0-1.0，提取时的置信度 |
| `verification` | enum | ✅ | `user_confirmed` / `system_verified` / `auto_extracted` |
| `source` | enum | ✅ | `auto`（自动提取）/ `manual`（手动创建）/ `system`（系统生成） |
| `priority` | enum | ✅ | `P0`（永久）/ `P1`（90天）/ `P2`（30天） |
| `created_at` | datetime | 系统生成 | 创建时间 |
| `last_accessed_at` | datetime | 系统维护 | 最近一次被召回的时间 |
| `access_count` | int | 系统维护 | 被召回次数 |
| `conflict_count` | int | 系统维护 | 被其他记忆冲突/质疑的次数 |
| `similar_to` | string | ❌ | 指向疑似重复的记忆 ID（候选关系，不自动覆盖） |
| `archived_at` | datetime | ❌ | 归档时间 |

### 2.3 TTL 唯一规则

**衰减只看 priority，不看 category。** Category 只提供"推荐 priority"（§2.1），实际写入时以 LLM 输出或人工指定的 priority 为准。不存在第二套 TTL 规则。

| Priority | 衰减条件 |
|----------|---------|
| P0 | 永不自动归档 |
| P1 | created_at > 90 天 且 access_count < 5 |
| P2 | created_at > 30 天 且 access_count < 3 |

**唯一来源**：本 PRD §2.3。

### 2.4 与项目节点的关系

- 记忆可以通过 `node_id` 关联到 FPMS 节点
- 当焦点切换到某个项目时，关联记忆**按需查询**（不自动全量注入）
- 记忆不是节点的子对象，是独立实体——项目归档了记忆还在

---

## 3. 事实源架构

### 3.1 层级定义

```
memory_events (append-only 事件流) ← 事实源 / Source of Truth
        ↓ projection
memories 表 (当前物化视图) ← 可重建的 projection
```

- **memory_events**：append-only 表，记录每一次记忆操作（create / update / archive / access）。不可修改、不可删除。这是记忆层的 Source of Truth。
- **memories**：当前状态的物化视图，由 memory_events 投影而来。损坏时可从 memory_events 完整重建。

### 3.2 事件类型

| 事件 | 说明 |
|------|------|
| `memory_created` | 新记忆写入 |
| `memory_updated` | 字段修改（记录 old_value / new_value） |
| `memory_archived` | 归档（衰减或手动 forget） |
| `memory_accessed` | 被召回（更新 access_count / last_accessed_at） |
| `memory_conflicted` | 与其他记忆产生冲突（更新 conflict_count） |

---

## 4. 功能需求

### FR-1: 自动记忆提取

**触发时机**：对话结束前（session compaction 或 heartbeat 时）

**提取方式**：利用当前对话 LLM，在对话末尾追加提取指令。

**自动提取禁止写入清单（硬规则）**：

以下内容 **绝对禁止** auto source 写入，脊髓引擎必须拦截：

| 禁止类型 | 示例 | 判定规则 |
|----------|------|---------|
| 推断类内容 | "Jeff 可能想做支付系统" | 含"可能/应该/也许/大概/推测" |
| 未确认关系 | "那个人可能是他老板" | relationship 且 confidence < 0.8 |
| 运营状态猜测 | "项目进度可能延期" | 非用户明确陈述的状态 |
| 模型总结/抽象 | "总体来说用户倾向于..." | 非原始事实，是归纳 |
| 涉及第三方隐私 | "某某的工资是..." | 含薪资/健康/私人信息 |

**只有以下才允许 auto 入库**：
- 用户明确陈述的事实
- 用户明确做出的决策
- 系统事件（task 完成、错误发生）
- 用户明确表达的偏好

**写入流程**：
1. LLM 返回 JSON 数组
2. 脊髓引擎校验格式、字段、禁止清单
3. 相似检查 → 命中时标记 `similar_to`（不覆盖）
4. 写入 memory_events（append-only）
5. 投影到 memories 表
6. auto 来源的记忆默认 `verification = auto_extracted`

### FR-2: 手动记忆管理

| Tool | 功能 | 权限 |
|------|------|------|
| `add_memory` | 手动添加一条记忆 | Agent + 人类。写入时 `verification = user_confirmed` |
| `search_memories` | 按 category/tags/node_id/关键词检索 | Agent + 人类。只读 |
| `update_memory` | 修改记忆内容或元数据 | **仅 manual/system source 可直接修改。auto source 必须先升级为 user_confirmed 才能修改**。修改记录 old_value/new_value 到 memory_events |
| `forget` | 归档一条记忆 | Agent + 人类。写入 memory_events 审计事件后标记 archived_at。不物理删除 |
| `confirm_memory` | 将 auto_extracted 升级为 user_confirmed | 仅人类触发（Agent 可建议但不可自行确认） |

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
| `verification` | 按验证状态筛选 |

**排序规则**（默认，可信度优先）：
1. verification 降序（user_confirmed > system_verified > auto_extracted）
2. priority 降序（P0 > P1 > P2）
3. confidence 降序
4. conflict_count 升序（冲突越少越可信）
5. last_accessed_at 降序

**负反馈机制**：
- 用户纠正某条记忆时 → 旧记忆 conflict_count +1，排序自动降权
- 记忆被 `forget` 后 → 同 tags 的 similar_to 链条上的记忆 conflict_count +1

### FR-4: 记忆注入认知包

**扩展 Context Bundle**，在 L_Alert 和 L1 之间新增 **L_Memory**：

```
L0 全局看板
L_Alert 系统告警
L_Memory 相关记忆（新增）
L1 近景关联
L2 焦点区
```

**L_Memory 分两层**：

**常驻层（每次 Bootstrap 必注入）**：
- `preference` + `user_confirmed` + P0 → 核心偏好（如沟通风格）
- `fact` + `user_confirmed` + P0 + access_count > 10 → 核心身份事实
- **上限 3 条，≤ 150 tokens**

**按需层（焦点切换时查询注入）**：
- 焦点节点 `node_id` 关联的记忆（仅 `user_confirmed` 或 `system_verified`）
- 当前对话提到的 tags 匹配的记忆（仅 confidence > 0.7）
- **上限 5 条，≤ 350 tokens**

**L_Memory 总预算：≤ 500 tokens**

**绝不注入的**：
- `auto_extracted` 且 `conflict_count > 0` 的记忆
- `archived_at` 不为空的记忆
- `confidence < 0.5` 的记忆

### FR-5: 去重策略（Append-First）

**核心原则：自动流程永远 append-only，不覆盖旧记忆。**

新记忆写入时：
1. 检查同 category 下 content 关键词重叠率
2. 重叠 > 80% → 新记忆正常创建，同时标记 `similar_to = 旧记忆 ID`
3. **不修改旧记忆的任何字段**
4. 两条共存，由检索排序自然优胜劣汰

**合并/覆盖旧记忆**的条件（高门槛）：
- 人类通过 `confirm_memory` 确认新版本 → 旧版本可被 `forget`
- 或人类通过 `update_memory` 直接修改

### FR-6: 记忆衰减与维护

**自动衰减**（Heartbeat 或 Cron 触发）：

衰减规则见 §2.3（唯一来源）。

**额外降权规则**：
- `auto_extracted` + 超过 30 天未被 accessed + 未被 confirm → 自动归档（不论 priority）
- `conflict_count > 3` → 自动归档

### FR-7: 记忆迁移

**从 MEMORY.md 冷启动**：
- 提供一次性迁移工具，解析现有 MEMORY.md
- 按内容自动分类 + 打标签
- 导入时 `source = system`，`verification = auto_extracted`
- 迁移后建议用户逐条 confirm 重要记忆
- MEMORY.md 标记为 legacy，不再使用

---

## 5. 协议一致性

| 定义 | 唯一来源 |
|------|---------|
| Category 枚举 + 判定规则 | 本 PRD §2.1 |
| Priority / TTL 衰减规则 | 本 PRD §2.3 |
| 自动提取禁止清单 | 本 PRD §FR-1 |
| L_Memory 注入策略 | 本 PRD §FR-4 |
| 事实源架构 | 本 PRD §3 |
| Tool 权限模型 | 本 PRD §FR-2 |

Schema、提取 prompt、检索逻辑、Bundle 组装必须引用本 PRD 定义，不得各自硬编码。提取 prompt 变更时须同步校验 §FR-1 禁止清单。

---

## 6. 非功能需求

| NFR | 要求 |
|-----|------|
| **存储** | 复用 FPMS 的 SQLite，新增 memories + memory_events 表 |
| **成本** | 不新增独立模型与基础设施。单次对话增加约 200-500 tokens 提取成本 |
| **性能** | 记忆检索 < 50ms（SQLite 索引查询） |
| **容量** | 支持 10,000+ 条记忆 |
| **隐私** | 全本地，不外传。隐私内容禁止 auto 入库（§FR-1 禁止清单） |
| **可恢复** | memory_events 是事实源，memories 表可完整重建 |

---

## 7. 非目标（v1 不做）

| 非目标 | 原因 |
|--------|------|
| 向量语义检索 | 确定性检索够用，不引入额外依赖 |
| 跨用户记忆 | 单用户场景 |
| 记忆推理 | 不做"基于记忆 A+B 推导 C" |
| 记忆可视化 UI | v1 通过 Tool Call 查询 |
| 自动关联发现 | 不自动推断记忆之间的关系 |
| 自动合并重复记忆 | append-first，合并需人工确认 |

---

## 8. 实现估算

| 模块 | 预估 | 等级 |
|------|------|------|
| Schema（memories + memory_events） | ~150 行 | L1 |
| Memory Store（CRUD + 事件流 + 投影） | ~400 行 | L2 |
| Memory 提取（对话结束时 + 禁止清单校验） | ~250 行 | L2 |
| Bundle 集成（L_Memory 常驻层 + 按需层） | ~200 行 | L2 |
| 迁移工具（MEMORY.md → DB） | ~100 行 | L1 |
| Tests | ~500 行 | — |
| **总计** | **~1600 行** | **L3 项目** |

---

## 9. 验收清单

### 写入安全
- [ ] 自动提取含"可能/应该/也许"的内容 → 拦截，不入库
- [ ] auto source 不可直接修改已有记忆
- [ ] 所有写入操作产生 memory_events 审计事件
- [ ] memories 表可从 memory_events 完整重建

### 去重与治理
- [ ] 相似记忆标记 similar_to，不自动覆盖
- [ ] update_memory 对 auto_extracted 记忆 → 拒绝（需先 confirm）
- [ ] forget 产生审计事件，不物理删除
- [ ] conflict_count > 3 的记忆自动归档

### 检索与注入
- [ ] 常驻层仅注入 user_confirmed + P0，≤ 3 条
- [ ] 按需层仅注入 confidence > 0.7 的记忆
- [ ] auto_extracted + conflict_count > 0 的记忆不进认知包
- [ ] L_Memory 总预算 ≤ 500 tokens

### 衰减
- [ ] P0 永不自动归档
- [ ] P2 超 30 天 + access_count < 3 → 归档
- [ ] auto_extracted 超 30 天未 accessed 未 confirm → 归档

### 迁移
- [ ] MEMORY.md 一键迁移成功
- [ ] 迁移后记忆 verification = auto_extracted

---

## 10. v1.0 → v1.1 变更摘要

| # | 问题 | 修复 |
|---|------|------|
| 1 | 自动提取无防污染机制 | 新增 FR-1 禁止写入清单（硬规则） |
| 2 | Category 不可判定 | §2.1 改为判定规则 + 冲突时优先级链 |
| 3 | Priority 和 category TTL 双轨 | §2.3 统一：衰减只看 priority |
| 4 | 去重自动覆盖旧记忆 | FR-5 改为 append-first，覆盖需人工确认 |
| 5 | 错误记忆自我强化 | 新增 conflict_count + verification 维度排序 |
| 6 | L_Memory 注入不够防御 | FR-4 分常驻层/按需层，严格准入条件 |
| 7 | "零成本"表述不严谨 | 改为"不新增独立模型，增加约 200-500 tokens/次" |
| 8 | 事实源定义不清 | §3 明确 memory_events = SoT，memories = projection |
| 9 | Tool 权限模型缺失 | FR-2 新增权限列 + confirm_memory Tool |
| 10 | 协议一致性未锁 | §5 新增唯一来源表 |
