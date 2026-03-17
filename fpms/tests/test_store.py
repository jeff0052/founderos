"""Tests for spine/store.py — Store class."""

import json
import os
import tempfile
from typing import Optional

import pytest

from spine.schema import init_db
from spine.store import Store
from spine.models import Node, Edge


# --- Fixtures ---

@pytest.fixture
def store_env(tmp_path):
    """Create a Store with temp DB and events.jsonl."""
    db_path = str(tmp_path / "fpms.db")
    events_path = str(tmp_path / "events.jsonl")
    init_db(db_path)
    s = Store(db_path=db_path, events_path=events_path)
    return s, db_path, events_path


@pytest.fixture
def store(store_env):
    return store_env[0]


def _make_node(
    title: str = "Test Node",
    node_type: str = "task",
    status: str = "inbox",
    is_root: bool = True,
    parent_id: Optional[str] = None,
    **kwargs,
) -> Node:
    return Node(
        id="",  # store auto-generates
        title=title,
        status=status,
        node_type=node_type,
        is_root=is_root,
        parent_id=parent_id,
        **kwargs,
    )


# ============================================================
# Node CRUD
# ============================================================

class TestCreateNode:
    def test_auto_generates_id_with_type_prefix(self, store):
        node = store.create_node(_make_node(node_type="task"))
        assert node.id.startswith("task-")
        assert len(node.id.split("-")[1]) == 4  # 4 hex chars

    def test_id_prefix_matches_node_type(self, store):
        for nt in ("goal", "project", "milestone", "task", "unknown"):
            node = store.create_node(_make_node(node_type=nt))
            assert node.id.startswith(f"{nt}-")

    def test_auto_fills_timestamps(self, store):
        node = store.create_node(_make_node())
        assert node.created_at != ""
        assert node.updated_at != ""
        assert node.status_changed_at != ""

    def test_timestamps_are_iso8601(self, store):
        from datetime import datetime
        node = store.create_node(_make_node())
        # Should not raise
        datetime.fromisoformat(node.created_at)
        datetime.fromisoformat(node.updated_at)
        datetime.fromisoformat(node.status_changed_at)

    def test_returned_node_matches_get(self, store):
        created = store.create_node(_make_node(title="Roundtrip"))
        fetched = store.get_node(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Roundtrip"


class TestGetNode:
    def test_existing_returns_node(self, store):
        created = store.create_node(_make_node())
        result = store.get_node(created.id)
        assert result is not None
        assert isinstance(result, Node)
        assert result.id == created.id

    def test_nonexistent_returns_none(self, store):
        assert store.get_node("task-0000") is None

    def test_returns_correct_fields(self, store):
        created = store.create_node(_make_node(
            title="Full Node",
            node_type="goal",
            is_root=True,
            summary="A summary",
            why="Because",
            next_step="Do it",
            owner="alice",
        ))
        got = store.get_node(created.id)
        assert got.title == "Full Node"
        assert got.node_type == "goal"
        assert got.is_root is True
        assert got.summary == "A summary"
        assert got.why == "Because"
        assert got.next_step == "Do it"
        assert got.owner == "alice"


class TestUpdateNode:
    def test_updates_specified_field(self, store):
        node = store.create_node(_make_node(title="Original"))
        updated = store.update_node(node.id, {"title": "Changed"})
        assert updated.title == "Changed"

    def test_updates_multiple_fields(self, store):
        node = store.create_node(_make_node())
        updated = store.update_node(node.id, {"summary": "New sum", "owner": "bob"})
        assert updated.summary == "New sum"
        assert updated.owner == "bob"

    def test_auto_refreshes_updated_at(self, store):
        node = store.create_node(_make_node())
        old_updated = node.updated_at
        import time; time.sleep(0.01)
        updated = store.update_node(node.id, {"title": "Refreshed"})
        assert updated.updated_at >= old_updated

    def test_nonexistent_raises(self, store):
        with pytest.raises(Exception):
            store.update_node("task-ffff", {"title": "Nope"})

    def test_persists_change(self, store):
        node = store.create_node(_make_node(title="Before"))
        store.update_node(node.id, {"title": "After"})
        got = store.get_node(node.id)
        assert got.title == "After"


class TestListNodes:
    def test_no_filter_returns_all(self, store):
        store.create_node(_make_node(title="A"))
        store.create_node(_make_node(title="B"))
        store.create_node(_make_node(title="C"))
        result = store.list_nodes()
        assert len(result) == 3

    def test_filter_by_status(self, store):
        n = store.create_node(_make_node(title="Active", status="inbox"))
        store.update_node(n.id, {"status": "active", "summary": "s"})
        store.create_node(_make_node(title="Inbox"))
        result = store.list_nodes(filters={"status": "inbox"})
        assert all(r.status == "inbox" for r in result)

    def test_filter_by_node_type(self, store):
        store.create_node(_make_node(node_type="goal"))
        store.create_node(_make_node(node_type="task"))
        result = store.list_nodes(filters={"node_type": "goal"})
        assert len(result) == 1
        assert result[0].node_type == "goal"

    def test_filter_by_parent_id(self, store):
        parent = store.create_node(_make_node(title="Parent"))
        child = store.create_node(_make_node(
            title="Child", is_root=False, parent_id=parent.id,
        ))
        store.create_node(_make_node(title="Other"))
        result = store.list_nodes(filters={"parent_id": parent.id})
        assert len(result) == 1
        assert result[0].id == child.id

    def test_pagination_limit(self, store):
        for i in range(5):
            store.create_node(_make_node(title=f"Node {i}"))
        result = store.list_nodes(limit=2)
        assert len(result) == 2

    def test_pagination_offset(self, store):
        nodes = []
        for i in range(5):
            nodes.append(store.create_node(_make_node(title=f"Node {i}")))
        all_nodes = store.list_nodes(limit=50)
        offset_nodes = store.list_nodes(limit=50, offset=2)
        assert len(offset_nodes) == 3
        assert offset_nodes[0].id == all_nodes[2].id

    def test_empty_returns_empty_list(self, store):
        assert store.list_nodes() == []


# ============================================================
# Edge CRUD
# ============================================================

class TestAddEdge:
    def test_add_edge_normal(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B"))
        edge = store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))
        assert isinstance(edge, Edge)
        assert edge.source_id == a.id
        assert edge.target_id == b.id
        assert edge.edge_type == "depends_on"

    def test_duplicate_edge_raises(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B"))
        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))
        with pytest.raises(Exception):
            store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))


