"""Tests for spine/command_executor.py — CommandExecutor."""

import json
from typing import Optional

import pytest

from spine.schema import init_db
from spine.store import Store
from spine.models import Node, ToolResult
from spine.command_executor import CommandExecutor


# --- Fixtures ---

@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)


@pytest.fixture
def executor(store):
    return CommandExecutor(store=store)


# ============================================================
# Idempotency
# ============================================================

class TestIdempotency:
    def test_same_command_id_returns_cached_result(self, executor, store):
        """同 command_id 调两次，只创建一个节点。"""
        result1 = executor.execute("cmd-001", "create_node", {
            "title": "Idempotent Node",
            "is_root": True,
        })
        assert result1.success is True
        node_id = result1.data["id"]

        result2 = executor.execute("cmd-001", "create_node", {
            "title": "Idempotent Node",
            "is_root": True,
        })
        assert result2.success is True
        assert result2.data["id"] == node_id

        # Verify only one node was actually created
        nodes = store.list_nodes(filters={"is_root": True})
        matching = [n for n in nodes if n.title == "Idempotent Node"]
        assert len(matching) == 1

    def test_different_command_ids_execute_independently(self, executor, store):
        """不同 command_id 独立执行。"""
        result1 = executor.execute("cmd-aaa", "create_node", {
            "title": "Node A",
            "is_root": True,
        })
        result2 = executor.execute("cmd-bbb", "create_node", {
            "title": "Node B",
            "is_root": True,
        })
        assert result1.success is True
        assert result2.success is True
        assert result1.data["id"] != result2.data["id"]

        nodes = store.list_nodes(filters={"is_root": True})
        titles = {n.title for n in nodes}
        assert "Node A" in titles
        assert "Node B" in titles


# ============================================================
# Pydantic Validation
# ============================================================

class TestPydanticValidation:
    def test_invalid_node_type_fails(self, executor):
        """Pydantic 校验失败返回 ToolResult(success=False)。"""
        result = executor.execute("cmd-bad-type", "create_node", {
            "title": "Bad Type",
            "node_type": "invalid_type",
            "is_root": True,
        })
        assert result.success is False
        assert result.error is not None

    def test_invalid_status_fails(self, executor):
        # First create a valid node
        r = executor.execute("cmd-setup", "create_node", {
            "title": "Test Node",
            "is_root": True,
        })
        node_id = r.data["id"]

        result = executor.execute("cmd-bad-status", "update_status", {
            "node_id": node_id,
            "new_status": "invalid_status",
        })
        assert result.success is False
        assert result.error is not None

    def test_invalid_field_name_fails(self, executor):
        r = executor.execute("cmd-setup-2", "create_node", {
            "title": "Test Node",
            "is_root": True,
        })
        node_id = r.data["id"]

        result = executor.execute("cmd-bad-field", "update_field", {
            "node_id": node_id,
            "field": "status",  # not in allowed fields
            "value": "active",
        })
        assert result.success is False

    def test_missing_required_title_fails(self, executor):
        result = executor.execute("cmd-no-title", "create_node", {
            "is_root": True,
        })
        assert result.success is False
        assert result.error is not None

    def test_invalid_deadline_format_fails(self, executor):
        result = executor.execute("cmd-bad-deadline", "create_node", {
            "title": "Bad Deadline",
            "is_root": True,
            "deadline": "next-tuesday",
        })
        assert result.success is False


# ============================================================
# recent_commands table
# ============================================================

class TestRecentCommands:
    def test_recent_commands_recorded(self, executor, store):
        """recent_commands 表记录执行。"""
        executor.execute("cmd-track-001", "create_node", {
            "title": "Tracked Node",
            "is_root": True,
        })
        # Check recent_commands table directly
        cur = store._conn.execute(
            "SELECT command_id, tool_name, result_json FROM recent_commands WHERE command_id=?",
            ("cmd-track-001",),
        )
        row = cur.fetchone()
        assert row is not None
        assert row["command_id"] == "cmd-track-001"
        assert row["tool_name"] == "create_node"
        result_data = json.loads(row["result_json"])
        assert result_data["success"] is True

    def test_failed_command_also_recorded(self, executor, store):
        """即使失败也记录到 recent_commands（用于幂等重放）。"""
        executor.execute("cmd-fail-001", "create_node", {
            "title": "Bad",
            "node_type": "invalid_type",
            "is_root": True,
        })
        cur = store._conn.execute(
            "SELECT command_id, result_json FROM recent_commands WHERE command_id=?",
            ("cmd-fail-001",),
        )
        row = cur.fetchone()
        assert row is not None
        result_data = json.loads(row["result_json"])
        assert result_data["success"] is False


