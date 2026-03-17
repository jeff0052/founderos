# Git Workflow — FounderOS 版本控制标准

## 分支策略

```
main              ← 生产就绪，只接受 PR merge，永远可用
  └─ feat/xxx     ← 新功能（从 main 拉，完成后 PR 回 main）
  └─ fix/xxx      ← Bug 修复
  └─ refactor/xxx ← 重构
  └─ hotfix/xxx   ← 紧急修复（唯一允许加速审查的类型）
```

**规则：**
- 不允许直接 push main
- 每个 task 一个 branch，branch 名带 FPMS task ID：`feat/task-xxxx-description`
- 完成后提 PR，PR 描述必须包含：做了什么、为什么、FPMS task ID
- PR 通过 Code Review Standard 审查后 merge
- merge 后删除 feature branch

## Commit Message 格式

```
<type>(<scope>): <description>

[optional body]

[optional footer: FPMS task ID]
```

**Type（必须）：**
- `feat` — 新功能
- `fix` — Bug 修复
- `refactor` — 重构（不改行为）
- `docs` — 文档变更
- `test` — 测试变更
- `chore` — 构建/配置/工具

**Scope（建议）：**
- `fpms` — FPMS 引擎
- `cto` — CTO Agent
- `pay` — 支付系统
- `interceptor` — 拦截器

**示例：**
```
feat(fpms): add MCP Server transport layer

Replaces shell exec with standard MCP protocol.
FPMS: task-a489
```

## Tag / Release

```
vX.Y.Z

X = 大版本（架构级变更）
Y = 功能版本（新模块/新能力）
Z = 补丁版本（bug fix）
```

**里程碑必须打 tag：**
- v0.1.0 — FPMS v0 完成
- v0.2.0 — FPMS v1 + CTO Agent 体系
- v0.3.0 — Constitution Interceptors
- v1.0.0 — 支付系统 v1

## CTO Agent 开发流程中的 Git

```
Phase -1  → 在 main 上评估（不改代码）
Phase 0   → 在 main 上写 design doc（可直接 commit）
Phase 1   → 创建 feat/task-xxxx branch
Phase 2   → 在 branch 上写规约和测试
Phase 3   → spawn agents 在 branch 上实现
Phase 4   → PR → Code Review Standard 审查 → merge main
Phase 5   → 反馈循环更新规约（在 main 上）
```

## 保护规则（未来启用）

当项目复杂度增长时：
- [ ] main branch protection（需要 PR + review）
- [ ] CI 自动跑测试（PR 必须全绿）
- [ ] Constitution Interceptor 作为 CI gate
- [ ] 铁律测试文件 hash 校验
