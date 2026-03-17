# Task 5: Implementer — tools.py + command_executor.py

实现 spine/tools.py 和 spine/command_executor.py，让 tests/test_tools.py 和 tests/test_command_executor.py 全部通过。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 铁律
- 严禁修改测试文件
- 先 read 测试文件理解预期行为

## 已有代码
- spine/schema.py: init_db
- spine/models.py: Node, Edge, ToolResult, CreateNodeInput, UpdateStatusInput, UpdateFieldInput
- spine/store.py: Store (全部 CRUD + transaction + outbox + graph queries)
- spine/validator.py: ValidationError, validate_status_transition, validate_dag_safety, validate_xor_constraint, validate_active_domain, validate_attach, validate_dependency
- spine/narrative.py: append_narrative, read_narrative

## tools.py 设计

### ToolHandler 类
```python
class ToolHandler:
    def __init__(self, store, narratives_dir):
        self.store = store
        self.narratives_dir = narratives_dir

    def handle(self, tool_name, params) -> ToolResult:
        handler = getattr(self, f"handle_{tool_name}", None)
        if not handler:
            return ToolResult(success=False, command_id="", error=f"Unknown tool: {tool_name}")
        return handler(params)
```

### 每个 handler 的模式
1. 从 params 取参数
2. 校验（通过 validator）
3. 写入（通过 store）
4. 写叙事（通过 narrative.append_narrative）
5. 返回 ToolResult

### handler 清单

**create_node**: CreateNodeInput 校验 → store.create_node → append_narrative → ToolResult(data={id, title, status, node_type})

**update_status**: UpdateStatusInput 校验 → validate_status_transition → store.update_node → append_narrative → ToolResult

**update_field**: UpdateFieldInput 校验 → store.update_node → append_narrative → ToolResult

**attach_node**: validate_attach → store.add_edge(parent) → store.update_node(parent_id=, is_root=False) → ToolResult

**detach_node**: store.remove_edge(parent) → store.update_node(parent_id=None) → ToolResult

**add_dependency**: validate_dependency → store.add_edge(depends_on) → ToolResult

**remove_dependency**: store.remove_edge(depends_on) → ToolResult

**append_log**: append_narrative → ToolResult

**unarchive**: store.update_node(archived_at=None, status_changed_at=now) → ToolResult

**set_persistent**: store.update_node(is_persistent=value) → ToolResult

**get_node**: store.get_node → ToolResult(data=node dict)

**search_nodes**: store.list_nodes(filters) → ToolResult(data={nodes: list})

## command_executor.py 设计

```python
class CommandExecutor:
    def __init__(self, store, narratives_dir=""):
        self.store = store
        self.handler = ToolHandler(store, narratives_dir)

    def execute(self, command_id, tool_name, params) -> ToolResult:
        # 1. 幂等检查
        existing = self.store._conn.execute(
            "SELECT result_json FROM recent_commands WHERE command_id = ?",
            (command_id,)
        ).fetchone()
        if existing:
            import json
            data = json.loads(existing[0])
            return ToolResult(**data)

        # 2. Pydantic 校验（写操作）
        # 3. 路由到 handler
        # 4. 记录到 recent_commands
        # 5. 返回结果
```

## 重要注意
- ToolResult.command_id 必须设置为传入的 command_id
- Pydantic 校验失败时返回 ToolResult(success=False, error=str(e), suggestion=...)
- ValidationError 捕获后返回 ToolResult(success=False, error=e.message, suggestion=e.suggestion)
- 读操作（get_node, search_nodes）不需要 Pydantic 校验和事务

## 验证
```bash
cd /Users/jeff/.openclaw/workspace/fpms
python3 -m pytest tests/test_tools.py tests/test_command_executor.py -v
```
