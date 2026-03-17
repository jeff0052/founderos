"""Tests for spine/tools.py — ToolHandler."""

import os
from typing import Optional

import pytest

from spine.schema import init_db
from spine.store import Store
from spine.models import Node, Edge
from spine import validator as validator_module
from spine import narrative as narrative_module
from spine.tools import ToolHandler


# --- Fixtures ---

@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)


@pytest.fixture
def narratives_dir(tmp_path):
    d = tmp_path / "narratives"
    d.mkdir()
    return str(d)


@pytest.fixture
def handler(store, narratives_dir):
    """Create a ToolHandler with real dependencies."""
    # Import optional modules; pass None if not needed for test
    try:
        from spine import risk as risk_module
    except ImportError:
        risk_module = None
    try:
        from spine import rollup as rollup_module
    except ImportError:
        rollup_module = None
    try:
        from spine import dashboard as dashboard_module
    except ImportError:
        dashboard_module = None

    return ToolHandler(
        store=store,
        validator_module=validator_module,
        narrative_module=narrative_module,
        risk_module=risk_module,
        rollup_module=rollup_module,
        dashboard_module=dashboard_module,
    )


def _make_root_node(handler, title: str = "Root Goal", **kwargs) -> str:
    """Helper: create a root node, return its id."""
    params = {"title": title, "is_root": True, "node_type": "goal"}
    params.update(kwargs)
    result = handler.handle("create_node", params)
    assert result.success, f"Failed to create root node: {result.error}"
    return result.data["id"]


def _make_child_node(handler, parent_id: str, title: str = "Child Task",
                     **kwargs) -> str:
    """Helper: create a child node, return its id."""
    params = {"title": title, "parent_id": parent_id, "node_type": "task"}
    params.update(kwargs)
    result = handler.handle("create_node", params)
    assert result.success, f"Failed to create child node: {result.error}"
    return result.data["id"]


# ============================================================
# create_node
# ============================================================

class TestCreateNode:
    def test_create_root_node(self, handler):
        result = handler.handle("create_node", {
            "title": "My Goal",
            "node_type": "goal",
            "is_root": True,
        })
        assert result.success is True
        assert "id" in result.data
        assert result.data["status"] == "inbox"
        assert result.data["title"] == "My Goal"
        assert result.data["node_type"] == "goal"
        assert result.data["is_root"] is True

    def test_create_child_node(self, handler):
        root_id = _make_root_node(handler)
        result = handler.handle("create_node", {
            "title": "Sub-task",
            "node_type": "task",
            "parent_id": root_id,
        })
        assert result.success is True
        assert result.data["parent_id"] == root_id
        assert result.data["is_root"] is False

    def test_create_node_generates_narrative(self, handler, narratives_dir):
        result = handler.handle("create_node", {
            "title": "Narrated Node",
            "is_root": True,
        })
        assert result.success is True
        node_id = result.data["id"]
        # Narrative file should exist for the created node
        narrative_path = os.path.join(narratives_dir, f"{node_id}.md")
        assert os.path.exists(narrative_path), \
            f"Expected narrative file at {narrative_path}"
        content = open(narrative_path).read()
        assert "create" in content.lower() or "Narrated Node" in content

    def test_create_node_missing_title(self, handler):
        result = handler.handle("create_node", {
            "is_root": True,
        })
        assert result.success is False
        assert result.error is not None


# ============================================================
# update_status
# ============================================================

