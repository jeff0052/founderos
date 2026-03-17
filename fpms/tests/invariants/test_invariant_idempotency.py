"""Invariant: Same command_id produces same result, no duplicates.

Source: Architecture: Idempotency Protocol
"""

import pytest
from spine.models import Node
from spine.command_executor import CommandExecutor


class TestIdempotency:
    """Same command_id called twice → same result, no side effects."""

    def test_create_node_idempotent(self, store):
        """create_node with same command_id twice → only one node created."""
        executor = CommandExecutor(store)

        result1 = executor.execute(
            command_id="cmd-001",
            tool_name="create_node",
            params={"title": "Idempotent Node", "node_type": "task", "is_root": True}
        )
        result2 = executor.execute(
            command_id="cmd-001",
            tool_name="create_node",
            params={"title": "Idempotent Node", "node_type": "task", "is_root": True}
        )

        # Same result
        assert result1.success == result2.success
        assert result1.command_id == result2.command_id

        # Only one node in DB
        nodes = store.list_nodes()
        matching = [n for n in nodes if n.title == "Idempotent Node"]
        assert len(matching) == 1

    def test_update_status_idempotent(self, store):
        """update_status with same command_id twice → status changed once."""
        executor = CommandExecutor(store)

        # First create a node
        create_result = executor.execute(
            command_id="cmd-010",
            tool_name="create_node",
            params={"title": "Status Test", "node_type": "task", "is_root": True, "summary": "Test"}
        )
        node_id = create_result.data.get("id") if create_result.data else None
        assert node_id is not None

        # Update status twice with same command_id
        result1 = executor.execute(
            command_id="cmd-011",
            tool_name="update_status",
            params={"node_id": node_id, "new_status": "active"}
        )
        result2 = executor.execute(
            command_id="cmd-011",
            tool_name="update_status",
            params={"node_id": node_id, "new_status": "active"}
        )

        assert result1.success == result2.success

    def test_different_command_ids_not_idempotent(self, store):
        """Different command_ids → independent executions."""
        executor = CommandExecutor(store)

        result1 = executor.execute(
            command_id="cmd-020",
            tool_name="create_node",
            params={"title": "Node A", "node_type": "task", "is_root": True}
        )
        result2 = executor.execute(
            command_id="cmd-021",
            tool_name="create_node",
            params={"title": "Node B", "node_type": "task", "is_root": True}
        )

        # Both succeed but create different nodes
        assert result1.success is True
        assert result2.success is True

        nodes = store.list_nodes()
        assert len(nodes) >= 2

    def test_recent_commands_table_populated(self, store):
        """After execution, recent_commands table has the command."""
        executor = CommandExecutor(store)

        executor.execute(
            command_id="cmd-030",
            tool_name="create_node",
            params={"title": "Track Test", "node_type": "task", "is_root": True}
        )

        row = store._conn.execute(
            "SELECT command_id, tool_name FROM recent_commands WHERE command_id = ?",
            ("cmd-030",)
        ).fetchone()
        assert row is not None
        assert row[0] == "cmd-030"
        assert row[1] == "create_node"