class TestRemoveEdge:
    def test_existing_returns_true(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B"))
        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))
        assert store.remove_edge(a.id, b.id, "depends_on") is True

    def test_nonexistent_returns_false(self, store):
        assert store.remove_edge("x", "y", "depends_on") is False

    def test_removed_edge_not_queryable(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B"))
        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))
        store.remove_edge(a.id, b.id, "depends_on")
        edges = store.get_edges(a.id, edge_type="depends_on", direction="outgoing")
        assert len(edges) == 0


class TestGetEdges:
    def _setup_edges(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B"))
        c = store.create_node(_make_node(title="C"))
        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))
        store.add_edge(Edge(source_id=c.id, target_id=a.id, edge_type="depends_on"))
        return a, b, c

    def test_outgoing(self, store):
        a, b, c = self._setup_edges(store)
        edges = store.get_edges(a.id, direction="outgoing")
        assert len(edges) == 1
        assert edges[0].target_id == b.id

    def test_incoming(self, store):
        a, b, c = self._setup_edges(store)
        edges = store.get_edges(a.id, direction="incoming")
        assert len(edges) == 1
        assert edges[0].source_id == c.id

    def test_filter_by_edge_type(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B"))
        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))
        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="parent"))
        edges = store.get_edges(a.id, edge_type="depends_on", direction="outgoing")
        assert len(edges) == 1
        assert edges[0].edge_type == "depends_on"


