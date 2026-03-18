# FounderOS — Claude Code 配置

## 项目概况
FounderOS: 创始人+AI 的公司操作系统。Python + SQLite 技术栈。

## 启动流程
1. 读 `agents/cto/SOUL.md` — 你的角色
2. 读 `agents/cto/CONSTITUTION.md` — 22 条铁律
3. 读 `fpms/docs/OVERVIEW.md` — 系统全景
4. 运行 `python3 fpms/spine.py bootstrap` — 加载项目看板

## gstack
Use /browse from gstack for all web browsing. Never use mcp__claude-in-chrome__* tools.

Available skills:
- /plan-eng-review — 工程方案审查（架构、测试、性能）
- /review — 代码审查（pre-landing PR review）
- /ship — 发版（测试、CHANGELOG、commit、push）
- /retro — 工程回顾统计
- /qa — QA 测试（需要 web app 时启用）
- /browse — 浏览器操控
- /plan-design-review — 设计审计
- /design-review — 设计审查 + 修复
- /design-consultation — 设计系统搭建
- /document-release — 文档更新

If gstack skills aren't working, run `cd .claude/skills/gstack && ./setup`

## 开发约束
- 所有写入通过 Tool Call，不直接碰 SQLite
- 测试先于实现（TDD）
- Constitution 铁律不可违反
- 任务状态更新到 FPMS
- commit message 格式: `type: 一句话描述`（feat/fix/refactor/docs/test）

## 技术栈
- Python 3.9+
- SQLite + WAL
- pytest
- Pydantic (input validation)

## 命令
```bash
python3 fpms/spine.py dashboard    # 看板
python3 fpms/spine.py bootstrap    # 启动 context
python3 fpms/spine.py heartbeat    # 心跳扫描
python3 fpms/spine.py tool <name> '<json>'  # 调用 MCP tool
pytest -x                          # 跑测试
```
