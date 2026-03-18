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

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    layer TEXT NOT NULL CHECK(layer IN ('fact','judgment','scratch')),
    sub_type TEXT CHECK(sub_type IS NULL OR sub_type IN ('preference','decision','lesson','pattern')),
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    node_id TEXT,
    based_on TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.8,
    verification TEXT NOT NULL CHECK(verification IN ('user_confirmed','system_verified','auto_extracted')),
    source TEXT NOT NULL CHECK(source IN ('auto','manual','system')),
    priority TEXT NOT NULL DEFAULT 'P1' CHECK(priority IN ('P0','P1','P2')),
    needs_review INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_accessed_at TEXT NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    conflict_count INTEGER NOT NULL DEFAULT 0,
    similar_to TEXT,
    archived_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_memories_layer ON memories(layer);
CREATE INDEX IF NOT EXISTS idx_memories_priority ON memories(priority);
CREATE INDEX IF NOT EXISTS idx_memories_verification ON memories(verification);
CREATE INDEX IF NOT EXISTS idx_memories_node_id ON memories(node_id);
CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);

CREATE TABLE IF NOT EXISTS memory_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('memory_created','memory_updated','memory_archived','memory_accessed','memory_promoted','memory_confirmed')),
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_events_memory_id ON memory_events(memory_id);
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
