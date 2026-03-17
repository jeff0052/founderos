"""Tests for spine/rollup.py — recursive rollup_status computation."""

import tempfile
from typing import Optional

import pytest

from spine.schema import init_db
from spine.store import Store
from spine.models import Node
from spine.rollup import compute_rollup, batch_compute_rollup


# --- Fixtures ---

@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "fpms.db")
    events_path = str(tmp_path / "events.jsonl")
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)


def _make(store: Store, title: str, status: str = "inbox",
          parent_id: Optional[str] = None, is_root: bool = False,
          archived_at: Optional[str] = None) -> Node:
    node = Node(
        id="", title=title, status=status, node_type="task",
        is_root=is_root if parent_id is None else False,
        parent_id=parent_id, archived_at=archived_at,
    )
    return store.create_node(node)


# ============================================================
# compute_rollup — leaf nodes
# ============================================================

class TestLeafNode:
    def test_leaf_returns_own_status_active(self, store):
        n = _make(store, "leaf", status="active", is_root=True)
        assert compute_rollup(store, n.id) == "active"

    def test_leaf_returns_own_status_done(self, store):
        n = _make(store, "leaf", status="done", is_root=True)
        assert compute_rollup(store, n.id) == "done"

    def test_leaf_returns_own_status_inbox(self, store):
        n = _make(store, "leaf", status="inbox", is_root=True)
        assert compute_rollup(store, n.id) == "inbox"


# ============================================================
# compute_rollup — one level of children
# ============================================================

class TestOneLevel:
    def test_one_active_one_done_returns_active(self, store):
        """Rule 2: any child active → rollup = active."""
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "c1", status="active", parent_id=parent.id)
        _make(store, "c2", status="done", parent_id=parent.id)
        assert compute_rollup(store, parent.id) == "active"

    def test_one_waiting_one_done_returns_waiting(self, store):
        """Rule 3: any child waiting → rollup = waiting."""
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "c1", status="waiting", parent_id=parent.id)
        _make(store, "c2", status="done", parent_id=parent.id)
        assert compute_rollup(store, parent.id) == "waiting"

    def test_all_done_returns_done(self, store):
        """Rule 4: all terminal, at least one done → done."""
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "c1", status="done", parent_id=parent.id)
        _make(store, "c2", status="done", parent_id=parent.id)
        assert compute_rollup(store, parent.id) == "done"

    def test_all_dropped_returns_dropped(self, store):
        """Rule 5: all dropped → dropped."""
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "c1", status="dropped", parent_id=parent.id)
        _make(store, "c2", status="dropped", parent_id=parent.id)
        assert compute_rollup(store, parent.id) == "dropped"

    def test_done_and_dropped_mix_returns_done(self, store):
        """Rule 4: all terminal, mixed done+dropped, at least one done → done."""
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "c1", status="done", parent_id=parent.id)
        _make(store, "c2", status="dropped", parent_id=parent.id)
        assert compute_rollup(store, parent.id) == "done"


# ============================================================
# inbox isolation — inbox children excluded from rollup
# ============================================================

class TestInboxIsolation:
    def test_inbox_child_excluded_all_others_done(self, store):
        """Inbox children don't participate. Only done children → rollup=done."""
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "inbox-child", status="inbox", parent_id=parent.id)
        _make(store, "done-child", status="done", parent_id=parent.id)
        assert compute_rollup(store, parent.id) == "done"

    def test_only_inbox_children_returns_own_status(self, store):
        """If all children are inbox (excluded), treat as leaf → own status."""
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "inbox1", status="inbox", parent_id=parent.id)
        _make(store, "inbox2", status="inbox", parent_id=parent.id)
        assert compute_rollup(store, parent.id) == "active"

    def test_inbox_plus_waiting_returns_waiting(self, store):
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "inbox-child", status="inbox", parent_id=parent.id)
        _make(store, "waiting-child", status="waiting", parent_id=parent.id)
        assert compute_rollup(store, parent.id) == "waiting"


# ============================================================
# archived children participate (denominator preservation)
# ============================================================