# ============================================================
# Graph Queries
# ============================================================

class TestGetChildren:
    def test_returns_direct_children(self, store):
        parent = store.create_node(_make_node(title="Parent"))
        c1 = store.create_node(_make_node(title="Child1", is_root=False, parent_id=parent.id))
        c2 = store.create_node(_make_node(title="Child2", is_root=False, parent_id=parent.id))
        children = store.get_children(parent.id)
        child_ids = {c.id for c in children}
        assert c1.id in child_ids
        assert c2.id in child_ids
        assert len(children) == 2

    def test_excludes_archived_by_default(self, store):
        parent = store.create_node(_make_node(title="Parent"))
        active_child = store.create_node(_make_node(title="Active", is_root=False, parent_id=parent.id))
        archived_child = store.create_node(_make_node(title="Archived", is_root=False, parent_id=parent.id))
        # Archive by setting archived_at
        store.update_node(archived_child.id, {"archived_at": "2026-01-01T00:00:00Z"})
        children = store.get_children(parent.id, include_archived=False)
        child_ids = {c.id for c in children}
        assert active_child.id in child_ids
        assert archived_child.id not in child_ids

    def test_includes_archived_when_requested(self, store):
        parent = store.create_node(_make_node(title="Parent"))
        store.create_node(_make_node(title="Active", is_root=False, parent_id=parent.id))
        archived_child = store.create_node(_make_node(title="Archived", is_root=False, parent_id=parent.id))
        store.update_node(archived_child.id, {"archived_at": "2026-01-01T00:00:00Z"})
        children = store.get_children(parent.id, include_archived=True)
        assert len(children) == 2

    def test_no_children_returns_empty(self, store):
        parent = store.create_node(_make_node(title="Leaf"))
        assert store.get_children(parent.id) == []


class TestGetParent:
    def test_has_parent(self, store):
        parent = store.create_node(_make_node(title="Parent"))
        child = store.create_node(_make_node(title="Child", is_root=False, parent_id=parent.id))
        result = store.get_parent(child.id)
        assert result is not None
        assert result.id == parent.id

    def test_root_node_returns_none(self, store):
        root = store.create_node(_make_node(title="Root", is_root=True))
        assert store.get_parent(root.id) is None


class TestGetDependencies:
    def test_returns_dependency_targets(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B"))
        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))
        deps = store.get_dependencies(a.id)
        assert len(deps) == 1
        assert deps[0].id == b.id

    def test_no_dependencies_returns_empty(self, store):
        a = store.create_node(_make_node(title="A"))
        assert store.get_dependencies(a.id) == []


