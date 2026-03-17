# Task 1: Implementer — schema.py

实现 spine/schema.py，让 tests/test_schema.py 的所有测试通过。

## Python 版本
Python 3.9。不要用 `X | None`，用 `Optional[X]`。不要用 match/case。

## 铁律
- 严禁修改测试文件
- 严格遵循接口签名
- models.py 已经完成（Pydantic + dataclass），不要修改

## 需要实现的接口
```python
def init_db(db_path: str) -> sqlite3.Connection:
    """创建/打开 SQLite，建表，启用 WAL。表已存在则跳过。"""

def get_connection(db_path: str) -> sqlite3.Connection:
    """获取已初始化的连接。"""
```

## SQLite 表结构

```sql
-- nodes: 核心节点事实表
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'inbox' CHECK(status IN ('inbox','active','waiting','done','dropped')),
    node_type TEXT NOT NULL DEFAULT 'unknown' CHECK(node_type IN ('goal','project','milestone','task','unknown')),
    is_root INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    why TEXT,
    next_step TEXT,
    owner TEXT,
    deadline TEXT,
    is_persistent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status_changed_at TEXT NOT NULL,
    archived_at TEXT,
    parent_id TEXT REFERENCES nodes(id),
    CHECK(NOT (is_root = 1 AND parent_id IS NOT NULL))
);

-- edges: 关系边
CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT NOT NULL REFERENCES nodes(id),
    target_id TEXT NOT NULL REFERENCES nodes(id),
    edge_type TEXT NOT NULL CHECK(edge_type IN ('parent','depends_on')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (source_id, target_id, edge_type)
);

-- session_state: 运行时状态
CREATE TABLE IF NOT EXISTS session_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- audit_outbox: 审计发件箱
CREATE TABLE IF NOT EXISTS audit_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    flushed INTEGER NOT NULL DEFAULT 0
);

-- recent_commands: 幂等性
CREATE TABLE IF NOT EXISTS recent_commands (
    command_id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
```

## 要求
- init_db 启用 WAL 模式: `PRAGMA journal_mode=WAL`
- init_db 启用外键: `PRAGMA foreign_keys=ON`
- 幂等：重复调用不报错
- get_connection 内部缓存连接或每次新建都可以

## 验证
完成后运行: `cd /Users/jeff/.openclaw/workspace/fpms && python3 -m pytest tests/test_schema.py -v`
确保全部通过。