class TestArchivedChildren:
    def test_archived_done_child_participates(self, store):
        """Archived child (status=done) counts in rollup."""
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "archived-done", status="done", parent_id=parent.id,
              archived_at="2026-01-01T00:00:00+00:00")
        _make(store, "active-child", status="active", parent_id=parent.id)
        # One active + one done(archived) → active (rule 2)
        assert compute_rollup(store, parent.id) == "active"

    def test_all_archived_done_returns_done(self, store):
        parent = _make(store, "parent", status="active", is_root=True)
        _make(store, "a1", status="done", parent_id=parent.id,
              archived_at="2026-01-01T00:00:00+00:00")
        _make(store, "a2", status="done", parent_id=parent.id,
              archived_at="2026-01-01T00:00:00+00:00")
        assert compute_rollup(store, parent.id) == "done"


# ============================================================
# recursive rollup — grandchild affects grandparent
# ============================================================

class TestRecursive:
    def test_grandchild_active_propagates_up(self, store):
        """
        root (active)
          └── mid (active)
                └── leaf (active)
        leaf active → mid rollup=active → root rollup=active
        """
        root = _make(store, "root", status="active", is_root=True)
        mid = _make(store, "mid", status="done", parent_id=root.id)
        _make(store, "leaf", status="active", parent_id=mid.id)
        # mid has active child → mid rollup=active → root has active child → active
        assert compute_rollup(store, root.id) == "active"

    def test_grandchild_all_done_propagates(self, store):
        root = _make(store, "root", status="active", is_root=True)
        mid = _make(store, "mid", status="done", parent_id=root.id)
        _make(store, "leaf", status="done", parent_id=mid.id)
        # mid rollup=done → root rollup=done
        assert compute_rollup(store, root.id) == "done"

    def test_deep_tree_three_levels(self, store):
        """
        root
          └── l1 (done)
                └── l2 (done)
                      └── l3 (waiting)
        l2 rollup=waiting → l1 rollup=waiting → root rollup=waiting
        """
        root = _make(store, "root", status="active", is_root=True)
        l1 = _make(store, "l1", status="done", parent_id=root.id)
        l2 = _make(store, "l2", status="done", parent_id=l1.id)
        _make(store, "l3", status="waiting", parent_id=l2.id)
        assert compute_rollup(store, root.id) == "waiting"


# ============================================================
# batch_compute_rollup
# ============================================================

class TestBatchRollup:
    def test_batch_multiple_trees(self, store):
        """Compute rollup for two independent trees."""
        r1 = _make(store, "root1", status="active", is_root=True)
        _make(store, "c1", status="done", parent_id=r1.id)

        r2 = _make(store, "root2", status="active", is_root=True)
        _make(store, "c2", status="active", parent_id=r2.id)

        result = batch_compute_rollup(store, root_ids=[r1.id, r2.id])
        assert result[r1.id] == "done"
        assert result[r2.id] == "active"

    def test_batch_includes_descendants(self, store):
        """batch should include rollup for all nodes in subtrees."""
        root = _make(store, "root", status="active", is_root=True)
        child = _make(store, "child", status="active", parent_id=root.id)
        _make(store, "gc", status="done", parent_id=child.id)

        result = batch_compute_rollup(store, root_ids=[root.id])
        # child has one done kid → rollup=done
        assert result[child.id] == "done"
        # root has child whose rollup=done → rollup=done
        assert result[root.id] == "done"

    def test_batch_none_computes_all_roots(self, store):
        """root_ids=None → find all root nodes and compute."""
        r1 = _make(store, "root1", status="active", is_root=True)
        _make(store, "c1", status="done", parent_id=r1.id)
        r2 = _make(store, "root2", status="waiting", is_root=True)

        result = batch_compute_rollup(store)
        assert r1.id in result
        assert result[r1.id] == "done"
        assert r2.id in result
        assert result[r2.id] == "waiting"  # leaf → own status


# ============================================================
# Edge case: node not found
# ============================================================

class TestEdgeCases:
    def test_nonexistent_node_raises(self, store):
        with pytest.raises(ValueError, match="not found"):
            compute_rollup(store, "no-such-id")
