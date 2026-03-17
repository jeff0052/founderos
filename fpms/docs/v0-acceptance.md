# FPMS v0 验收清单

v0 目标：证明写入、校验、恢复能稳定工作。

验收通过标准：**全部 checkbox 打勾，零 FAIL。**

---

## 第 1 层：铁律测试（Invariant Tests）

系统不可违背的不变量。一条不过 = v0 不通过。

- [x] **DAG 永不成环** — parent 环、depends_on 环、跨维度环均被拒绝
- [x] **XOR 互斥** — is_root=True 且 parent_id≠None 永不共存
- [x] **原子提交** — facts + audit_outbox 在同一事务，崩溃后无半提交
- [x] **状态机合法** — 所有非法迁移被拒绝，合法迁移全部通过
- [x] **归档热区隔离** — attach/dependency 目标不可以是已归档节点
- [x] **派生层隔离** — 写路径代码中无任何 derived_*/cache 表的读取
- [x] **幂等** — 相同 command_id 重复调用返回相同结果，不产生重复数据

```
运行命令: pytest tests/invariants/ -v
结果: 62 passed in 0.45s ✅
```

---

## 第 2 层：单元测试

每个模块的功能正确性。

### schema.py + models.py
- [x] SQLite 建表成功，所有 CHECK 约束生效
- [x] nodes 表 status CHECK 约束拒绝非法值
- [x] nodes 表 XOR CHECK（is_root=1 AND parent_id IS NOT NULL → 拒绝）
- [x] audit_outbox 表存在且结构正确
- [x] recent_commands 表存在且结构正确
- [x] WAL 模式已启用
- [x] Pydantic CreateNodeInput 类型强转正确（"true" → True）
- [x] Pydantic CreateNodeInput 非法 node_type 拒绝 + 清晰报错
- [x] Pydantic UpdateStatusInput 非法 status 拒绝
- [x] Pydantic deadline 非 ISO8601 格式拒绝 + 示例提示

### narrative.py
- [x] append_narrative 追加格式 `## {timestamp} [{event_type}]\n{content}`
- [x] append_narrative 不覆盖已有内容（append-only 验证）
- [x] read_narrative 按条数截取（last_n_entries）
- [x] read_narrative 按天数截取（since_days）
- [x] read_compressed / write_compressed 正确读写
- [x] write_repair_event 写入修复记录
- [x] 目标文件不存在时自动创建目录和文件

### store.py
- [x] create_node 写入 DB + audit_outbox（同一事务内）
- [x] get_node 存在/不存在
- [x] update_node 更新字段 + updated_at 自动刷新
- [x] list_nodes 按 status/node_type/parent_id 过滤
- [x] list_nodes 分页（limit + offset）
- [x] add_edge / remove_edge 正确
- [x] get_edges 按方向（outgoing/incoming/both）
- [x] get_children / get_parent / get_dependencies / get_dependents / get_siblings
- [x] get_ancestors 递归向上正确
- [x] get_descendants 递归向下正确
- [x] `with store.transaction():` 正常 commit
- [x] `with store.transaction():` 异常自动 rollback，无脏数据
- [x] write_event 写入 audit_outbox
- [x] flush_events 从 outbox 写入 events.jsonl + 标记 flushed=1
- [x] session_state get/set 正确
- [x] command_id 幂等：相同 id 返回上次结果

### validator.py
- [x] inbox→active 合法
- [x] inbox→active 缺 summary → 拒绝 + actionable suggestion
- [x] inbox→active 缺 parent_id 且非 root → 拒绝
- [x] active→done 合法（无子节点）
- [x] active→done 有活跃子节点 → 拒绝 + 列出子节点
- [x] active→dropped 有活跃子节点 → 允许 + warning
- [x] done→active 缺 reason → 拒绝
- [x] dropped→inbox 缺 reason → 拒绝
- [x] done→waiting → 拒绝（非法迁移）
- [x] DAG parent 环路 → 拒绝
- [x] DAG depends_on 环路 → 拒绝
- [x] DAG 跨维度死锁（child depends_on ancestor）→ 拒绝
- [x] XOR: is_root=True + parent_id≠None → 拒绝
- [x] 活跃域: attach 到已归档节点 → 拒绝
- [x] 自依赖: node depends_on 自己 → 拒绝
- [x] 所有 ValidationError 包含 code + message + suggestion

