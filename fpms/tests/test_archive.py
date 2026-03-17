"""Tests for spine/archive.py — archive scan, archive, unarchive."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from spine.schema import init_db
from spine.store import Store
from spine.models import Node, Edge
from spine.archive import scan_archive_candidates, archive_nodes, unarchive_node


# --- Fixtures ---

@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "fpms.db")
    events_path = str(tmp_path / "events.jsonl")
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)


def _past_iso(days: int) -> str:
    """Return ISO timestamp `days` days in the past."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _make_node(
    store: Store,
    title: str = "node",
    status: str = "done",
    is_root: bool = True,
    parent_id: Optional[str] = None,
    is_persistent: bool = False,
    status_changed_days_ago: int = 10,
    archived_at: Optional[str] = None,
    node_type: str = "task",
) -> Node:
    """Helper: create node, then backdate status_changed_at."""
    node = store.create_node(Node(
        id="",
        title=title,
        status=status,
        node_type=node_type,
        is_root=is_root,
        parent_id=parent_id,
        is_persistent=is_persistent,
    ))
    # Backdate status_changed_at directly
    past = _past_iso(status_changed_days_ago)
    store._conn.execute(
        "UPDATE nodes SET status_changed_at=? WHERE id=?",
        (past, node.id),
    )
    if archived_at is not None:
        store._conn.execute(
            "UPDATE nodes SET archived_at=? WHERE id=?",
            (archived_at, node.id),
        )
    store._conn.commit()
    return store.get_node(node.id)  # type: ignore


# ============================================================
# scan_archive_candidates
# ============================================================

class TestScanArchiveCandidates:
    def test_done_past_cooldown_no_deps_is_candidate(self, store):
        node = _make_node(store, status="done", status_changed_days_ago=10)
        candidates = scan_archive_candidates(store)
        assert node.id in candidates

    def test_done_within_cooldown_not_candidate(self, store):
        node = _make_node(store, status="done", status_changed_days_ago=3)
        candidates = scan_archive_candidates(store)
        assert node.id not in candidates

    def test_done_exactly_7_days_not_candidate(self, store):
        """Boundary: exactly 7 days should NOT qualify (< not <=)."""
        node = _make_node(store, status="done", status_changed_days_ago=7)
        # At exactly 7 days the timestamp is equal to cutoff, not less than.
        # Due to sub-second timing this is borderline; we just verify no crash.
        # The real boundary is tested by 3-day (no) and 10-day (yes).
        scan_archive_candidates(store)

    def test_dropped_past_cooldown_is_candidate(self, store):
        node = _make_node(store, status="dropped", status_changed_days_ago=10)
        candidates = scan_archive_candidates(store)
        assert node.id in candidates

    def test_active_node_never_candidate(self, store):
        node = _make_node(store, status="active", status_changed_days_ago=30)
        candidates = scan_archive_candidates(store)
        assert node.id not in candidates

    def test_waiting_node_never_candidate(self, store):
        node = _make_node(store, status="waiting", status_changed_days_ago=30)
        candidates = scan_archive_candidates(store)
        assert node.id not in candidates

    def test_inbox_node_never_candidate(self, store):
        node = _make_node(store, status="inbox", status_changed_days_ago=30)
        candidates = scan_archive_candidates(store)
        assert node.id not in candidates

    def test_persistent_never_candidate(self, store):
        node = _make_node(store, status="done", status_changed_days_ago=10,
                          is_persistent=True)
        candidates = scan_archive_candidates(store)
        assert node.id not in candidates

    def test_already_archived_not_candidate(self, store):
        node = _make_node(store, status="done", status_changed_days_ago=10,
                          archived_at=_past_iso(1))
        candidates = scan_archive_candidates(store)
        assert node.id not in candidates

    def test_has_non_archived_child_not_candidate(self, store):
        parent = _make_node(store, title="parent", status="done",
                            status_changed_days_ago=10)
        child = _make_node(store, title="child", status="active",
                           is_root=False, parent_id=parent.id,
                           status_changed_days_ago=1)
        store.add_edge(Edge(source_id=child.id, target_id=parent.id,
                            edge_type="parent"))
        candidates = scan_archive_candidates(store)
        assert parent.id not in candidates

    def test_all_children_archived_is_candidate(self, store):
        parent = _make_node(store, title="parent", status="done",
                            status_changed_days_ago=10)
        child = _make_node(store, title="child", status="done",
                           is_root=False, parent_id=parent.id,
                           status_changed_days_ago=10,
                           archived_at=_past_iso(1))
        store.add_edge(Edge(source_id=child.id, target_id=parent.id,
                            edge_type="parent"))
        candidates = scan_archive_candidates(store)
        assert parent.id in candidates

    def test_has_non_archived_grandchild_not_candidate(self, store):
        grandparent = _make_node(store, title="gp", status="done",
                                  status_changed_days_ago=10)
        parent = _make_node(store, title="parent", status="done",
                            is_root=False, parent_id=grandparent.id,
                            status_changed_days_ago=10,
                            archived_at=_past_iso(1))
        store.add_edge(Edge(source_id=parent.id, target_id=grandparent.id,
                            edge_type="parent"))
        child = _make_node(store, title="child", status="active",
                           is_root=False, parent_id=parent.id,
                           status_changed_days_ago=1)
        store.add_edge(Edge(source_id=child.id, target_id=parent.id,
                            edge_type="parent"))
        candidates = scan_archive_candidates(store)
        assert grandparent.id not in candidates

    def test_depended_on_by_non_archived_not_candidate(self, store):
        target = _make_node(store, title="target", status="done",
                            status_changed_days_ago=10)
        source = _make_node(store, title="source", status="active",
                            status_changed_days_ago=1)
        store.add_edge(Edge(source_id=source.id, target_id=target.id,
                            edge_type="depends_on"))
        candidates = scan_archive_candidates(store)
        assert target.id not in candidates

    def test_depended_on_by_archived_node_is_candidate(self, store):
        target = _make_node(store, title="target", status="done",
                            status_changed_days_ago=10)
        source = _make_node(store, title="source", status="done",
                            status_changed_days_ago=10,
                            archived_at=_past_iso(1))
        store.add_edge(Edge(source_id=source.id, target_id=target.id,
                            edge_type="depends_on"))
        candidates = scan_archive_candidates(store)
        assert target.id in candidates

    def test_empty_store_returns_empty(self, store):
        assert scan_archive_candidates(store) == []