# ============================================================
# Transaction rollback
# ============================================================

class TestTransactionSafety:
    def test_exception_rolls_back_no_dirty_data(self, executor, store):
        """事务内异常回滚，不留脏数据。"""
        # Count existing nodes
        before_count = len(store.list_nodes())

        # Trigger a validation error (inbox -> done is illegal)
        r = executor.execute("cmd-setup-tx", "create_node", {
            "title": "TX Test",
            "is_root": True,
        })
        node_id = r.data["id"]
        after_create_count = len(store.list_nodes())

        result = executor.execute("cmd-bad-transition", "update_status", {
            "node_id": node_id,
            "new_status": "done",  # illegal from inbox
        })
        assert result.success is False

        # No extra nodes should have been created by the failed command
        final_count = len(store.list_nodes())
        assert final_count == after_create_count


# ============================================================
# Unknown tool_name
# ============================================================

class TestUnknownTool:
    def test_unknown_tool_returns_error(self, executor):
        """未知 tool_name → 错误。"""
        result = executor.execute("cmd-unknown", "nonexistent_tool", {})
        assert result.success is False
        assert result.error is not None
        assert "nonexistent_tool" in result.error or "unknown" in result.error.lower()


# ============================================================
# Audit outbox
# ============================================================

class TestAuditOutbox:
    def test_write_produces_audit_event(self, executor, store):
        """Write tool produces an audit event in outbox."""
        executor.execute("cmd-audit-001", "create_node", {
            "title": "Audited Node",
            "is_root": True,
        })
        cur = store._conn.execute(
            "SELECT event_json FROM audit_outbox WHERE flushed=0"
        )
        rows = cur.fetchall()
        assert len(rows) >= 1
        # At least one event should reference create_node
        events = [json.loads(r["event_json"]) for r in rows]
        create_events = [
            e for e in events
            if e.get("tool_name") == "create_node"
            or e.get("event_type") == "create_node"
            or "create" in str(e).lower()
        ]
        assert len(create_events) >= 1

    def test_read_tool_no_audit_event(self, executor, store):
        """Read-only tools should not produce audit events."""
        r = executor.execute("cmd-create-for-read", "create_node", {
            "title": "Readable",
            "is_root": True,
        })
        node_id = r.data["id"]

        # Flush existing events
        store.flush_events()

        # Read-only operation
        executor.execute("cmd-read-001", "get_node", {"node_id": node_id})

        # No new unflushed audit events
        cur = store._conn.execute(
            "SELECT COUNT(*) as cnt FROM audit_outbox WHERE flushed=0"
        )
        count = cur.fetchone()["cnt"]
        assert count == 0


# ============================================================
# End-to-end: create + update through executor
# ============================================================

class TestEndToEnd:
    def test_create_then_update_status(self, executor):
        r1 = executor.execute("cmd-e2e-create", "create_node", {
            "title": "E2E Node",
            "is_root": True,
            "summary": "Has summary for activation",
        })
        assert r1.success is True
        node_id = r1.data["id"]

        r2 = executor.execute("cmd-e2e-activate", "update_status", {
            "node_id": node_id,
            "new_status": "active",
        })
        assert r2.success is True
        assert r2.data["status"] == "active"

    def test_create_then_search(self, executor):
        executor.execute("cmd-e2e-s1", "create_node", {
            "title": "Searchable A",
            "is_root": True,
        })
        executor.execute("cmd-e2e-s2", "create_node", {
            "title": "Searchable B",
            "is_root": True,
        })
        result = executor.execute("cmd-e2e-search", "search_nodes", {
            "status": "inbox",
        })
        assert result.success is True
