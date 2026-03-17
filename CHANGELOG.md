# CHANGELOG — FounderOS

## v0.3.0 (2026-03-18)
**Constitution Guard — 三道物理防线**

### 新增
- AST Float Scanner：检测支付路径中的 float 使用（Constitution §13）
- Ironclad Test Lock：SHA-256 防止铁律测试被篡改（Constitution §5）
- Core Path Gate：标记支付核心路径变更需 Founder 审批（Constitution §3）
- constitution_guard CLI：统一入口（check / update-hashes / status）
- CODE-REVIEW-STANDARD.md：P0-P3 分级审查标准
- GIT-WORKFLOW.md：分支策略 + commit 规范
- CTO Agent SOUL.md：架构可见性 + 代码可读性标准

### 修复
- S1: recovery.py bundle.assemble() 位置参数错误 → 改为关键字参数
- S2: validator.py 每次校验新开 DB 连接 → 复用 store._conn
- S3: store.py get_connection() 不建表 → 改为 init_db()

### 测试
- Constitution Guard：34 tests
- FPMS bug fix：5 new regression tests
- 总计：533 tests, 全绿

---

## v0.2.0 (2026-03-18)
**CTO Agent 体系完成**

### 新增
- CTO Agent workspace（agents/cto/）
  - SOUL.md：Build + Protect + Simplify
  - AGENTS.md：Phase -1 到 Phase 5 + FPMS 自动更新
  - CONSTITUTION.md：22 条铁律
  - MEMORY.md：CTO Agent 持久记忆
  - repos.md：代码库清单
- FounderOS WhitePaper V3.1（十步闭环）
- Memory Architecture V1（五层模型）
- OVERVIEW.md：系统全局入口
- GitHub repo：jeff0052/founderos (Private)

### 完善
- Phase -1 Feasibility Check 流程
- Kill Criteria 强制要求
- Complexity Budget（Constitution #21）
- "能删就不加"（Constitution #22）
- CTO Agent 三层方法论：FounderOS + CDRE + Superpowers

---

## v0.1.0 (2026-03-17)
**FPMS v1 完成**

### 新增
- FPMS 分形项目管理系统 v1
- 16 模块，3034 LOC
- 494 tests / 494 passed / 3.39s
- OpenClaw 集成（spine.py CLI）
- Dashboard（GitHub Pages）

### 模块
store, tools, validator, dashboard, focus, bundle, compression,
heartbeat, models, command_executor, archive, narrative, rollup,
recovery, risk, schema
