# Task 3: Implementer — store.py + command_executor.py

实现 spine/store.py，让 tests/test_store.py 的所有测试通过。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 铁律
- 严禁修改测试文件
- 严格遵循 INTERFACES.md 的函数签名
- schema.py 和 models.py 已实现，直接 import 使用

## 已有代码
- spine/schema.py: init_db(db_path) → Connection, get_connection(db_path) → Connection
- spine/models.py: Node, Edge, ToolResult dataclasses

## 关键设计

### ID 生成
- 格式: `{node_type前缀}-{4位hex随机}`
- 前缀映射: goal→goal, project→proj, milestone→mile, task→task, unknown→node
- 冲突时重试

### 事务 Context Manager
```python
@contextmanager
def transaction(self):
    try:
        yield
        self._conn.commit()
    except:
        self._conn.rollback()
        raise
```

### Transactional Outbox
- write_event(event) → INSERT INTO audit_outbox (event_json, created_at, flushed) VALUES (json, now, 0)
- flush_events() → SELECT * FROM audit_outbox WHERE flushed=0 → append to events.jsonl → UPDATE flushed=1

### Graph Queries (递归)
- get_ancestors: 使用 WITH RECURSIVE CTE 递归查找所有祖先
- get_descendants: 使用 WITH RECURSIVE CTE 递归查找所有后代

### Node CRUD 注意
- create_node: node.id 为空字符串时自动生成
- create_node: 自动填充 created_at, updated_at, status_changed_at 为 UTC ISO8601
- update_node: 自动更新 updated_at
- update_node: node_id 不存在 raise ValueError
- list_nodes: filters 支持 status, node_type, parent_id, is_root, archived
- get_children: 通过 parent_id 字段查找（不通过 edges 表）

### parent_id 关系
parent_id 既存在于 nodes 表（字段）也存在于 edges 表（edge_type='parent'）。
- nodes.parent_id 是快捷查询字段
- edges parent 记录是完整关系图
- add_edge(type='parent') 时同步更新 nodes.parent_id
- remove_edge(type='parent') 时同步清除 nodes.parent_id

## 验证
完成后运行: `cd /Users/jeff/.openclaw/workspace/fpms && python3 -m pytest tests/test_store.py -v`
