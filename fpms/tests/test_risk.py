"""Tests for spine/risk.py — compute_risks (pure) and batch_compute_risks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from spine.models import Node
from spine.risk import RiskMarks, compute_risks, batch_compute_risks


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_node(
    id: str = "task-0001",
    status: str = "active",
    deadline: str | None = None,
    status_changed_at: str | None = None,
    created_at: str | None = None,
    **kwargs,
) -> Node:
    now = _utcnow_iso()
    return Node(
        id=id,
        title=f"Node {id}",
        status=status,
        node_type="task",
        created_at=created_at or now,
        updated_at=now,
        status_changed_at=status_changed_at or now,
        deadline=deadline,
        **kwargs,
    )


# ── blocked ──────────────────────────────────────────────────────


class TestBlocked:
    def test_blocked_when_dep_not_done(self):
        node = _make_node(status="active")
        dep = _make_node(id="task-dep1", status="active")
        marks = compute_risks(node, [dep])
        assert marks.blocked is True
        assert "task-dep1" in marks.blocked_by

    def test_blocked_multiple_deps(self):
        node = _make_node(status="active")
        dep1 = _make_node(id="dep-1", status="done")
        dep2 = _make_node(id="dep-2", status="waiting")
        marks = compute_risks(node, [dep1, dep2])
        assert marks.blocked is True
        assert marks.blocked_by == ["dep-2"]

    def test_not_blocked_all_deps_done(self):
        node = _make_node(status="active")
        dep = _make_node(id="dep-1", status="done")
        marks = compute_risks(node, [dep])
        assert marks.blocked is False
        assert marks.blocked_by == []

    def test_blocked_dep_dropped_still_blocked(self):
        """dropped 不解锁 blocked（dropped 前置 = 死胡同）"""
        node = _make_node(status="active")
        dep = _make_node(id="dep-1", status="dropped")
        marks = compute_risks(node, [dep])
        assert marks.blocked is True
        assert "dep-1" in marks.blocked_by

    def test_not_blocked_self_done(self):
        node = _make_node(status="done")
        dep = _make_node(id="dep-1", status="active")
        marks = compute_risks(node, [dep])
        assert marks.blocked is False

    def test_not_blocked_self_dropped(self):
        node = _make_node(status="dropped")
        dep = _make_node(id="dep-1", status="active")
        marks = compute_risks(node, [dep])
        assert marks.blocked is False

    def test_not_blocked_no_deps(self):
        node = _make_node(status="active")
        marks = compute_risks(node, [])
        assert marks.blocked is False

    def test_blocked_inbox_with_undone_dep(self):
        node = _make_node(status="inbox")
        dep = _make_node(id="dep-1", status="waiting")
        marks = compute_risks(node, [dep])
        assert marks.blocked is True


# ── at_risk ──────────────────────────────────────────────────────


class TestAtRisk:
    def test_at_risk_deadline_47h(self):
        deadline = (datetime.now(timezone.utc) + timedelta(hours=47)).isoformat()
        node = _make_node(status="active", deadline=deadline)
        marks = compute_risks(node, [])
        assert marks.at_risk is True

    def test_not_at_risk_deadline_49h(self):
        deadline = (datetime.now(timezone.utc) + timedelta(hours=49)).isoformat()
        node = _make_node(status="active", deadline=deadline)
        marks = compute_risks(node, [])
        assert marks.at_risk is False

    def test_not_at_risk_no_deadline(self):
        node = _make_node(status="active", deadline=None)
        marks = compute_risks(node, [])
        assert marks.at_risk is False

    def test_not_at_risk_done_with_near_deadline(self):
        deadline = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()
        node = _make_node(status="done", deadline=deadline)
        marks = compute_risks(node, [])
        assert marks.at_risk is False

    def test_not_at_risk_dropped_with_near_deadline(self):
        deadline = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()
        node = _make_node(status="dropped", deadline=deadline)
        marks = compute_risks(node, [])
        assert marks.at_risk is False

    def test_at_risk_deadline_already_passed(self):
        deadline = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        node = _make_node(status="active", deadline=deadline)
        marks = compute_risks(node, [])
        assert marks.at_risk is True

    def test_not_at_risk_deadline_well_beyond_48h(self):
        """Deadline 50h from now — clearly not at_risk."""
        deadline = (datetime.now(timezone.utc) + timedelta(hours=50)).isoformat()
        node = _make_node(status="active", deadline=deadline)
        marks = compute_risks(node, [])
        assert marks.at_risk is False


# ── stale ────────────────────────────────────────────────────────


class TestStale:
    def test_stale_active_8days(self):
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        node = _make_node(status="active", status_changed_at=old)
        marks = compute_risks(node, [])
        assert marks.stale is True

    def test_not_stale_active_6days(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
        node = _make_node(status="active", status_changed_at=recent)
        marks = compute_risks(node, [])
        assert marks.stale is False

    def test_stale_waiting_8days(self):
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        node = _make_node(status="waiting", status_changed_at=old)
        marks = compute_risks(node, [])
        assert marks.stale is True

    def test_not_stale_done(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        node = _make_node(status="done", status_changed_at=old)
        marks = compute_risks(node, [])
        assert marks.stale is False

    def test_not_stale_dropped(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        node = _make_node(status="dropped", status_changed_at=old)
        marks = compute_risks(node, [])
        assert marks.stale is False

    def test_stale_inbox_uses_created_at(self):
        """inbox 节点的 stale 看 created_at 而非 status_changed_at。"""
        old_created = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        recent_status = _utcnow_iso()
        node = _make_node(
            status="inbox",
            created_at=old_created,
            status_changed_at=recent_status,
        )
        marks = compute_risks(node, [])
        assert marks.stale is True

    def test_not_stale_inbox_recent_created_at(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        node = _make_node(status="inbox", created_at=recent)
        marks = compute_risks(node, [])
        assert marks.stale is False

    def test_not_stale_active_5days(self):
        """5 days — clearly not stale."""
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        node = _make_node(status="active", status_changed_at=recent)
        marks = compute_risks(node, [])
        assert marks.stale is False


# ── combined ─────────────────────────────────────────────────────


class TestCombined:
    def test_all_risks_at_once(self):
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        near_deadline = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        node = _make_node(
            status="active", status_changed_at=old, deadline=near_deadline
        )
        dep = _make_node(id="dep-1", status="waiting")
        marks = compute_risks(node, [dep])
        assert marks.blocked is True
        assert marks.at_risk is True
        assert marks.stale is True

    def test_clean_node(self):
        node = _make_node(status="active")
        marks = compute_risks(node, [])
        assert marks.blocked is False
        assert marks.at_risk is False
        assert marks.stale is False
        assert marks.blocked_by == []


# ── batch_compute_risks ─────────────────────────────────────────


class TestBatchComputeRisks:
    def test_batch_returns_dict(self, tmp_path):
        from spine.schema import init_db
        from spine.store import Store

        db = str(tmp_path / "test.db")
        events = str(tmp_path / "events.jsonl")
        init_db(db)
        store = Store(db, events)

        # Create two nodes: one active, one done
        n1 = Node(
            id="", title="Active task", status="active", node_type="task",
            is_root=True,
            created_at=_utcnow_iso(), updated_at=_utcnow_iso(),
            status_changed_at=_utcnow_iso(),
        )
        n2 = Node(
            id="", title="Done task", status="done", node_type="task",
            is_root=True,
            created_at=_utcnow_iso(), updated_at=_utcnow_iso(),
            status_changed_at=_utcnow_iso(),
        )
        n1 = store.create_node(n1)
        n2 = store.create_node(n2)

        result = batch_compute_risks(store)
        # Only non-terminal nodes should be included
        assert n1.id in result
        assert n2.id not in result

    def test_batch_specific_ids(self, tmp_path):
        from spine.schema import init_db
        from spine.store import Store

        db = str(tmp_path / "test.db")
        events = str(tmp_path / "events.jsonl")
        init_db(db)
        store = Store(db, events)

        n1 = Node(
            id="", title="Task 1", status="active", node_type="task",
            is_root=True,
            created_at=_utcnow_iso(), updated_at=_utcnow_iso(),
            status_changed_at=_utcnow_iso(),
        )
        n2 = Node(
            id="", title="Task 2", status="active", node_type="task",
            is_root=True,
            created_at=_utcnow_iso(), updated_at=_utcnow_iso(),
            status_changed_at=_utcnow_iso(),
        )
        n1 = store.create_node(n1)
        n2 = store.create_node(n2)

        result = batch_compute_risks(store, node_ids=[n1.id])
        assert n1.id in result
        assert n2.id not in result

    def test_batch_with_blocked_dep(self, tmp_path):
        from spine.schema import init_db
        from spine.store import Store
        from spine.models import Edge

        db = str(tmp_path / "test.db")
        events = str(tmp_path / "events.jsonl")
        init_db(db)
        store = Store(db, events)

        n1 = Node(
            id="", title="Blocked", status="active", node_type="task",
            is_root=True,
            created_at=_utcnow_iso(), updated_at=_utcnow_iso(),
            status_changed_at=_utcnow_iso(),
        )
        n2 = Node(
            id="", title="Dep", status="waiting", node_type="task",
            is_root=True,
            created_at=_utcnow_iso(), updated_at=_utcnow_iso(),
            status_changed_at=_utcnow_iso(),
        )
        n1 = store.create_node(n1)
        n2 = store.create_node(n2)

        edge = Edge(source_id=n1.id, target_id=n2.id, edge_type="depends_on")
        store.add_edge(edge)

        result = batch_compute_risks(store)
        assert result[n1.id].blocked is True
        assert n2.id in result[n1.id].blocked_by