### tools.py
- [x] create_node: 正常创建 → 返回 Node + event_id
- [x] create_node: Pydantic 校验失败 → 拒绝 + 详细报错
- [x] update_status: 合法迁移 → 成功
- [x] update_status: 非法迁移 → 拒绝 + actionable error
- [x] update_status(is_root=true): 自动清除 parent_id
- [x] update_field: 正常更新
- [x] update_field: 禁止字段 → 拒绝
- [x] attach_node: 正常挂载
- [x] attach_node: 已有 parent → 原子替换（detach old + attach new）
- [x] attach_node: 归档目标 → 拒绝
- [x] attach_node: 会造成环 → 拒绝
- [x] detach_node: 正常脱离
- [x] add_dependency: 正常
- [x] add_dependency: 自依赖 → 拒绝
- [x] add_dependency: 环路 → 拒绝
- [x] add_dependency: 归档目标 → 拒绝
- [x] remove_dependency: 正常
- [x] append_log: 正常追加 narrative
- [x] unarchive: status_changed_at 刷新为 NOW()
- [x] unarchive(new_status=): 原子解封 + 状态迁移
- [x] set_persistent: 设置/取消
- [x] shift_focus: 切换焦点
- [x] expand_context: 扩展
- [x] get_node: 存在/不存在
- [x] search_nodes: 按 status/parent_id 过滤 + 分页
- [x] 幂等: 相同 command_id → 返回相同结果

```
运行命令: pytest tests/ --ignore=tests/invariants/ -q
结果: 408 passed in 2.55s ✅
```

---

## 第 3 层：端到端冒烟测试

模拟真实使用场景，跨模块验证。

### 场景 A：基本生命周期
- [x] 创建 goal 节点（is_root=true）
- [x] 创建 project 节点，attach 到 goal
- [x] 创建 task 节点，attach 到 project
- [x] 三层树结构正确（get_children 验证）
- [x] task: inbox → active（补 summary 后）
- [x] task: active → done
- [x] project: inbox → active → done（task 已终态后）
- [x] goal: inbox → active → done（project 已终态后）

### 场景 B：依赖与阻塞
- [x] 创建 task-A 和 task-B
- [x] task-B depends_on task-A
- [x] task-B 在 task-A 未完成时 blocked=True
- [x] task-A → done 后 task-B 不再 blocked
- [x] 尝试反向依赖 task-A depends_on task-B → 环路拒绝

### 场景 C：状态回退
- [x] task → done → active（带 reason）
- [x] task → dropped → inbox（带 reason）

### 场景 D：归档边界
- [x] unarchive 节点 → status_changed_at = NOW()
- [x] attach 到已归档节点 → 拒绝
- [x] add_dependency 到已归档节点 → 拒绝

### 场景 E：审计完整性
- [x] 全部操作后 audit_outbox 有对应记录
- [x] flush_events → events.jsonl 行数 ≥ 操作次数
- [x] events.jsonl 每行可 JSON parse
- [x] 每条 event 包含 tool_name + timestamp

### 场景 F：幂等与崩溃
- [x] 用相同 command_id 调用 create_node 两次 → 只创建一个节点

### 场景 G：Actionable Errors
- [x] 触发至少 3 种不同的 ValidationError
- [x] 每个 error 都包含 suggestion 或 actionable message

```
运行命令: pytest tests/test_acceptance_e2e.py tests/test_e2e_smoke.py -v
结果: 18 passed ✅
```

---

## 第 4 层：PRD 附录 7 对照

### 拓扑安全
- [x] 新增 parent 前执行全息 DAG 查环
- [x] 新增 depends_on 前执行全息 DAG 查环
- [x] 跨维度死锁（child depends_on ancestor）被拒绝
- [x] 不存在的 node_id 引用被拒绝
- [x] attach 自动处理旧 parent 的 detach
- [x] archive 条件检查包含"无活跃后代"

### 写入一致性
- [x] 事实写入和审计日志在同一事务
- [x] Narrative 写入失败不回滚事实
- [x] 无 delete_node（只有 dropped → archive）
- [x] 所有 Tool 写入产生可重放的 event

### 状态引擎
- [x] inbox→active 需要 summary + (parent OR root)
- [x] →done 需要所有子节点终态
- [x] done→active 必须带 reason
- [x] dropped→inbox 必须带 reason

---

## 验收结果

```
总测试: 480 passed in 3.13s
  铁律测试:  62 passed (7 不变量文件)
  单元测试: 408 passed (16 模块)
  E2E测试:  18 passed (7 场景)
  零 FAIL
```

- [x] **v0 验收通过** — 日期: 2026-03-17 — 执行者: Agent (Opus)
