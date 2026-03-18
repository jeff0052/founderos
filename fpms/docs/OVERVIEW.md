# FounderOS — 系统全景

> 最后更新: 2026-03-18 v0.4.0 (6f92d3a)
> Jeff 的监督窗口：架构、进度、方向。具体任务状态看 FPMS。

---

## 一句话

FounderOS 让一个创始人+AI 管得住一家越来越复杂的公司。

## 架构

```
FounderOS
├── 灵魂（愿力）— VISION.md ✅, 白皮书 V3.1 ✅
├── 大脑（知识系统）
│   ├── 记忆层 ✅ 三层模型+事件溯源, 6 MCP Tools
│   ├── 信号检测 ❌ → Phase 1
│   ├── 关系图谱 ❌ → Phase 1
│   ├── 概念蒸馏 ❌ → Phase 1
│   └── 邮件采集 ❌ → Phase 1
├── 骨架（执行体系）
│   ├── FPMS ✅ 594 tests, 26 tools
│   └── CTO Agent ✅ Constitution 22条 + 执行引擎
├── 心脏（Jeff）✅
└── 经济模型 — 支付系统 📥
```

## 版本线

| 版本 | 日期 | 一句话 | tests |
|------|------|--------|-------|
| v0.1.0 | 3/17 | FPMS v1: 16模块 | 494 |
| v0.2.0 | 3/18 | CTO Agent 体系 | 494 |
| v0.3.0 | 3/18 | Constitution Guard | 533 |
| v0.3.1 | 3/18 | Memory Layer v1 | 576 |
| **v0.4.0** | **3/18** | **Memory Tools 接入路由** | **594** |

## 下一步

1. **固定开发 SOP** — 总分总循环，参考 gstack
2. **Phase 1 开发** — 信号检测 / 关系图谱 / 概念蒸馏 / 邮件采集
3. **CTO Agent 实例化** — 独立 session 执行开发任务

## 查看实时状态

```bash
python3 fpms/spine.py dashboard    # FPMS 看板（任务状态）
python3 fpms/spine.py bootstrap    # Agent 启动 context
```

## 文档索引

| 文档 | 位置 |
|------|------|
| 系统全景（本文） | `fpms/docs/OVERVIEW.md` |
| 白皮书 V3.1 | `fpms/docs/FounderOS-WhitePaper-V3.1.md` |
| 知识系统需求 | `founderos/requirements/knowledge-system-v1.md` |
| 记忆架构 V1 | `fpms/docs/FounderOS-Memory-Architecture-V1.md` |
| CTO Agent | `agents/cto/` |
| 里程碑日志 | `reports/milestones/` |
