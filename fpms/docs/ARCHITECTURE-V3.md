# FPMS 分形项目管理系统 — 技术架构文档 V3.0

**版本**: V3.0 | **日期**: 2026-03-15  
**设计范式**: 大小脑解耦 · 控制反转(IoC) · 确定性优先 · 内存投影架构  
**审核来源**: GPT / Gemini / Grok 共7轮架构审核后的最终收敛版

---

## 1. 架构愿景

### 1.1 一句话定义

**用纯文本文件作为唯一事实源，启动时投影到内存SQLite进行图计算，让AI Agent拥有持续的项目上下文意识——零数据库依赖、零Token基建税、零运维成本。**

### 1.2 核心设计原则

| 原则 | 含义 | 来源 |
|------|------|------|
| **确定性优先** | 状态冒泡、环检测、死锁拦截等逻辑100%由Python代码完成，绝不交给LLM | Gemini |
| **控制反转(IoC)** | 数据主动找CPU，不是CPU摸黑找数据。Agent被唤醒前Context已组装好 | Gemini |
| **单一事实源(SSoT)** | 磁盘上只有MD文件，内存SQLite是一次性投影，崩溃重启即恢复 | Gemini |
| **0 Token基建税** | 状态推导、依赖寻址、全局投影等系统运维操作零LLM调用 | 全部 |
| **胖代码瘦DB** | SQL只做查询和批量更新，业务逻辑(冒泡规则/迁移规则)在Python中可见可调试 | Gemini |
| **精准胜于全面** | 5k精准Context > 50k泛泛Context，每个token必须服务于当前任务 | PRD |

### 1.3 关键架构创新

**DCP (Deterministic Context Push) — 确定性上下文注入**

传统Agent系统使用PSP（概率性语义拉取）：Agent醒来后摸黑搜索，N+1查询，Token浪费严重。

FPMS使用DCP：Agent被唤醒的前一毫秒，脊髓层基于内存图计算，以当前焦点为中心BFS遍历，瞬间组装完美的Context Bundle直接Push给Agent。

```
PSP模式: Agent醒来 → search("Anext进度") → 阅读 → search("法务进度") → ...
DCP模式: Agent醒来 → Context Bundle已在System Prompt里 → 直接回答
```

**内存投影架构 (In-Memory Projection)**

```
磁盘(SSoT)          内存(计算层)         Agent
MD Frontmatter  →   sqlite3(':memory:')  →  Context Bundle
   ↑                      ↓
   └── 计算结果回写Frontmatter ←┘
```

- 启动时：读取所有MD文件 → 提取Frontmatter → INSERT到内存SQLite
- 运行时：SQL辅助查询 + Python业务逻辑
- 写回时：计算结果 → 更新MD Frontmatter原子写入
- 崩溃恢复：重启即重建，永不脑裂

---

## 2. 系统拓扑架构

### 2.1 三层总览

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LAYER 3 · 认知层                      3 模块
 非确定性 · LLM · 按需计费
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ① 决策引擎    ② 叙事生成器    ③ 语义摘要器
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      ↑ Context Bundle (Push)  ↓ Tool Call
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LAYER 2 · 运行时内核                  7 模块
 确定性 · 纯Python · 0 Token · 毫秒级
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ④ 内存SQLite引擎    ⑤ 状态机    ⑥ 焦点选择器
 ⑦ Bundle组装器    ⑧ Risk扫描器    ⑨ 投影引擎
                  ⑩ 文件回写器
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      ↑ 读取(微秒)      ↓ 原子写入Frontmatter
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LAYER 1 · 存储层                      3 模块
 纯文本 · Git追踪 · 100%数据主权
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ⑪ MD节点文件    ⑫ 事件日志    ⑬ 归档冷冻区
 + 派生视图: global_view / focus_view / alert_view
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2.2 完整模块清单