class TestUpdateStatus:
    def test_inbox_to_active_with_summary_and_root(self, handler):
        node_id = _make_root_node(handler, summary="Has summary")
        result = handler.handle("update_status", {
            "node_id": node_id,
            "new_status": "active",
        })
        assert result.success is True
        assert result.data["status"] == "active"

    def test_inbox_to_active_missing_summary(self, handler):
        node_id = _make_root_node(handler)
        result = handler.handle("update_status", {
            "node_id": node_id,
            "new_status": "active",
        })
        assert result.success is False
        assert result.suggestion is not None
        # Suggestion should tell LLM how to fix
        assert "summary" in result.suggestion.lower() or "update_field" in result.suggestion

    def test_illegal_transition_inbox_to_done(self, handler):
        node_id = _make_root_node(handler)
        result = handler.handle("update_status", {
            "node_id": node_id,
            "new_status": "done",
        })
        assert result.success is False
        assert result.error is not None

    def test_active_to_done(self, handler):
        node_id = _make_root_node(handler, summary="Ready")
        # inbox -> active
        handler.handle("update_status", {
            "node_id": node_id,
            "new_status": "active",
        })
        # active -> done
        result = handler.handle("update_status", {
            "node_id": node_id,
            "new_status": "done",
        })
        assert result.success is True
        assert result.data["status"] == "done"

    def test_done_to_active_requires_reason(self, handler):
        node_id = _make_root_node(handler, summary="Ready")
        handler.handle("update_status", {
            "node_id": node_id, "new_status": "active",
        })
        handler.handle("update_status", {
            "node_id": node_id, "new_status": "done",
        })
        # done -> active without reason should fail
        result = handler.handle("update_status", {
            "node_id": node_id,
            "new_status": "active",
        })
        assert result.success is False

    def test_done_to_active_with_reason(self, handler):
        node_id = _make_root_node(handler, summary="Ready")
        handler.handle("update_status", {
            "node_id": node_id, "new_status": "active",
        })
        handler.handle("update_status", {
            "node_id": node_id, "new_status": "done",
        })
        result = handler.handle("update_status", {
            "node_id": node_id,
            "new_status": "active",
            "reason": "Reopening due to new requirements",
        })
        assert result.success is True
        assert result.data["status"] == "active"


# ============================================================
# update_field
# ============================================================

class TestUpdateField:
    def test_update_summary(self, handler):
        node_id = _make_root_node(handler)
        result = handler.handle("update_field", {
            "node_id": node_id,
            "field": "summary",
            "value": "New summary text",
        })
        assert result.success is True
        assert result.data["summary"] == "New summary text"

    def test_update_title(self, handler):
        node_id = _make_root_node(handler, title="Old Title")
        result = handler.handle("update_field", {
            "node_id": node_id,
            "field": "title",
            "value": "New Title",
        })
        assert result.success is True
        assert result.data["title"] == "New Title"

    def test_update_illegal_field(self, handler):
        node_id = _make_root_node(handler)
        result = handler.handle("update_field", {
            "node_id": node_id,
            "field": "status",  # status is not in allowed fields
            "value": "active",
        })
        assert result.success is False
        assert result.error is not None

    def test_update_field_nonexistent_node(self, handler):
        result = handler.handle("update_field", {
            "node_id": "nonexistent-0000",
            "field": "summary",
            "value": "test",
        })
        assert result.success is False


# ============================================================
# attach_node
# ============================================================

class TestAttachNode:
    def test_attach_normal(self, handler, store):
        root_id = _make_root_node(handler)
        orphan_id = _make_root_node(handler, title="Orphan")
        result = handler.handle("attach_node", {
            "node_id": orphan_id,
            "parent_id": root_id,
        })
        assert result.success is True
        # Verify parent_id updated
        node = store.get_node(orphan_id)
        assert node.parent_id == root_id
        assert node.is_root is False

    def test_attach_to_archived_target_fails(self, handler, store):
        root_id = _make_root_node(handler, summary="Ready")
        # Make root active then done so it can be archived
        handler.handle("update_status", {
            "node_id": root_id, "new_status": "active",
        })
        handler.handle("update_status", {
            "node_id": root_id, "new_status": "done",
        })
        # Manually archive the node
        with store.transaction():
            store.update_node(root_id, {"archived_at": "2026-01-01T00:00:00Z"})

        orphan_id = _make_root_node(handler, title="Orphan")
        result = handler.handle("attach_node", {
            "node_id": orphan_id,
            "parent_id": root_id,
        })
        assert result.success is False
        assert "archived" in result.error.lower() or "ARCHIVED" in result.error

    def test_attach_replaces_existing_parent(self, handler, store):
        """attach_node on node with existing parent → atomic replace."""
        root_a = _make_root_node(handler, title="Parent A")
        root_b = _make_root_node(handler, title="Parent B")
        child_id = _make_child_node(handler, root_a, title="Movable")
        assert store.get_node(child_id).parent_id == root_a

        result = handler.handle("attach_node", {
            "node_id": child_id,
            "parent_id": root_b,
        })
        assert result.success is True
        node = store.get_node(child_id)
        assert node.parent_id == root_b


