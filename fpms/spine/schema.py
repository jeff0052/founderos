"""SQLite schema initialization and migrations."""

import sqlite3

_TABLES_SQL = """
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

CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    edge_type TEXT NOT NULL CHECK(edge_type IN ('parent','depends_on')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (source_id, target_id, edge_type)
);

CREATE TABLE IF NOT EXISTS session_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_outbox (
    id INTEGER PRIMARY KEY,
    event_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    flushed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recent_commands (
    command_id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """创建/打开 SQLite 数据库，建表，启用 WAL 模式。
    如果表已存在则跳过。返回连接对象。"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_TABLES_SQL)
    return conn


def get_connection(db_path: str) -> sqlite3.Connection:
    """获取已初始化的数据库连接。"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