| # | 层级 | 模块 | 类型 | 核心职责 | LLM | Token |
|---|------|------|------|---------|-----|-------|
| ① | 认知 | 决策引擎 | 非确定性 | 意图理解 → Tool指令输出 | ✅ 旗舰 | 按需 |
| ② | 认知 | 叙事生成器 | 非确定性 | 状态变更 → 人类可读叙事 | ✅ 旗舰 | 按需 |
| ③ | 认知 | 语义摘要器 | 非确定性 | 超长日志 → 精炼摘要(规则优先,Ollama fallback) | ✅ Ollama | 免费 |
| ④ | 内核 | 内存SQLite引擎 | 确定性 | 启动投影/图查询/递归CTE/关系计算 | ❌ | $0 |
| ⑤ | 内核 | 状态机 | 确定性 | 状态迁移/冒泡/级联解锁/健康度/风险标记 | ❌ | $0 |
| ⑥ | 内核 | 焦点选择器 | 确定性 | 焦点仲裁/时间衰减/事件驱动/用户指定 | ❌ | $0 |
| ⑦ | 内核 | Bundle组装器 | 确定性 | L2焦点全文+L1近景摘要+L0全局概览+token预算 | ❌ | $0 |
| ⑧ | 内核 | Risk扫描器 | 确定性 | deadline检测/stale检测/blocked升级/优先级调整 | ❌ | $0 |
| ⑨ | 内核 | 投影引擎 | 确定性 | 多视图生成(global/focus/alert)/L0缓存 | ❌ | $0 |
| ⑩ | 内核 | 文件回写器 | 确定性 | Frontmatter原子更新/事件日志记录/归档移动 | ❌ | $0 |
| ⑪ | 存储 | MD节点文件 | 事实源 | Frontmatter骨架 + 叙事血肉(合体) | - | - |
| ⑫ | 存储 | 事件日志 | 事实源 | 结构化JSON审计轨迹(可回放/可调试) | - | - |
| ⑬ | 存储 | 归档冷冻区 | 事实源 | Done+7天+入度=0的节点冷存储 | - | - |

**统计: 13个模块 (认知3 + 内核7 + 存储3) + 3个派生视图**

---

## 3. 数据模型

### 3.1 节点文件格式 (Frontmatter + 叙事合体)

每个节点是一个`.md`文件，存储在`fpms/nodes/`目录下。

**文件名**: `{prefix}-{hash}.md` (例: `anext-7f2a.md`)

```markdown
---
id: anext-7f2a
title: "Anext 信贷协议最终审核"
status: blocked

relations:
  parent_id: macro-0a1b
  depends_on: [legal-5x2p]

metadata:
  owner: Jeff
  priority: high
  deadline: "2026-03-20T18:00:00Z"
  created: "2026-03-10T09:00:00Z"

background_summary: |
  利率已从8.2%降至7.8%，Charles让步但增加连带担保条款。
  当前等待法务team审核担保条款的法律风险评估。
---

# Anext 信贷协议 - 叙事时间线

## 背景
Anext寻求700万信贷额度，用于扩大KA商户覆盖。

## 关键事件 (Append-Only)

**2026-03-10 09:30** - 初始条件
- Charles提出8.2%年化利率
- 要求Uniweb公司作为担保方

**2026-03-12 14:15** - 利率谈判成功
- Jeff推回利率过高，Charles同意降至7.8%
- 但坚持连带担保条款

**2026-03-13 16:45** - [BLOCKED] 法务介入
- 发现担保条款涉及"连带无限责任"
- 转交法务team (legal-5x2p) 审核
```

### 3.2 ID命名规则

| 组成 | 规则 | 示例 |
|------|------|------|
| 前缀 | 项目/类型简写，4字符 | anext, netst, legal, pdax |
| 分隔符 | `-` | - |
| 后缀 | 随机短哈希，4字符hex | 7f2a, 9k3l, 5x2p |
| 完整ID | `{prefix}-{hash}` | `anext-7f2a` |

### 3.3 状态集

| 状态 | 含义 | 可迁移到 |
|------|------|---------|
| `active` | 正在进行中 | waiting, blocked, done, dropped |
| `waiting` | 等待外部输入 | active, blocked, done, dropped |
| `blocked` | 被依赖方阻塞 | active (当阻塞解除) |
| `done` | 已完成 | (终态，7天后可归档) |
| `dropped` | 已放弃 | (终态，立即从index移除) |

### 3.4 关系类型