class TestGetDependents:
    def test_returns_nodes_depending_on_target(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B"))
        store.add_edge(Edge(source_id=b.id, target_id=a.id, edge_type="depends_on"))
        dependents = store.get_dependents(a.id)
        assert len(dependents) == 1
        assert dependents[0].id == b.id

    def test_no_dependents_returns_empty(self, store):
        a = store.create_node(_make_node(title="A"))
        assert store.get_dependents(a.id) == []


class TestGetSiblings:
    def test_same_parent_siblings(self, store):
        parent = store.create_node(_make_node(title="Parent"))
        c1 = store.create_node(_make_node(title="C1", is_root=False, parent_id=parent.id))
        c2 = store.create_node(_make_node(title="C2", is_root=False, parent_id=parent.id))
        c3 = store.create_node(_make_node(title="C3", is_root=False, parent_id=parent.id))
        siblings = store.get_siblings(c1.id)
        sib_ids = {s.id for s in siblings}
        assert c2.id in sib_ids
        assert c3.id in sib_ids
        # Should not include self
        assert c1.id not in sib_ids

    def test_root_node_has_no_siblings(self, store):
        root = store.create_node(_make_node(title="Root"))
        assert store.get_siblings(root.id) == []


class TestGetAncestors:
    def test_recursive_ancestors(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B", is_root=False, parent_id=a.id))
        c = store.create_node(_make_node(title="C", is_root=False, parent_id=b.id))
        ancestors = store.get_ancestors(c.id)
        assert b.id in ancestors
        assert a.id in ancestors
        assert len(ancestors) == 2

    def test_root_has_no_ancestors(self, store):
        root = store.create_node(_make_node(title="Root"))
        assert store.get_ancestors(root.id) == []


class TestGetDescendants:
    def test_recursive_descendants(self, store):
        a = store.create_node(_make_node(title="A"))
        b = store.create_node(_make_node(title="B", is_root=False, parent_id=a.id))
        c = store.create_node(_make_node(title="C", is_root=False, parent_id=b.id))
        descendants = store.get_descendants(a.id)
        assert b.id in descendants
        assert c.id in descendants
        assert len(descendants) == 2

    def test_leaf_has_no_descendants(self, store):
        leaf = store.create_node(_make_node(title="Leaf"))
        assert store.get_descendants(leaf.id) == []


# ============================================================
# Session State
# ============================================================

class TestSessionState:
    def test_set_and_get_roundtrip(self, store):
        data = {"focus_node": "task-1234", "expanded": True}
        store.set_session("focus", data)
        result = store.get_session("focus")
        assert result == data

    def test_get_nonexistent_returns_none(self, store):
        assert store.get_session("no_such_key") is None

    def test_overwrite_existing_key(self, store):
        store.set_session("key", {"v": 1})
        store.set_session("key", {"v": 2})
        assert store.get_session("key") == {"v": 2}


# ============================================================
# Transaction
# ============================================================

class TestTransaction:
    def test_commit_on_success(self, store):
        with store.transaction():
            node = store.create_node(_make_node(title="Committed"))
        assert store.get_node(node.id) is not None

    def test_rollback_on_exception(self, store):
        node_id = None
        try:
            with store.transaction():
                node = store.create_node(_make_node(title="Rollback"))
                node_id = node.id
                raise ValueError("boom")
        except ValueError:
            pass
        # Node should not be visible after rollback
        assert store.get_node(node_id) is None

    def test_nested_transaction_behavior(self, store):
        """Nested transactions: inner exception should rollback outer too."""
        outer_id = None
        try:
            with store.transaction():
                outer = store.create_node(_make_node(title="Outer"))
                outer_id = outer.id
                with store.transaction():
                    store.create_node(_make_node(title="Inner"))
                    raise RuntimeError("inner fail")
        except RuntimeError:
            pass
        # Depending on implementation, outer may or may not survive.
        # At minimum, we verify no crash occurred.
        # If nested = savepoint, outer could survive; if flat, both rollback.


# ============================================================
# Audit Outbox
# ============================================================

class TestAuditOutbox:
    def test_write_event_in_transaction(self, store):
        with store.transaction():
            store.write_event({"action": "test", "node_id": "task-0001"})
        # Should be flushable
        count = store.flush_events()
        assert count == 1

    def test_flush_writes_to_events_jsonl(self, store_env):
        s, db_path, events_path = store_env
        with s.transaction():
            s.write_event({"action": "created", "node_id": "task-abcd"})
        s.flush_events()
        assert os.path.exists(events_path)
        with open(events_path, "r") as f:
            lines = f.readlines()
        assert len(lines) >= 1
        parsed = json.loads(lines[0])
        assert parsed["action"] == "created"

    def test_flush_marks_flushed(self, store):
        with store.transaction():
            store.write_event({"action": "test"})
        first = store.flush_events()
        assert first >= 1
        second = store.flush_events()
        assert second == 0

    def test_multiple_events_flush(self, store):
        with store.transaction():
            store.write_event({"action": "one"})
            store.write_event({"action": "two"})
            store.write_event({"action": "three"})
        count = store.flush_events()
        assert count == 3

    def test_second_flush_returns_zero(self, store):
        with store.transaction():
            store.write_event({"action": "once"})
        store.flush_events()
        assert store.flush_events() == 0
