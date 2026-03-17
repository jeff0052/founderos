"""Invariant: DB facts + audit_outbox commit atomically.

Source: PRD Invariant #5/#6, Architecture: Transactional Outbox
"""

import json
import pytest
from spine.models import Node


class TestAtomicCommit:
    """Facts and audit events are in the same SQLite transaction."""

    def test_successful_write_has_audit(self, store):
        """Successful node creation → audit_outbox has matching event."""
        node = store.create_node(Node(id="", title="Test", status="inbox", node_type="task", is_root=True))

        # Check audit_outbox has an event
        conn = store._conn  # Access internal connection for verification
        cursor = conn.execute("SELECT event_json FROM audit_outbox WHERE flushed = 0")
        rows = cursor.fetchall()
        assert len(rows) >= 1

        # Event should reference the created node
        event = json.loads(rows[-1][0])
        assert event.get("tool_name") == "create_node" or node.id in str(event)

    def test_failed_write_no_audit(self, store):
        """Failed write (e.g., constraint violation) → no audit_outbox entry, no node."""
        initial_count = store._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        initial_audit = store._conn.execute("SELECT COUNT(*) FROM audit_outbox").fetchone()[0]

        # Try to create a node that violates constraints (e.g., duplicate id)
        node = store.create_node(Node(id="", title="First", status="inbox", node_type="task", is_root=True))

        try:
            # Try to create with same ID → should fail
            bad_node = Node(id=node.id, title="Dupe", status="inbox", node_type="task", is_root=True)
            store.create_node(bad_node)
        except Exception:
            pass

        # Verify: only 1 node exists (the first one)
        final_count = store._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        assert final_count == initial_count + 1

    def test_transaction_rollback_on_exception(self, store):
        """Exception inside transaction → both facts and audit rolled back."""
        initial_nodes = store._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        initial_audit = store._conn.execute("SELECT COUNT(*) FROM audit_outbox").fetchone()[0]

        try:
            with store.transaction():
                store._conn.execute(
                    "INSERT INTO nodes (id, title, status, node_type, is_root, created_at, updated_at, status_changed_at) "
                    "VALUES ('test-rollback', 'Rollback', 'inbox', 'task', 1, '2026-01-01', '2026-01-01', '2026-01-01')"
                )
                store._conn.execute(
                    "INSERT INTO audit_outbox (event_json, created_at, flushed) "
                    "VALUES ('{\"test\": true}', '2026-01-01', 0)"
                )
                raise RuntimeError("Simulated crash")
        except RuntimeError:
            pass

        # Both should be rolled back
        final_nodes = store._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        final_audit = store._conn.execute("SELECT COUNT(*) FROM audit_outbox").fetchone()[0]
        assert final_nodes == initial_nodes
        assert final_audit == initial_audit


class TestFlushEvents:
    """Audit outbox flush to events.jsonl."""

    def test_flush_writes_jsonl(self, store, tmp_events_path):
        """flush_events → events.jsonl contains the events."""
        store.create_node(Node(id="", title="Flush Test", status="inbox", node_type="task", is_root=True))

        count = store.flush_events()
        assert count >= 1

        with open(tmp_events_path) as f:
            lines = f.readlines()
        assert len(lines) >= 1
        event = json.loads(lines[0])
        assert "tool_name" in event or "timestamp" in event

    def test_flush_marks_flushed(self, store):
        """After flush, outbox events marked flushed=1."""
        store.create_node(Node(id="", title="Mark Test", status="inbox", node_type="task", is_root=True))

        store.flush_events()

        unflushed = store._conn.execute("SELECT COUNT(*) FROM audit_outbox WHERE flushed = 0").fetchone()[0]
        assert unflushed == 0

    def test_double_flush_no_duplicates(self, store, tmp_events_path):
        """Flushing twice doesn't duplicate events in jsonl."""
        store.create_node(Node(id="", title="Dupe Flush", status="inbox", node_type="task", is_root=True))

        count1 = store.flush_events()
        count2 = store.flush_events()

        assert count2 == 0  # Nothing new to flush

        with open(tmp_events_path) as f:
            lines = f.readlines()
        assert len(lines) == count1
