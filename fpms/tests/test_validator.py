"""Tests for spine/validator.py — status transitions, DAG safety, XOR, active domain."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

import pytest

from spine.models import Node, Edge
from spine.schema import init_db
from spine.validator import (
    ValidationError,
    validate_active_domain,
    validate_attach,
    validate_dag_safety,
    validate_dependency,
    validate_status_transition,
    validate_xor_constraint,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    from spine.store import Store
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_node(
    id: str = "node-1",
    title: str = "Test",
    status: str = "inbox",
    node_type: str = "task",
    is_root: bool = False,
    parent_id: Optional[str] = None,
    summary: Optional[str] = None,
    archived_at: Optional[str] = None,
) -> Node:
    now = _now()
    return Node(
        id=id,
        title=title,
        status=status,
        node_type=node_type,
        is_root=is_root,
        parent_id=parent_id,
        summary=summary,
        archived_at=archived_at,
        created_at=now,
        updated_at=now,
        status_changed_at=now,
    )


# ---------------------------------------------------------------------------
# validate_status_transition — legal transitions
# ---------------------------------------------------------------------------

class TestStatusTransitionLegal:
    """All 9 legal transitions should pass without raising."""

    @pytest.mark.parametrize("current,target", [
        ("inbox", "active"),
        ("inbox", "waiting"),
        ("inbox", "dropped"),
        ("active", "waiting"),
        ("active", "done"),
        ("active", "dropped"),
        ("waiting", "active"),
        ("waiting", "done"),
        ("waiting", "dropped"),
    ])
    def test_legal_transitions(self, current, target):
        # inbox→active/waiting needs summary + parent_id/is_root
        node = _make_node(status=current, summary="has summary", parent_id="p-1")
        # For →done, supply no children (vacuously terminal)
        validate_status_transition(current, target, node, children=[])

    def test_done_to_active_legal(self):
        """done→active is legal (reason checked externally)."""
        node = _make_node(status="done", summary="s", parent_id="p-1")
        validate_status_transition("done", "active", node, children=[])

    def test_dropped_to_inbox_legal(self):
        """dropped→inbox is legal (reason checked externally)."""
        node = _make_node(status="dropped", summary="s", parent_id="p-1")
        validate_status_transition("dropped", "inbox", node, children=[])


# ---------------------------------------------------------------------------
# validate_status_transition — illegal transitions
# ---------------------------------------------------------------------------

class TestStatusTransitionIllegal:
    """All 7 illegal transitions should raise ValidationError."""

    @pytest.mark.parametrize("current,target", [
        ("inbox", "done"),
        ("done", "waiting"),
        ("done", "dropped"),
        ("done", "inbox"),
        ("dropped", "active"),
        ("dropped", "waiting"),
        ("dropped", "done"),
    ])
    def test_illegal_transitions(self, current, target):
        node = _make_node(status=current, summary="s", parent_id="p-1")
        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition(current, target, node, children=[])
        assert exc_info.value.code  # non-empty code


# ---------------------------------------------------------------------------
# validate_status_transition — precondition failures
# ---------------------------------------------------------------------------

class TestStatusTransitionPreconditions:

    def test_inbox_to_active_missing_summary(self):
        """inbox→active without summary → reject with actionable suggestion."""
        node = _make_node(status="inbox", summary=None, parent_id="p-1")
        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition("inbox", "active", node, children=[])
        err = exc_info.value
        assert err.code
        # suggestion should mention how to fix (update_field or summary)
        combined = (err.suggestion + " " + err.message).lower()
        assert "update_field" in combined or "summary" in combined

    def test_inbox_to_waiting_missing_summary(self):
        """inbox→waiting without summary → reject."""
        node = _make_node(status="inbox", summary=None, parent_id="p-1")
        with pytest.raises(ValidationError):
            validate_status_transition("inbox", "waiting", node, children=[])

    def test_inbox_to_active_missing_parent_and_not_root(self):
        """inbox→active with no parent_id and is_root=False → reject."""
        node = _make_node(status="inbox", summary="has summary",
                          parent_id=None, is_root=False)
        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition("inbox", "active", node, children=[])
        assert exc_info.value.code

    def test_inbox_to_active_is_root_no_parent_ok(self):
        """inbox→active with is_root=True and no parent → OK."""
        node = _make_node(status="inbox", summary="has summary",
                          parent_id=None, is_root=True)
        validate_status_transition("inbox", "active", node, children=[])

    def test_to_done_with_active_children_rejected(self):
        """→done with active children → reject, listing child info."""
        child_active = _make_node(id="c-1", status="active", summary="s", parent_id="node-1")
        child_done = _make_node(id="c-2", status="done", summary="s", parent_id="node-1")
        node = _make_node(status="active", summary="s", parent_id="p-1")
        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition("active", "done", node,
                                       children=[child_active, child_done])
        err = exc_info.value
        assert err.code
        # error should mention the non-terminal child
        assert "c-1" in err.message or "c-1" in err.suggestion

    def test_to_done_all_children_terminal_ok(self):
        """→done when all children are done/dropped → pass."""
        child_done = _make_node(id="c-1", status="done", summary="s", parent_id="node-1")
        child_dropped = _make_node(id="c-2", status="dropped", summary="s", parent_id="node-1")
        node = _make_node(status="active", summary="s", parent_id="p-1")
        validate_status_transition("active", "done", node,
                                   children=[child_done, child_dropped])

    def test_to_dropped_with_active_children_passes(self):
        """→dropped with active children → allowed (warning handled by caller)."""
        child_active = _make_node(id="c-1", status="active", summary="s", parent_id="node-1")
        node = _make_node(status="active", summary="s", parent_id="p-1")
        # Should NOT raise
        validate_status_transition("active", "dropped", node,
                                   children=[child_active])


# ---------------------------------------------------------------------------
# validate_xor_constraint
# ---------------------------------------------------------------------------

class TestXORConstraint:

    def test_root_no_parent_ok(self):
        validate_xor_constraint(is_root=True, parent_id=None)

    def test_not_root_with_parent_ok(self):
        validate_xor_constraint(is_root=False, parent_id="p-1")

    def test_not_root_no_parent_ok(self):
        """Both False/None is allowed (inbox node with no parent yet)."""
        validate_xor_constraint(is_root=False, parent_id=None)

    def test_root_with_parent_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_xor_constraint(is_root=True, parent_id="p-1")
        assert exc_info.value.code


# ---------------------------------------------------------------------------
# validate_active_domain
# ---------------------------------------------------------------------------

class TestActiveDomain:

    def test_non_archived_ok(self):
        node = _make_node(archived_at=None)
        validate_active_domain(node)

    def test_archived_rejected(self):
        node = _make_node(archived_at="2026-01-01T00:00:00Z")
        with pytest.raises(ValidationError) as exc_info:
            validate_active_domain(node)
        assert exc_info.value.code


# ---------------------------------------------------------------------------
# validate_dag_safety (requires store fixture)
# ---------------------------------------------------------------------------

def _insert_node_raw(store, node_id: str, parent_id: Optional[str] = None,
                     is_root: bool = False) -> None:
    """Directly insert a node into the store's DB for testing."""
    now = _now()
    conn = sqlite3.connect(store.db_path if hasattr(store, 'db_path') else store._db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO nodes (id, title, status, node_type, is_root, parent_id, "
        "created_at, updated_at, status_changed_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (node_id, f"Node {node_id}", "active", "task", int(is_root),
         parent_id, now, now, now),
    )
    if parent_id:
        conn.execute(
            "INSERT OR IGNORE INTO edges (source_id, target_id, edge_type, created_at) "
            "VALUES (?,?,?,?)",
            (node_id, parent_id, "parent", now),
        )
    conn.commit()
    conn.close()