| 类型 | 字段 | 冒泡 | 用途 |
|------|------|------|------|
| **强边** | `parent_id` | ✅ 参与冒泡 | 层级归属，子→父状态传播 |
| **弱边** | `depends_on[]` | ❌ 不参与冒泡 | 阻塞警告，仅用于级联解锁 |

### 3.5 内存SQLite Schema

启动时从Frontmatter投影生成，不落盘：

```sql
-- 节点表
CREATE TABLE nodes (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL CHECK(status IN ('active','waiting','blocked','done','dropped')),
    parent_id   TEXT,
    owner       TEXT,
    priority    TEXT,
    deadline    TEXT,
    created     TEXT,
    background_summary TEXT,
    file_path   TEXT NOT NULL,  -- 对应的MD文件路径
    FOREIGN KEY (parent_id) REFERENCES nodes(id)
);

-- 依赖关系表
CREATE TABLE dependencies (
    from_id     TEXT NOT NULL,  -- 被阻塞方
    to_id       TEXT NOT NULL,  -- 阻塞方
    PRIMARY KEY (from_id, to_id),
    FOREIGN KEY (from_id) REFERENCES nodes(id),
    FOREIGN KEY (to_id) REFERENCES nodes(id)
);

-- 索引
CREATE INDEX idx_nodes_status ON nodes(status);
CREATE INDEX idx_nodes_parent ON nodes(parent_id);
CREATE INDEX idx_nodes_deadline ON nodes(deadline);
CREATE INDEX idx_deps_to ON dependencies(to_id);
```

### 3.6 事件日志格式

`fpms/events.jsonl` (JSON Lines, Append-Only):

```json
{"ts":"2026-03-15T14:03:00Z","op":"update_status","node":"legal-5x2p","from":"active","to":"done","cascade":["anext-7f2a:blocked→active"],"actor":"agent"}
{"ts":"2026-03-15T14:03:00Z","op":"bubble_up","node":"macro-0a1b","from":"active","to":"active","reason":"sibling anext-7f2a still blocked"}
```

### 3.7 目录结构

```
fpms/
├── docs/
│   └── ARCHITECTURE-V3.md     # 本文档
├── nodes/                      # 所有活跃节点 (MD Frontmatter + 叙事)
│   ├── anext-7f2a.md
│   ├── legal-5x2p.md
│   ├── netst-9k3l.md
│   └── ...
├── archive/                    # Done+7天+入度=0 的冷冻节点
├── views/                      # 派生视图 (只读，自动生成)
│   ├── global_view.md
│   ├── focus_view.md
│   └── alert_view.md
├── events.jsonl                # 事件日志 (Append-Only)
└── spine.py                    # 脊髓引擎 (全部运行时内核)
```

---

## 4. 核心工作流

### 4.1 启动投影流 (Boot Projection)

```
Agent唤醒 / spine.py启动
    │
    ↓
读取 fpms/nodes/*.md 所有文件 (<10ms, SSD)
    │
    ↓
解析每个文件的 YAML Frontmatter
    │
    ↓
INSERT INTO sqlite3(':memory:') nodes表 + dependencies表
    │
    ↓
内存SQLite就绪 → 可执行SQL查询
    │
    ↓
④ 内存SQLite引擎准备完毕
```

### 4.2 上下文注入流 (Context Push)

```
用户提问: "Anext卡在哪了?"
    │
    ↓
⑥ 焦点选择器: 匹配关键词 → Focus = anext-7f2a
    │
    ↓
⑦ Bundle组装器:
    ├── L2 焦点: 读取 anext-7f2a.md 完整叙事 (~800 tokens)
    ├── L1 近景: SQL查询parent + siblings + depends_on的摘要 (~600 tokens)
    ├── L0 背景: 引用⑨投影引擎的全局缓存 (~500 tokens)
    └── 预警:   ⑧Risk扫描器注入deadline/stale警告 (~100 tokens)
    │
    ↓ Context Bundle (~2k tokens) Push到System Prompt
    │
    ↓
① 决策引擎(LLM): 基于完美上下文直接回答
    "Anext目前被法务审核(legal-5x2p)卡住了,
     3/10引入了连带担保条款, 律师预计3/18出意见..."
```

