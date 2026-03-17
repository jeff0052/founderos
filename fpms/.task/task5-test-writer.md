# Task 5: Test Writer — tools.py + command_executor.py

你是测试工程师。为 tools.py 和 command_executor.py 编写测试。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 已有代码（全部已实现）
- spine/schema.py: init_db
- spine/models.py: Node, Edge, ToolResult, CreateNodeInput, UpdateStatusInput, UpdateFieldInput
- spine/store.py: Store (CRUD + tx + outbox + graph queries)
- spine/validator.py: ValidationError, validate_*
- spine/narrative.py: append_narrative, read_narrative, etc.

## 接口签名

### command_executor.py
```python
class CommandExecutor:
    def __init__(self, store: Store): ...
    def execute(self, command_id: str, tool_name: str, params: dict) -> ToolResult:
        """
        1. 幂等: command_id 已存在 → 返回上次结果
        2. Pydantic 校验（写操作）
        3. 路由到 ToolHandler
        4. 同一事务: facts + audit_outbox + recent_commands
        5. Post-commit: narrative + flush
        """
```

### tools.py
```python
class ToolHandler:
    def __init__(self, store, validator_module, narrative_module, ...): ...
    def handle(self, tool_name: str, params: dict) -> ToolResult: ...

    # Write tools
    def handle_create_node(self, params) -> ToolResult: ...
    def handle_update_status(self, params) -> ToolResult: ...
    def handle_update_field(self, params) -> ToolResult: ...
    def handle_attach_node(self, params) -> ToolResult: ...
    def handle_detach_node(self, params) -> ToolResult: ...
    def handle_add_dependency(self, params) -> ToolResult: ...
    def handle_remove_dependency(self, params) -> ToolResult: ...
    def handle_append_log(self, params) -> ToolResult: ...
    def handle_unarchive(self, params) -> ToolResult: ...
    def handle_set_persistent(self, params) -> ToolResult: ...

    # Read tools
    def handle_get_node(self, params) -> ToolResult: ...
    def handle_search_nodes(self, params) -> ToolResult: ...
```

## 测试文件结构

### tests/test_command_executor.py
- 幂等: 同 command_id 调两次，只创建一个节点
- 不同 command_id 独立执行
- Pydantic 校验失败返回 ToolResult(success=False, error=...)
- recent_commands 表记录执行
- 事务内异常回滚（不留脏数据）
- 未知 tool_name → 错误

### tests/test_tools.py
- create_node: 正常创建 → ToolResult(success=True, data={'id':..., 'status': 'inbox'})
- create_node: 自动生成 narrative 条目
- update_status: inbox→active（有 summary + root）→ 成功
- update_status: inbox→active 缺 summary → ToolResult(success=False, suggestion=...)
- update_status: 非法迁移 inbox→done → 失败
- update_field: 更新 summary → 成功
- update_field: 非法字段 → 失败
- attach_node: 正常挂载 → child.parent_id 更新 + is_root 清除
- attach_node: 归档目标 → 失败
- detach_node: 正常脱离 → parent_id 清除
- add_dependency: 正常 → 成功
- add_dependency: 环路 → 失败 + actionable error
- remove_dependency: 正常 → 成功
- append_log: 写入叙事 → 成功
- unarchive: 归档节点解封 → archived_at 清除 + status_changed_at 刷新
- set_persistent: 设 is_persistent=True → 成功
- get_node: 存在 → data 含完整字段
- get_node: 不存在 → success=False
- search_nodes: 按 status 搜索 → 返回匹配列表

## conftest.py fixture
```python
@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    from spine.schema import init_db
    init_db(db_path)
    from spine.store import Store
    return Store(db_path=db_path, events_path=events_path)

@pytest.fixture
def narratives_dir(tmp_path):
    d = tmp_path / "narratives"
    d.mkdir()
    return str(d)
```

## 约束
- 只输出 tests/test_tools.py 和 tests/test_command_executor.py
- 不写实现代码
- 不 mock — 用真实 Store