def _insert_edge_raw(store, source_id: str, target_id: str,
                     edge_type: str = "depends_on") -> None:
    """Directly insert an edge into the store's DB for testing."""
    now = _now()
    conn = sqlite3.connect(store.db_path if hasattr(store, 'db_path') else store._db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO edges (source_id, target_id, edge_type, created_at) "
        "VALUES (?,?,?,?)",
        (source_id, target_id, edge_type, now),
    )
    conn.commit()
    conn.close()


def _get_db_path(store) -> str:
    """Get the db_path from a store regardless of attribute naming."""
    for attr in ("db_path", "_db_path"):
        if hasattr(store, attr):
            return getattr(store, attr)
    raise AttributeError("Cannot find db_path on store")


class TestDAGSafety:

    def test_no_cycle_ok(self, store):
        """A→B (parent) — adding B→C should be fine."""
        db = _get_db_path(store)
        _insert_node_raw(store, "A", is_root=True)
        _insert_node_raw(store, "B", parent_id="A")
        _insert_node_raw(store, "C", is_root=True)
        validate_dag_safety(store, "B", "C", "depends_on")

    def test_parent_cycle_rejected(self, store):
        """Parent cycle: A→B, trying to add B→A parent → reject."""
        db = _get_db_path(store)
        _insert_node_raw(store, "A", is_root=True)
        _insert_node_raw(store, "B", parent_id="A")
        with pytest.raises(ValidationError):
            validate_dag_safety(store, "A", "B", "parent")

    def test_depends_on_cycle_rejected(self, store):
        """Dependency cycle: A depends_on B, B depends_on C, add C depends_on A → reject."""
        db = _get_db_path(store)
        _insert_node_raw(store, "A", is_root=True)
        _insert_node_raw(store, "B", is_root=True)
        _insert_node_raw(store, "C", is_root=True)
        _insert_edge_raw(store, "A", "B", "depends_on")
        _insert_edge_raw(store, "B", "C", "depends_on")
        with pytest.raises(ValidationError):
            validate_dag_safety(store, "C", "A", "depends_on")

    def test_cross_dimension_child_depends_on_ancestor_rejected(self, store):
        """Cross-dimensional deadlock: child depends_on ancestor → reject."""
        db = _get_db_path(store)
        _insert_node_raw(store, "root", is_root=True)
        _insert_node_raw(store, "child", parent_id="root")
        # child depends_on root (its own ancestor) → deadlock
        with pytest.raises(ValidationError):
            validate_dag_safety(store, "child", "root", "depends_on")