### 4.3 状态变更流 (Safe Mutation)

```
① 决策引擎输出: update_status("legal-5x2p", "done")
    │
    ↓
⑤ 状态机接管:
    │
    ├── 1. 验证迁移合法性: active→done ✅
    │
    ├── 2. 更新内存SQLite: UPDATE nodes SET status='done' WHERE id='legal-5x2p'
    │
    ├── 3. 级联解锁(Python逻辑):
    │      SQL: SELECT from_id FROM dependencies WHERE to_id='legal-5x2p'
    │      发现 anext-7f2a 被阻塞 → 检查其所有depends_on是否全done
    │      → 全done → anext-7f2a: blocked→active
    │
    ├── 4. 向上冒泡(Python逻辑):
    │      SQL: WITH RECURSIVE ancestors AS (...) 
    │      沿parent_id向上扫描
    │      兄弟全done → 父节点done
    │      兄弟有blocked → 父节点标记attention_required
    │
    └── 5. 健康度评估:
           检查是否产生状态死锁/流程停滞
    │
    ↓
⑩ 文件回写器:
    ├── 更新 legal-5x2p.md Frontmatter: status→done
    ├── 更新 anext-7f2a.md Frontmatter: status→active
    ├── 追加 events.jsonl: 状态变更记录
    ├── 触发 ⑨投影引擎: 重绘 views/*.md
    └── 检查归档条件: legal-5x2p Done+入度=0 → 7天后移入archive/
    │
    ↓
② 叙事生成器(LLM):
    追加到 legal-5x2p.md:
    "**2026-03-15 14:03** - [DONE] 法务审核通过，阻塞解除"
    追加到 anext-7f2a.md:
    "**2026-03-15 14:03** - 法务审核通过，项目重新激活"
```

---

## 5. 三类死锁防护

| 类型 | 检测模块 | 触发时机 | 机制 | 处理方式 |
|------|---------|---------|------|---------|
| **结构死锁** | ④ 内存SQLite引擎 | 添加依赖时 | 递归CTE检测环路 | 拒绝写入，Error返回LLM |
| **状态死锁** | ⑤ 状态机 | 状态变更后 | 节点组合分析(互等/全blocked) | 标记`health=stalled` |
| **流程死锁** | ⑧ Risk扫描器 | 定期扫描 | `status=waiting/blocked` > 7天 | `attention_required=true` |

### 结构死锁检测 (SQL实现):

```sql
-- 检查添加 A→B 依赖后是否成环
WITH RECURSIVE chain(id, path) AS (
    SELECT to_id, ARRAY[from_id, to_id]
    FROM dependencies WHERE from_id = :new_from
    UNION ALL
    SELECT d.to_id, chain.path || d.to_id
    FROM dependencies d JOIN chain ON d.from_id = chain.id
    WHERE d.to_id != ALL(chain.path)  -- 防无限递归
)
SELECT EXISTS(SELECT 1 FROM chain WHERE id = :new_from) AS has_cycle;
```

---

## 6. 眼球模型 (Foveal Vision)

### 6.1 三层分辨率

| 层级 | 隐喻 | 信息量 | Token预算 | 数据来源 |
|------|------|--------|----------|---------|
| **L2 焦点** | 注视点 | 完整叙事+决策历史+联系人+依赖 | ~2.5k | MD全文读取 |
| **L1 近景** | 焦点旁边 | 摘要+状态+下一步+卡点 | ~1.5k | SQL查询parent/siblings/deps的background_summary |
| **L0 背景** | 视野边缘 | 一句话状态 | ~500 | ⑨投影引擎全局缓存 |

### 6.2 焦点驱动方式

| 驱动方式 | 描述 | 实现 |
|---------|------|------|
| **用户驱动** | Jeff提到某个项目/任务 | ⑥焦点选择器关键词匹配 |
| **时间驱动** | deadline < 48h | ⑧Risk扫描器自动升级 |
| **事件驱动** | 收到相关消息/邮件 | 外部事件触发 |
| **衰减机制** | >3天未接触 | ⑥焦点选择器自动降级 |

### 6.3 Token预算总控

