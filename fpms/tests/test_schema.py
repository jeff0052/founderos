"""Tests for spine/schema.py — DB initialization, constraints, WAL mode."""

import os
import sqlite3
import tempfile

import pytest

from spine.schema import init_db, get_connection


@pytest.fixture
def tmp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


# ── init_db 基本行为 ──────────────────────────────────────────


class TestInitDB:
    """init_db creates all tables and enables WAL."""

    def test_creates_all_five_tables(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = sorted(row[0] for row in cursor.fetchall())
        expected = sorted([
            "audit_outbox",
            "edges",
            "nodes",
            "recent_commands",
            "session_state",
        ])
        assert tables == expected

    def test_wal_mode_enabled(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"

    def test_idempotent_double_init(self, tmp_db_path):
        """Calling init_db twice on the same DB should not raise."""
        conn1 = init_db(tmp_db_path)
        conn1.close()
        conn2 = init_db(tmp_db_path)
        tables = conn2.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        assert tables == 5
        conn2.close()


# ── nodes 约束 ────────────────────────────────────────────────


class TestNodesConstraints:
    """CHECK constraints on nodes table."""

    def _insert_node(self, conn, **overrides):
        defaults = dict(
            id="task-0001",
            title="test node",
            status="inbox",
            node_type="task",
            is_root=1,
            parent_id=None,
            summary=None,
            why=None,
            next_step=None,
            owner=None,
            deadline=None,
            is_persistent=0,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            status_changed_at="2026-01-01T00:00:00Z",
            archived_at=None,
        )
        defaults.update(overrides)
        cols = ", ".join(defaults.keys())
        placeholders = ", ".join(["?"] * len(defaults))
        conn.execute(
            f"INSERT INTO nodes ({cols}) VALUES ({placeholders})",
            list(defaults.values()),
        )

    def test_valid_status_accepted(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        for status in ("inbox", "active", "waiting", "done", "dropped"):
            self._insert_node(
                conn,
                id=f"task-{status}",
                status=status,
            )
        assert conn.execute("SELECT count(*) FROM nodes").fetchone()[0] == 5

    def test_invalid_status_rejected(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        with pytest.raises(sqlite3.IntegrityError):
            self._insert_node(conn, status="invalid_status")

    def test_valid_node_type_accepted(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        for i, nt in enumerate(("goal", "project", "milestone", "task", "unknown")):
            self._insert_node(
                conn,
                id=f"node-{i}",
                node_type=nt,
            )
        assert conn.execute("SELECT count(*) FROM nodes").fetchone()[0] == 5

    def test_invalid_node_type_rejected(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        with pytest.raises(sqlite3.IntegrityError):
            self._insert_node(conn, node_type="epic")

    def test_xor_both_root_and_parent_rejected(self, tmp_db_path):
        """is_root=1 AND parent_id IS NOT NULL must be rejected."""
        conn = init_db(tmp_db_path)
        with pytest.raises(sqlite3.IntegrityError):
            self._insert_node(conn, is_root=1, parent_id="goal-0001")

    def test_xor_root_without_parent_accepted(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        self._insert_node(conn, is_root=1, parent_id=None)
        assert conn.execute("SELECT count(*) FROM nodes").fetchone()[0] == 1

    def test_xor_non_root_with_parent_accepted(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        # Create parent first
        self._insert_node(conn, id="goal-0001", is_root=1, parent_id=None)
        self._insert_node(
            conn, id="task-0002", is_root=0, parent_id="goal-0001"
        )
        assert conn.execute("SELECT count(*) FROM nodes").fetchone()[0] == 2


# ── edges 约束 ────────────────────────────────────────────────


class TestEdgesConstraints:
    """PK constraint on edges table."""

    def test_duplicate_edge_rejected(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        conn.execute(
            "INSERT INTO edges (source_id, target_id, edge_type, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("a", "b", "parent", "2026-01-01T00:00:00Z"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (source_id, target_id, edge_type, created_at) "
                "VALUES (?, ?, ?, ?)",
                ("a", "b", "parent", "2026-01-01T00:00:00Z"),
            )

    def test_same_pair_different_type_accepted(self, tmp_db_path):
        conn = init_db(tmp_db_path)
        conn.execute(
            "INSERT INTO edges (source_id, target_id, edge_type, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("a", "b", "parent", "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO edges (source_id, target_id, edge_type, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("a", "b", "depends_on", "2026-01-01T00:00:00Z"),
        )
        assert conn.execute("SELECT count(*) FROM edges").fetchone()[0] == 2


# ── get_connection ────────────────────────────────────────────


class TestGetConnection:
    """get_connection returns a usable connection."""

    def test_returns_valid_connection(self, tmp_db_path):
        init_db(tmp_db_path)
        conn = get_connection(tmp_db_path)
        assert isinstance(conn, sqlite3.Connection)
        # Should be able to query tables
        tables = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        assert tables == 5
        conn.close()
