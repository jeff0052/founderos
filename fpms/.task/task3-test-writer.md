# Task 3: Test Writer — store.py

你是测试工程师。为 store.py 编写测试。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 已有代码
- spine/schema.py 已实现（init_db 建表 + WAL）
- spine/models.py 已实现（Node, Edge, ToolResult dataclasses + Pydantic）

## 接口签名

```python
class Store:
    def __init__(self, db_path: str, events_path: str): ...

    # Node CRUD
    def create_node(self, node: Node) -> Node:
        """插入新节点。自动生成 id（格式: {node_type前缀}-{4位hex}）和 timestamps。"""
    def get_node(self, node_id: str) -> Optional[Node]: ...
    def update_node(self, node_id: str, fields: dict) -> Node:
        """更新指定字段。自动更新 updated_at。"""
    def list_nodes(self, filters: Optional[dict] = None, order_by: str = "updated_at",
                   limit: int = 50, offset: int = 0) -> list: ...

    # Edge CRUD
    def add_edge(self, edge: Edge) -> Edge: ...
    def remove_edge(self, source_id: str, target_id: str, edge_type: str) -> bool: ...
    def get_edges(self, node_id: str, edge_type: Optional[str] = None, direction: str = "outgoing") -> list: ...

    # Graph Queries
    def get_children(self, node_id: str, include_archived: bool = False) -> list: ...
    def get_parent(self, node_id: str) -> Optional[Node]: ...
    def get_dependencies(self, node_id: str) -> list: ...
    def get_dependents(self, node_id: str) -> list: ...
    def get_siblings(self, node_id: str) -> list: ...
    def get_ancestors(self, node_id: str) -> list:
        """递归向上，返回 node_id 列表。"""
    def get_descendants(self, node_id: str) -> list:
        """递归向下，返回 node_id 列表。"""

    # Session State
    def get_session(self, key: str) -> Optional[dict]: ...
    def set_session(self, key: str, value: dict) -> None: ...

    # Transaction (Context Manager)
    @contextmanager
    def transaction(self):
        """with store.transaction(): ... 成功 commit，异常 rollback。"""

    # Audit Outbox
    def write_event(self, event: dict) -> None:
        """写入 audit_outbox 表。必须在 transaction() 内。"""
    def flush_events(self) -> int:
        """outbox → events.jsonl。返回 flush 数。"""
```

## 测试要点

### Node CRUD
- create_node 自动生成 id（格式 {type前缀}-{4hex}）
- create_node 自动填充 created_at/updated_at/status_changed_at
- get_node 存在返回 Node / 不存在返回 None
- update_node 更新字段 + updated_at 自动刷新
- update_node 不存在的 node_id → 抛异常
- list_nodes 无 filter 返回所有
- list_nodes filter by status / node_type / parent_id
- list_nodes 分页 limit + offset

### Edge CRUD
- add_edge 正常添加
- add_edge 重复 → 报错（PK约束）
- remove_edge 存在 → True / 不存在 → False
- get_edges outgoing / incoming / both

### Graph Queries
- get_children 返回直接子节点
- get_children include_archived=False 排除归档
- get_parent 有 parent / 无 parent 返回 None
- get_dependencies / get_dependents 正确方向
- get_siblings 同 parent 的兄弟
- get_ancestors 递归（A→B→C，C 的 ancestors = [B, A]）
- get_descendants 递归

### Session State
- set_session + get_session roundtrip
- get_session 不存在 → None

### Transaction
- 正常 commit: 数据可见
- 异常 rollback: 数据不可见
- 嵌套调用行为

### Audit Outbox
- write_event 在事务内写入 audit_outbox
- flush_events → events.jsonl 文件有内容
- flush 后 flushed=1
- 二次 flush 返回 0（无新事件）

## 约束
- 只输出 tests/test_store.py
- 不写实现代码
- import from spine.schema import init_db 和 from spine.store import Store 和 from spine.models import Node, Edge
- 用 tempfile 创建临时 DB 和 events.jsonl