```
PRD约束: 系统总占用 < context window的5% = 10k tokens

实际分配:
  L0 全局概览     ~500 tokens   (⑨投影引擎)
  L1 近景摘要    ~1.5k tokens   (⑦Bundle: parent+siblings+deps)
  L2 焦点全文    ~2.5k tokens   (⑦Bundle: 当前节点完整叙事)
  预警注入        ~500 tokens   (⑧Risk扫描器)
  ────────────────────────────
  总计           ~5k tokens     ✅ 远低于10k上限
```

---

## 7. 约束合规性验证

| PRD约束 | V3.0合规性 | 说明 |
|---------|-----------|------|
| 纯文件系统，不依赖数据库 | ✅ | 磁盘上零DB文件，sqlite3(':memory:')是Python标准库计算工具 |
| Agent在OpenClaw框架内运行 | ✅ | spine.py通过exec Tool调用，或集成为OpenClaw Shell Tool |
| 不破坏MEMORY.md/memory/ | ✅ | FPMS数据在fpms/目录下，完全隔离 |
| Token预算<5% | ✅ | 实际~5k tokens，占2.5% |
| Markdown+YAML格式 | ✅ | MD Frontmatter(YAML) + 叙事(Markdown) |
| 人类可读 | ✅ | cat/vim直接查看编辑 |
| Git追踪 | ✅ | 纯文本，完美diff/blame/checkout |
| 零外部依赖 | ✅ | Python标准库(sqlite3, yaml, json) |

---

## 8. 需求覆盖矩阵

| 需求 | 描述 | 承载模块 | 状态 |
|------|------|---------|------|
| FR-1 | 统一节点模型 | ⑪MD节点文件(Frontmatter) | ✅ |
| FR-2 | 叙事体上下文 | ⑪MD节点文件(叙事部分) + ②叙事生成器 | ✅ |
| FR-3 | 快速全局概览≤50行 | ⑨投影引擎 → global_view.md | ✅ |
| FR-4 | 按需深度加载 | ⑦Bundle组装器(L2) | ✅ |
| FR-5 | 状态冒泡 | ⑤状态机 + ④内存SQLite引擎 | ✅ |
| FR-6 | 智能遗忘/归档 | ⑤状态机 + ⑩文件回写器 → ⑬归档 | ✅ |
| FR-7 | Inbox快速捕获 | ①决策引擎 + ⑩文件回写器(parent_id=null) | ✅ |
| FR-8 | 主动提醒/Heartbeat | ⑧Risk扫描器 | ✅ |
| FR-9 | 眼球模型 | ⑥焦点选择器 + ⑦Bundle组装器 | ✅ |
| FR-10 | 30秒上下文恢复 | ④启动投影 + ⑥焦点 + ⑦Bundle | ✅ |
| NFR-1 | Context效率<10k | ⑦Bundle组装器(token预算控制) | ✅ |
| NFR-2 | Agent自主维护 | ①决策引擎 + ⑩文件回写器 | ✅ |
| NFR-3 | 渐进式增长 | ④内存SQLite引擎(动态投影) | ✅ |
| NFR-4 | 容错 | ④引擎 + ⑤状态机(子节点为准重新计算) | ✅ |

---

## 9. 模块间数据流

```
用户提问
  │
  ↓
④ 内存SQLite引擎 ← 启动时投影自 ← ⑪ MD节点文件
  │
  ├→ ⑥ 焦点选择器 (SQL辅助匹配 + 规则仲裁)
  │     │
  │     ↓
  ├→ ⑦ Bundle组装器 ← 读取MD全文(L2) + SQL查询摘要(L1) + 引用⑨缓存(L0)
  │     │
  │     ↓ Context Bundle (Push)
  │
  ├→ ⑧ Risk扫描器 → 预警注入Bundle
  │
  ↓
① 决策引擎 (LLM)
  │
  ├→ 回答用户
  │
  └→ Tool Call: update_status() / create_node() / append_log()
        │
        ↓
  ⑤ 状态机 ← SQL查询辅助 ← ④ 内存SQLite引擎
        │
        ├→ 迁移合法性验证 (Python规则)
        ├→ 级联解锁计算 (SQL查询 + Python逻辑)
        ├→ 向上冒泡计算 (递归CTE + Python规则)
        ├→ 健康度评估 (Python规则)
        ├→ 更新内存SQLite (UPDATE)
        │
        ↓
  ⑩ 文件回写器
        │
        ├→ 原子更新MD Frontmatter → ⑪ MD节点文件
        ├→ 追加 → ⑫ 事件日志 (events.jsonl)
        ├→ 触发 → ⑨ 投影引擎 → views/*.md (派生视图)
        ├→ 检查归档 → ⑬ 归档冷冻区
        │
        └→ 通知 → ② 叙事生成器(LLM)
                      │
                      └→ 追加叙事到 ⑪ MD节点文件
```