# ---------------------------------------------------------------------------
# validate_attach (composite)
# ---------------------------------------------------------------------------

class TestValidateAttach:

    def test_normal_attach_ok(self, store):
        """Attaching a node to a non-archived parent with no cycle → OK."""
        _insert_node_raw(store, "parent", is_root=True)
        _insert_node_raw(store, "child", is_root=True)
        validate_attach(store, "child", "parent")

    def test_attach_to_archived_rejected(self, store):
        """Attach target is archived → rejected by active domain check."""
        _insert_node_raw(store, "parent", is_root=True)
        _insert_node_raw(store, "child", is_root=True)
        # Archive the parent directly
        db = _get_db_path(store)
        conn = sqlite3.connect(db)
        conn.execute("UPDATE nodes SET archived_at = ? WHERE id = ?",
                     (_now(), "parent"))
        conn.commit()
        conn.close()
        with pytest.raises(ValidationError):
            validate_attach(store, "child", "parent")

    def test_attach_cycle_rejected(self, store):
        """Attach would create cycle → rejected."""
        _insert_node_raw(store, "A", is_root=True)
        _insert_node_raw(store, "B", parent_id="A")
        # Try to attach A under B (A is ancestor of B)
        with pytest.raises(ValidationError):
            validate_attach(store, "A", "B")


# ---------------------------------------------------------------------------
# validate_dependency (composite)
# ---------------------------------------------------------------------------

class TestValidateDependency:

    def test_normal_dependency_ok(self, store):
        """Normal dependency between unrelated nodes → OK."""
        _insert_node_raw(store, "X", is_root=True)
        _insert_node_raw(store, "Y", is_root=True)
        validate_dependency(store, "X", "Y")

    def test_self_dependency_rejected(self, store):
        """Self-dependency → rejected."""
        _insert_node_raw(store, "X", is_root=True)
        with pytest.raises(ValidationError):
            validate_dependency(store, "X", "X")

    def test_dependency_on_archived_rejected(self, store):
        """Dependency target is archived → rejected."""
        _insert_node_raw(store, "X", is_root=True)
        _insert_node_raw(store, "Y", is_root=True)
        db = _get_db_path(store)
        conn = sqlite3.connect(db)
        conn.execute("UPDATE nodes SET archived_at = ? WHERE id = ?",
                     (_now(), "Y"))
        conn.commit()
        conn.close()
        with pytest.raises(ValidationError):
            validate_dependency(store, "X", "Y")

    def test_dependency_cycle_rejected(self, store):
        """Dependency that would create a cycle → rejected."""
        _insert_node_raw(store, "A", is_root=True)
        _insert_node_raw(store, "B", is_root=True)
        _insert_edge_raw(store, "A", "B", "depends_on")
        with pytest.raises(ValidationError):
            validate_dependency(store, "B", "A")


# ---------------------------------------------------------------------------
# Actionable Errors — every ValidationError has non-empty code
# ---------------------------------------------------------------------------

class TestActionableErrors:

    def test_all_validation_errors_have_code(self):
        """Spot-check: ValidationError always carries a code."""
        node = _make_node(status="inbox", summary=None, parent_id="p-1")
        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition("inbox", "active", node, children=[])
        assert exc_info.value.code != ""

    def test_missing_summary_suggestion_is_actionable(self):
        """Missing summary error should suggest how to fix it."""
        node = _make_node(status="inbox", summary=None, parent_id="p-1")
        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition("inbox", "active", node, children=[])
        err = exc_info.value
        combined = (err.suggestion + " " + err.message).lower()
        assert "update_field" in combined or "summary" in combined

    def test_xor_error_has_code(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_xor_constraint(is_root=True, parent_id="p-1")
        assert exc_info.value.code != ""

    def test_active_domain_error_has_code(self):
        node = _make_node(archived_at="2026-01-01T00:00:00Z")
        with pytest.raises(ValidationError) as exc_info:
            validate_active_domain(node)
        assert exc_info.value.code != ""
