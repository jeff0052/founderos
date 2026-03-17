# CTO Agent — 长期技术记忆

## 关键架构决策

### FPMS（2026-03-17）
- SQLite + WAL 作为 source of truth
- 所有写入通过 Tool Call，LLM 不直接碰存储
- DAG 拓扑 + 状态机 + 原子提交
- 眼球模型 L0/L1/L2 三级分辨率
- 494 测试全绿，16 模块，3034 LOC
- 当前通过 shell exec 接入 OpenClaw（草台），应升级为 MCP Server

## 技术栈

- FPMS: Python 3.9 + SQLite + Pydantic
- 测试: pytest
- 代码管理: 本地（未来 Git）

## 踩过的坑

### recovery.py import 命名（2026-03-17）
- 问题: test_recovery.py 用 `patch("spine.recovery.bundle.xxx")` 但 recovery.py 里 import 为 `_bundle`
- 解决: 统一命名，import 时不加下划线前缀
- 教训: mock patch 路径必须跟实际 import 名一致

## FounderOS 上下文

- 白皮书 V3.1: `fpms/docs/FounderOS-WhitePaper-V3.1.md`
- Memory Architecture: `fpms/docs/FounderOS-Memory-Architecture-V1.md`
- 系统全景: `fpms/docs/OVERVIEW.md`
- CTO PRD: `fpms/docs/CTO-AGENT-PRD-V2.md`