# ============================================================
# detach_node
# ============================================================

class TestDetachNode:
    def test_detach_normal(self, handler, store):
        root_id = _make_root_node(handler)
        child_id = _make_child_node(handler, root_id)
        assert store.get_node(child_id).parent_id == root_id

        result = handler.handle("detach_node", {"node_id": child_id})
        assert result.success is True
        node = store.get_node(child_id)
        assert node.parent_id is None

    def test_detach_node_without_parent(self, handler):
        root_id = _make_root_node(handler)
        result = handler.handle("detach_node", {"node_id": root_id})
        # Should either succeed (no-op) or fail gracefully
        # Either way, it should not crash
        assert isinstance(result.success, bool)


# ============================================================
# add_dependency
# ============================================================

class TestAddDependency:
    def test_add_dependency_normal(self, handler):
        a_id = _make_root_node(handler, title="Task A")
        b_id = _make_root_node(handler, title="Task B")
        result = handler.handle("add_dependency", {
            "source_id": a_id,
            "target_id": b_id,
        })
        assert result.success is True

    def test_add_dependency_cycle_fails(self, handler):
        a_id = _make_root_node(handler, title="Task A")
        b_id = _make_root_node(handler, title="Task B")
        # A depends on B
        handler.handle("add_dependency", {
            "source_id": a_id, "target_id": b_id,
        })
        # B depends on A → cycle
        result = handler.handle("add_dependency", {
            "source_id": b_id,
            "target_id": a_id,
        })
        assert result.success is False
        assert result.error is not None
        # Should include actionable suggestion
        assert result.suggestion is not None or "cycle" in result.error.lower()

    def test_add_dependency_self_fails(self, handler):
        a_id = _make_root_node(handler)
        result = handler.handle("add_dependency", {
            "source_id": a_id,
            "target_id": a_id,
        })
        assert result.success is False


# ============================================================
# remove_dependency
# ============================================================

class TestRemoveDependency:
    def test_remove_dependency_normal(self, handler):
        a_id = _make_root_node(handler, title="Task A")
        b_id = _make_root_node(handler, title="Task B")
        handler.handle("add_dependency", {
            "source_id": a_id, "target_id": b_id,
        })
        result = handler.handle("remove_dependency", {
            "source_id": a_id,
            "target_id": b_id,
        })
        assert result.success is True

    def test_remove_nonexistent_dependency(self, handler):
        a_id = _make_root_node(handler, title="Task A")
        b_id = _make_root_node(handler, title="Task B")
        result = handler.handle("remove_dependency", {
            "source_id": a_id,
            "target_id": b_id,
        })
        # Should either fail or succeed as no-op
        assert isinstance(result.success, bool)


# ============================================================
# append_log
# ============================================================

class TestAppendLog:
    def test_append_log_success(self, handler, narratives_dir):
        node_id = _make_root_node(handler)
        result = handler.handle("append_log", {
            "node_id": node_id,
            "content": "Did some work today",
        })
        assert result.success is True
        # Verify narrative file was written
        narrative_path = os.path.join(narratives_dir, f"{node_id}.md")
        assert os.path.exists(narrative_path)
        content = open(narrative_path).read()
        assert "Did some work today" in content

    def test_append_log_nonexistent_node(self, handler):
        result = handler.handle("append_log", {
            "node_id": "nonexistent-0000",
            "content": "Ghost log",
        })
        assert result.success is False


# ============================================================
# unarchive
# ============================================================