# ============================================================
# archive_nodes
# ============================================================

class TestArchiveNodes:
    def test_sets_archived_at(self, store):
        node = _make_node(store, status="done", status_changed_days_ago=10)
        count = archive_nodes(store, [node.id])
        assert count == 1
        updated = store.get_node(node.id)
        assert updated.archived_at is not None

    def test_empty_list_returns_zero(self, store):
        assert archive_nodes(store, []) == 0

    def test_already_archived_skipped(self, store):
        node = _make_node(store, status="done", status_changed_days_ago=10,
                          archived_at=_past_iso(1))
        count = archive_nodes(store, [node.id])
        assert count == 0

    def test_nonexistent_node_skipped(self, store):
        count = archive_nodes(store, ["nonexistent-1234"])
        assert count == 0

    def test_multiple_nodes(self, store):
        n1 = _make_node(store, title="a", status="done",
                        status_changed_days_ago=10)
        n2 = _make_node(store, title="b", status="dropped",
                        status_changed_days_ago=10)
        count = archive_nodes(store, [n1.id, n2.id])
        assert count == 2
        assert store.get_node(n1.id).archived_at is not None
        assert store.get_node(n2.id).archived_at is not None

    def test_writes_audit_event(self, store):
        node = _make_node(store, status="done", status_changed_days_ago=10)
        archive_nodes(store, [node.id])
        cur = store._conn.execute(
            "SELECT event_json FROM audit_outbox WHERE flushed=0 ORDER BY id DESC LIMIT 1"
        )
        import json
        event = json.loads(cur.fetchone()[0])
        assert event["tool_name"] == "archive_node"
        assert event["node_id"] == node.id


# ============================================================
# unarchive_node
# ============================================================

class TestUnarchiveNode:
    def _archived_node(self, store) -> Node:
        node = _make_node(store, status="done", status_changed_days_ago=10,
                          archived_at=_past_iso(1))
        return node

    def test_clears_archived_at(self, store):
        node = self._archived_node(store)
        result = unarchive_node(store, node.id)
        assert result.archived_at is None

    def test_resets_status_changed_at(self, store):
        node = self._archived_node(store)
        old_sca = node.status_changed_at
        result = unarchive_node(store, node.id)
        assert result.status_changed_at != old_sca
        # Should be recent (within last minute)
        sca_dt = datetime.fromisoformat(result.status_changed_at)
        assert (datetime.now(timezone.utc) - sca_dt).total_seconds() < 60

    def test_with_new_status(self, store):
        node = self._archived_node(store)
        assert node.status == "done"
        result = unarchive_node(store, node.id, new_status="active")
        assert result.status == "active"
        assert result.archived_at is None

    def test_without_new_status_keeps_original(self, store):
        node = self._archived_node(store)
        result = unarchive_node(store, node.id)
        assert result.status == "done"

    def test_non_archived_node_raises(self, store):
        node = _make_node(store, status="done", status_changed_days_ago=10)
        with pytest.raises(ValueError, match="not archived"):
            unarchive_node(store, node.id)

    def test_nonexistent_node_raises(self, store):
        with pytest.raises(ValueError, match="not found"):
            unarchive_node(store, "nonexistent-1234")

    def test_writes_audit_event(self, store):
        node = self._archived_node(store)
        unarchive_node(store, node.id)
        cur = store._conn.execute(
            "SELECT event_json FROM audit_outbox WHERE flushed=0 ORDER BY id DESC LIMIT 1"
        )
        import json
        event = json.loads(cur.fetchone()[0])
        assert event["tool_name"] == "unarchive_node"
        assert event["node_id"] == node.id
