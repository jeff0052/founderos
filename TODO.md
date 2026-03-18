# FounderOS 开发任务清单

> 更新: 2026-03-18 | 基于 Knowledge System v1 需求 + 当前代码状态

---

## 🔧 P0 — 收尾项（Memory Layer 接入）

Memory Layer 代码已写完但未接入 spine 路由，agent 无法调用。

- [ ] **T01** 在 `spine/tools.py` 注册 6 个 memory handler
  - `handle_memory_add` → `MemoryStore.add_memory()`
  - `handle_memory_search` → `MemoryStore.search_memories()`
  - `handle_memory_update` → `MemoryStore.update_memory()`
  - `handle_memory_forget` → `MemoryStore.forget()`
  - `handle_memory_promote` → `MemoryStore.promote_memory()`
  - `handle_memory_confirm` → `MemoryStore.confirm_memory()`
- [ ] **T02** ToolHandler.__init__ 初始化 MemoryStore 实例
- [ ] **T03** 补充 6 个 tool 的集成测试（通过 spine.py tool 调用验证）
- [ ] **T04** 更新 spine.py bootstrap 输出，显示常驻记忆摘要
- [ ] **T05** 更新 README / CHANGELOG，标记 Memory Layer 正式上线
- [ ] **T06** commit + push（标记 v0.4.0）

---

## 📡 Phase 1A — 信号检测（Signal Detection）

从信息流中自动识别关键 signal，减少 Jeff 手动总结。

- [ ] **T10** 定义 Signal 数据模型（type, source, urgency, content, related_memory_id）
- [ ] **T11** 设计 Signal Rules 引擎（规则定义格式 + 匹配逻辑）
- [ ] **T12** 实现基础规则集
  - 邮件关键词匹配（牌照、合规、紧急）
  - 日期/截止日提取
  - 金额/数字异常检测
- [ ] **T13** Signal → Memory 自动写入管道
- [ ] **T14** Signal 优先级排序算法
- [ ] **T15** Signal Dashboard 展示（集成到现有 dashboard）
- [ ] **T16** spine.py tool 注册（signal_scan, signal_list, signal_dismiss）
- [ ] **T17** 测试：规则匹配准确率 >70% 基准测试集

---

## 🕸️ Phase 1B — 关系图谱（Relationship Graph）

追踪合作伙伴、机构、人物之间的关系和互动温度。

- [ ] **T20** 设计 Entity 模型（person, org, institution + 属性）
- [ ] **T21** 设计 Relationship 模型（type, strength, last_interaction, notes）
- [ ] **T22** 复用 FPMS 的 nodes/edges 还是独立建表？→ 需架构决策
- [ ] **T23** 实现 entity CRUD（add, update, merge, archive）
- [ ] **T24** 实现 relationship CRUD + 温度衰减算法
- [ ] **T25** 从现有记忆/文档中提取初始实体（bootstrap 脚本）
- [ ] **T26** 关系可视化（D3.js 或集成到 dashboard）
- [ ] **T27** spine.py tool 注册（entity_add, entity_search, relationship_update）
- [ ] **T28** 测试：覆盖所有活跃合作伙伴

---

## 🧬 Phase 1C — 概念蒸馏（Concept Distillation）

从日常细节中提炼出可复用的模式和知识。

- [ ] **T30** 定义 Concept 模型（title, summary, evidence[], confidence, domain）
- [ ] **T31** 设计蒸馏管道（raw memory → pattern detection → concept proposal → Jeff 审核）
- [ ] **T32** 实现周期性蒸馏任务（heartbeat 触发或 cron）
- [ ] **T33** Concept 版本管理（概念会进化，需要追踪变更）
- [ ] **T34** Concept ↔ Memory 双向关联
- [ ] **T35** spine.py tool 注册（concept_list, concept_review, concept_merge）
- [ ] **T36** 测试：蒸馏输出格式验证 + Jeff 审核通过率追踪

---

## 📧 Phase 1D — 邮件采集（Email Ingestion）

自动采集和处理商务邮件，接入知识系统。

- [ ] **T40** 邮件接入方案选型（Gmail API / IMAP / forwarding）
- [ ] **T41** 邮件抓取 + 去重 + 存储
- [ ] **T42** 邮件解析器（发件人、主题、正文摘要、附件识别）
- [ ] **T43** 邮件 → Signal 管道（触发信号检测）
- [ ] **T44** 邮件 → Entity 管道（更新关系图谱交互记录）
- [ ] **T45** 邮件摘要生成（每日/每周 digest）
- [ ] **T46** 隐私过滤（敏感内容标记 + 访问控制）
- [ ] **T47** 测试：采集准确率 + 去重效果

---

## 🔍 Phase 2 — 检索 + 共享

- [ ] **T50** 向量数据库选型（sqlite-vss / Chroma / Qdrant）
- [ ] **T51** 文档 embedding 管道
- [ ] **T52** 语义检索 API（5000+ 文件 <3s）
- [ ] **T53** 多 Agent 记忆共享协议（CTO Agent ↔ Main Agent）
- [ ] **T54** 权限模型（哪些记忆可共享，哪些隔离）
- [ ] **T55** Context 恢复加速（新 session <30s 建立准确 context）

---

## 🧠 Phase 3 — 智能层

- [ ] **T60** 知识图谱构建（Entity + Concept + Memory 三元组）
- [ ] **T61** 多跳推理查询（3 跳以内）
- [ ] **T62** 预测性建议引擎（基于模式 + 趋势）
- [ ] **T63** 月度战略复盘自动化
- [ ] **T64** 新角色 onboarding（1 天内了解完整业务状态）

---

## 💰 经济模型

- [ ] **T70** 支付系统 PRD（project-0e05）
- [ ] **T71** 支付架构设计
- [ ] **T72** MVP 实现

---

## 📊 里程碑

| 里程碑 | 目标 | 预计 |
|--------|------|------|
| v0.4.0 | Memory Tools 接入路由，完全可用 | 本周 |
| v0.5.0 | Phase 1A 信号检测 MVP | 1-2 周 |
| v0.6.0 | Phase 1B 关系图谱 MVP | 2-3 周 |
| v0.7.0 | Phase 1C + 1D 概念蒸馏 + 邮件 | 1 月内 |
| v1.0.0 | Phase 2 语义检索 + 多 Agent 共享 | 1-3 月 |
| v2.0.0 | Phase 3 知识图谱 + 预测 | 3-6 月 |