---

## 10. 关键架构决策记录 (ADR)

| # | 决策 | 选择 | 备选 | 理由 | 审核来源 |
|---|------|------|------|------|---------|
| 1 | 持久化方式 | MD Frontmatter(SSoT) | YAML+MD分离 / SQLite落盘 | 单一事实源，零双写风险，Git完美追踪 | Gemini |
| 2 | 计算引擎 | 内存SQLite投影 | NetworkX内存图 / 持久化SQLite | SQL查询能力+零落盘风险+崩溃重建 | Gemini |
| 3 | LLM隔离层 | 最外层(认知层) | 混合在脊髓层 | 最不稳定的变化隔离在外，Clean Arch原则 | Grok |
| 4 | 环检测归属 | ④内存SQLite引擎 | ⑤状态机 | 图结构性质≠业务逻辑 | Gemini |
| 5 | 叙事压缩 | 规则优先,Ollama fallback | 纯LLM / 纯规则 | 90%确定性，极端才用LLM | Grok |
| 6 | 焦点与组装 | 独立模块⑥⑦ | 合并为一个 | 选择和拼装是独立决策 | Gemini |
| 7 | 状态冒泡 | SQL查询+Python规则 | SQL触发器 | 触发器是反模式，胖代码瘦DB | Gemini |
| 8 | 全局看板 | 派生视图(只读) | 事实源 | 不是SSoT，禁止手动编辑 | GPT+Gemini |
| 9 | 事件日志 | JSONL Append-Only | 无 / SQLite表 | 可审计/可回放/可调试，纯文本Git友好 | GPT |
| 10 | 死锁分类 | 3类(结构/状态/流程) | 笼统"死锁拦截" | 精确定义避免实现混乱 | Gemini |

---

## 11. Sprint规划

### Sprint 1 (P0): 写链路核心
- ④ 内存SQLite引擎: 启动投影 + 基础查询
- ⑤ 状态机: 冒泡 + 级联解锁 + 环检测
- ⑩ 文件回写器: Frontmatter原子更新 + 事件日志
- ⑨ 投影引擎: global_view.md生成

### Sprint 2 (P1): 接入Agent
- ① 决策引擎: OpenClaw Tool集成
- ② 叙事生成器: 状态变更→叙事追加
- ⑦ Bundle组装器: L0+L1+L2完整组装
- ⑥ 焦点选择器: 基础关键词匹配

### Sprint 3 (P2): 长线运维
- ⑧ Risk扫描器: deadline/stale检测
- ③ 语义摘要器: 规则压缩 + Ollama fallback
- ⑬ 归档冷冻: 自动归档逻辑

---

## 12. 与OpenViking对比

```
                    FPMS V3.0        OpenViking
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
定位              项目管理认知OS      通用上下文数据库
模块数             13                 18
语言栈            纯Python           Python+Go+Rust+C++
外部API依赖        0                  4(Embedding+VLM)
Token基建税       $0/月              持续消耗
持久化            MD文件(SSoT)       viking://专有协议
计算引擎          内存SQLite投影      Embedding+向量检索
上下文寻址        DCP(确定性Push)    PSP(概率性Pull)
状态冒泡          ✅ 内置             ❌ 不支持
业务语义          ✅ 项目管理         ❌ 通用存储
Git追踪           ✅ 100%            ❌ 专有格式
部署复杂度        单文件spine.py     Server+AGFS+DB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

*本文档经GPT/Gemini/Grok共7轮架构审核，所有关键决策均有据可查。*
*最后更新: 2026-03-15 V3.0*
