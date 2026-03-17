# Task 1: Test Writer — schema.py + models.py

你是测试工程师。为 schema.py 和 models.py 编写测试。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 接口签名

### schema.py
```python
def init_db(db_path: str) -> sqlite3.Connection:
    """创建/打开 SQLite 数据库，建表，启用 WAL 模式。"""

def get_connection(db_path: str) -> sqlite3.Connection:
    """获取已初始化的数据库连接。"""
```

### models.py（Pydantic 输入模型）
```python
class CreateNodeInput(BaseModel):
    title: str
    node_type: str = "unknown"  # goal|project|milestone|task|unknown
    parent_id: Optional[str] = None
    is_root: bool = False
    summary, why, next_step, owner, deadline: Optional[str]
    # Validators: node_type in allowed set, deadline ISO8601

class UpdateStatusInput(BaseModel):
    node_id: str
    new_status: str  # inbox|active|waiting|done|dropped
    reason: Optional[str] = None
    is_root: Optional[bool] = None

class UpdateFieldInput(BaseModel):
    node_id: str
    field: str  # title|summary|why|next_step|owner|deadline|node_type
    value: Optional[str] = None
```

### SQLite 表结构
```sql
nodes (id, title, status, node_type, is_root, parent_id, summary, why, next_step, owner, deadline, is_persistent, created_at, updated_at, status_changed_at, archived_at)
edges (source_id, target_id, edge_type, created_at) PK(source_id, target_id, edge_type)
session_state (key, value, updated_at)
audit_outbox (id autoincrement, event_json, created_at, flushed)
recent_commands (command_id, tool_name, result_json, created_at, expires_at)
```

## 测试要点

### test_schema.py
- init_db 创建所有 5 张表
- WAL 模式启用
- nodes.status CHECK 约束拒绝非法值
- nodes.node_type CHECK 约束拒绝非法值
- nodes XOR CHECK (is_root=1 AND parent_id IS NOT NULL → 拒绝)
- edges PK 约束防重复
- 重复调用 init_db 不报错（IF NOT EXISTS）
- get_connection 返回有效连接

### test_models.py
- CreateNodeInput 正常输入通过
- CreateNodeInput 类型强转（"true" → True for is_root）
- CreateNodeInput 非法 node_type → ValueError
- CreateNodeInput 非法 deadline 格式 → ValueError + 示例提示
- UpdateStatusInput 非法 status → ValueError
- UpdateFieldInput 非法 field → ValueError
- Node dataclass 字段完整（16 个字段）
- Edge dataclass 字段完整
- ToolResult 字段完整（含 command_id, event_id, warnings）

## 约束
- 只输出 tests/test_schema.py 和 tests/test_models.py
- 不写任何实现代码
- 使用 pytest + tempfile 创建临时 DB
