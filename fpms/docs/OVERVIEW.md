# FounderOS — 系统全景

> 最后更新: 2026-03-18 v0.5.0 (9aefac0)
> Jeff 的监督窗口：架构、进度、方向。具体任务状态看 FPMS。

---

## 一句话

FounderOS 让一个创始人+AI 管得住一家越来越复杂的公司。

## 总工程图

```
FounderOS — 放大一个人的能力
│
├── 灵魂（愿力）
│   ├── VISION.md ✅
│   ├── 白皮书 V3.1 ✅
│   └── 链上铭刻 — 未来
│
├── 大脑（知识系统）
│   ├── 记忆层 ✅（三层模型 + 事件溯源 + 6 MCP Tools 已接入路由）
│   ├── 信号检测 ❌ Phase 1
│   ├── 关系图谱 ❌ Phase 1
│   ├── 概念蒸馏 ❌ Phase 1
│   └── 邮件采集 ❌ Phase 1
│
├── 骨架（执行体系）
│   ├── FPMS 项目管理 ✅（594 tests, 26 MCP tools）
│   ├── CTO Agent 执行引擎 ✅（SUBAGENT-PROTOCOL + Constitution 22条）
│   ├── CTO 工具链 ✅（gstack 13 skills 已装）
│   └── 开发 SOP ✅（总分总 + 三阶段 + 三层文档体系）
│
├── 心脏（Jeff）
│   └── ✅ 一直在
│
└── 经济模型
    └── 支付系统 📥 inbox（project-0e05）
```

## Phase 进度

| Phase | 目标 | 状态 |
|-------|------|------|
| Phase 0 | 记忆底座 + 基础结构 + SOP | ✅ 3/18 完成 |
| Phase 1 | 信号检测 + 关系图谱 + 概念蒸馏 + 邮件 | ❌ 下一步 |
| Phase 2 | 向量检索 + 多 Agent 共享记忆 | ❌ |
| Phase 3 | 知识图谱 + 预测分析 | ❌ |

## 版本线

| 版本 | 日期 | 一句话 | tests |
|------|------|--------|-------|
| v0.1.0 | 3/17 | FPMS v1: 16模块 | 494 |
| v0.2.0 | 3/18 | CTO Agent 体系 | 494 |
| v0.3.0 | 3/18 | Constitution Guard | 533 |
| v0.3.1 | 3/18 | Memory Layer v1 | 576 |
| v0.4.0 | 3/18 | Memory Tools 接入路由 | 594 |
| **v0.5.0** | **3/18** | **开发 SOP + gstack 工具链** | **594** |

## 开发工具链

- **CTO Agent** 装了 **gstack** (garrytan/gstack) — 13 skills
- 现阶段启用：/plan-eng-review, /review, /ship, /retro
- 未来启用：/qa, /browse, /design-review（有 UI 产品时）
- 配置：`.claude/CLAUDE.md`

## 三层文档分工

| 文档 | 职责 | 内容 |
|------|------|------|
| FPMS | what — 任务状态 | `python3 fpms/spine.py dashboard` |
| OVERVIEW.md | where — 系统全景 | 本文件 |
| MEMORY.md | how — 工作记忆 | 约定、偏好、教训 |

## 查看实时状态

```bash
python3 fpms/spine.py dashboard    # FPMS 看板
python3 fpms/spine.py bootstrap    # Agent 启动 context
```

## 文档索引

| 文档 | 位置 |
|------|------|
| 系统全景（本文） | `fpms/docs/OVERVIEW.md` |
| 白皮书 V3.1 | `fpms/docs/FounderOS-WhitePaper-V3.1.md` |
| 知识系统需求 | `founderos/requirements/knowledge-system-v1.md` |
| 记忆系统 PRD | `fpms/docs/PRD-memory-v2.2.md` |
| 记忆架构 V1 | `fpms/docs/FounderOS-Memory-Architecture-V1.md` |
| CTO Agent | `agents/cto/` |
| 开发 SOP | `founderos/dev-sop.md` |
| 里程碑日志 | `reports/milestones/` |