class TestUnarchive:
    def test_unarchive_clears_archived_at(self, handler, store):
        node_id = _make_root_node(handler, summary="Ready")
        handler.handle("update_status", {
            "node_id": node_id, "new_status": "active",
        })
        handler.handle("update_status", {
            "node_id": node_id, "new_status": "done",
        })
        # Manually archive
        with store.transaction():
            store.update_node(node_id, {"archived_at": "2026-01-01T00:00:00Z"})

        result = handler.handle("unarchive", {"node_id": node_id})
        assert result.success is True
        node = store.get_node(node_id)
        assert node.archived_at is None

    def test_unarchive_refreshes_status_changed_at(self, handler, store):
        node_id = _make_root_node(handler, summary="Ready")
        handler.handle("update_status", {
            "node_id": node_id, "new_status": "active",
        })
        handler.handle("update_status", {
            "node_id": node_id, "new_status": "done",
        })
        with store.transaction():
            store.update_node(node_id, {
                "archived_at": "2026-01-01T00:00:00Z",
                "status_changed_at": "2025-01-01T00:00:00Z",
            })
        old_sca = store.get_node(node_id).status_changed_at

        handler.handle("unarchive", {"node_id": node_id})
        node = store.get_node(node_id)
        assert node.status_changed_at != old_sca
        assert node.status_changed_at > old_sca

    def test_unarchive_non_archived_node(self, handler):
        node_id = _make_root_node(handler)
        result = handler.handle("unarchive", {"node_id": node_id})
        # Should fail or no-op since node is not archived
        assert isinstance(result.success, bool)


# ============================================================
# set_persistent
# ============================================================

class TestSetPersistent:
    def test_set_persistent_true(self, handler, store):
        node_id = _make_root_node(handler)
        result = handler.handle("set_persistent", {
            "node_id": node_id,
            "is_persistent": True,
        })
        assert result.success is True
        node = store.get_node(node_id)
        assert node.is_persistent is True

    def test_set_persistent_false(self, handler, store):
        node_id = _make_root_node(handler)
        handler.handle("set_persistent", {
            "node_id": node_id, "is_persistent": True,
        })
        result = handler.handle("set_persistent", {
            "node_id": node_id,
            "is_persistent": False,
        })
        assert result.success is True
        node = store.get_node(node_id)
        assert node.is_persistent is False


# ============================================================
# get_node
# ============================================================

class TestGetNode:
    def test_get_existing_node(self, handler):
        node_id = _make_root_node(handler, title="Findable")
        result = handler.handle("get_node", {"node_id": node_id})
        assert result.success is True
        assert result.data["id"] == node_id
        assert result.data["title"] == "Findable"
        # Should contain all core fields
        for field in ("status", "node_type", "is_root", "created_at", "updated_at"):
            assert field in result.data

    def test_get_nonexistent_node(self, handler):
        result = handler.handle("get_node", {"node_id": "nonexistent-ffff"})
        assert result.success is False


# ============================================================
# search_nodes
# ============================================================

class TestSearchNodes:
    def test_search_by_status(self, handler):
        _make_root_node(handler, title="Node A")
        _make_root_node(handler, title="Node B")
        result = handler.handle("search_nodes", {"status": "inbox"})
        assert result.success is True
        assert isinstance(result.data, (list, dict))
        # Both nodes are inbox by default
        if isinstance(result.data, list):
            assert len(result.data) >= 2
        elif isinstance(result.data, dict) and "nodes" in result.data:
            assert len(result.data["nodes"]) >= 2

    def test_search_by_parent_id(self, handler):
        root_id = _make_root_node(handler)
        _make_child_node(handler, root_id, title="Child 1")
        _make_child_node(handler, root_id, title="Child 2")
        result = handler.handle("search_nodes", {"parent_id": root_id})
        assert result.success is True
        if isinstance(result.data, list):
            assert len(result.data) == 2
        elif isinstance(result.data, dict) and "nodes" in result.data:
            assert len(result.data["nodes"]) == 2

    def test_search_empty_result(self, handler):
        result = handler.handle("search_nodes", {"status": "done"})
        assert result.success is True
        if isinstance(result.data, list):
            assert len(result.data) == 0
        elif isinstance(result.data, dict) and "nodes" in result.data:
            assert len(result.data["nodes"]) == 0

    def test_search_pagination(self, handler):
        root_id = _make_root_node(handler)
        for i in range(5):
            _make_child_node(handler, root_id, title=f"Task {i}")
        result = handler.handle("search_nodes", {
            "parent_id": root_id,
            "limit": 2,
            "offset": 0,
        })
        assert result.success is True
        if isinstance(result.data, list):
            assert len(result.data) == 2
        elif isinstance(result.data, dict) and "nodes" in result.data:
            assert len(result.data["nodes"]) == 2


# ============================================================
# handle routing
# ============================================================

class TestHandleRouting:
    def test_unknown_tool_name(self, handler):
        result = handler.handle("nonexistent_tool", {})
        assert result.success is False
        assert result.error is not None
