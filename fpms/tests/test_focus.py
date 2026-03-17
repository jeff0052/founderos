"""Tests for spine/focus.py — arbitrate and shift_focus."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from spine.focus import FocusResult, arbitrate, shift_focus
from spine.models import Node
from spine.schema import init_db
from spine.store import Store


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)


def _create_active_node(store: Store, node_id: str, **kwargs) -> Node:
    """Helper: create an active node with summary (meets activation preconditions)."""
    return store.create_node(Node(
        id=node_id,
        title=f"Node {node_id}",
        status="active",
        node_type="task",
        is_root=True,
        summary="test summary",
        created_at="",
        updated_at="",
        status_changed_at="",
        **kwargs,
    ))


def _empty_session() -> dict:
    return {}


def _session_with_focus(primary: str | None = None,
                        secondaries: list[str] | None = None,
                        touched_at: dict[str, str] | None = None) -> dict:
    s = {}
    if primary is not None:
        s["focus_primary"] = primary
    if secondaries is not None:
        s["focus_secondaries"] = json.dumps(secondaries)
    if touched_at is not None:
        s["focus_touched_at"] = json.dumps(touched_at)
    return s


# ── arbitrate: no focus, no sources ─────────────────────────────


class TestArbitrateEmpty:
    def test_no_focus_no_sources(self, store):
        result = arbitrate(store, _empty_session())
        assert result.primary is None
        assert result.secondaries == []

    def test_no_focus_no_sources_has_reason(self, store):
        result = arbitrate(store, _empty_session())
        assert isinstance(result.reason, str)


# ── arbitrate: user_request overrides all ────────────────────────


class TestArbitrateUserRequest:
    def test_user_request_becomes_primary(self, store):
        n = _create_active_node(store, "task-aaaa")
        result = arbitrate(store, _empty_session(), user_request="task-aaaa")
        assert result.primary == "task-aaaa"

    def test_user_request_overrides_historical(self, store):
        _create_active_node(store, "task-aaaa")
        _create_active_node(store, "task-bbbb")
        session = _session_with_focus(
            primary="task-bbbb",
            touched_at={"task-bbbb": _utcnow_iso()},
        )
        result = arbitrate(store, session, user_request="task-aaaa")
        assert result.primary == "task-aaaa"
        # old primary demoted to secondary
        assert "task-bbbb" in result.secondaries

    def test_user_request_overrides_alerts(self, store):
        _create_active_node(store, "task-aaaa")
        _create_active_node(store, "task-bbbb")
        result = arbitrate(
            store, _empty_session(),
            user_request="task-aaaa",
            alert_candidates=["task-bbbb"],
        )
        assert result.primary == "task-aaaa"

    def test_user_request_invalid_node(self, store):
        """user_request pointing to nonexistent node → fallback, not crash."""
        result = arbitrate(store, _empty_session(), user_request="task-9999")
        assert result.primary is None


# ── arbitrate: alert_candidates ──────────────────────────────────


class TestArbitrateAlerts:
    def test_alert_becomes_primary(self, store):
        _create_active_node(store, "task-aaaa")
        result = arbitrate(store, _empty_session(), alert_candidates=["task-aaaa"])
        assert result.primary == "task-aaaa"

    def test_alert_overrides_historical(self, store):
        _create_active_node(store, "task-aaaa")
        _create_active_node(store, "task-bbbb")
        session = _session_with_focus(
            primary="task-bbbb",
            touched_at={"task-bbbb": _utcnow_iso()},
        )
        result = arbitrate(store, session, alert_candidates=["task-aaaa"])
        assert result.primary == "task-aaaa"

    def test_multiple_alerts_first_is_primary(self, store):
        _create_active_node(store, "task-aaaa")
        _create_active_node(store, "task-bbbb")
        _create_active_node(store, "task-cccc")
        result = arbitrate(
            store, _empty_session(),
            alert_candidates=["task-aaaa", "task-bbbb", "task-cccc"],
        )
        assert result.primary == "task-aaaa"
        assert "task-bbbb" in result.secondaries
        assert "task-cccc" in result.secondaries

    def test_alerts_capped_at_3(self, store):
        """4 alerts → only 3 slots (1 primary + 2 secondaries)."""
        for suffix in ["aaaa", "bbbb", "cccc", "dddd"]:
            _create_active_node(store, f"task-{suffix}")
        result = arbitrate(
            store, _empty_session(),
            alert_candidates=["task-aaaa", "task-bbbb", "task-cccc", "task-dddd"],
        )
        total = ([result.primary] if result.primary else []) + result.secondaries
        assert len(total) <= 3


# ── arbitrate: time-driven (deadline) ────────────────────────────


class TestArbitrateDeadline:
    def test_nearest_deadline_wins(self, store):
        soon = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        later = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        _create_active_node(store, "task-soon", deadline=soon)
        _create_active_node(store, "task-later", deadline=later)
        result = arbitrate(store, _empty_session())
        assert result.primary == "task-soon"

    def test_no_deadline_nodes_skipped(self, store):
        """Nodes without deadline don't participate in time-driven selection."""
        _create_active_node(store, "task-nodeadline")
        # If there's nothing else, time-driven returns nothing
        result = arbitrate(store, _empty_session())
        # Should fall through to no focus (no deadline, no history)
        assert result.primary is None


# ── arbitrate: historical focus restore ──────────────────────────


class TestArbitrateHistorical:
    def test_restore_historical_primary(self, store):
        _create_active_node(store, "task-aaaa")
        session = _session_with_focus(
            primary="task-aaaa",
            touched_at={"task-aaaa": _utcnow_iso()},
        )
        result = arbitrate(store, session)
        assert result.primary == "task-aaaa"

    def test_historical_with_secondaries(self, store):
        _create_active_node(store, "task-aaaa")
        _create_active_node(store, "task-bbbb")
        now = _utcnow_iso()
        session = _session_with_focus(
            primary="task-aaaa",
            secondaries=["task-bbbb"],
            touched_at={"task-aaaa": now, "task-bbbb": now},
        )
        result = arbitrate(store, session)
        assert result.primary == "task-aaaa"
        assert "task-bbbb" in result.secondaries

    def test_historical_deleted_node_cleared(self, store):
        """Historical focus pointing to deleted node → cleared."""
        session = _session_with_focus(
            primary="task-gone",
            touched_at={"task-gone": _utcnow_iso()},
        )
        result = arbitrate(store, session)
        assert result.primary is None


# ── decay: 3-day untouched removal ──────────────────────────────


class TestDecay:
    def test_stale_focus_removed(self, store):
        _create_active_node(store, "task-stale")
        session = _session_with_focus(
            primary="task-stale",
            touched_at={"task-stale": _days_ago_iso(4)},
        )
        result = arbitrate(store, session)
        # Stale node should be decayed out
        assert result.primary != "task-stale"

    def test_fresh_focus_kept(self, store):
        _create_active_node(store, "task-fresh")
        session = _session_with_focus(
            primary="task-fresh",
            touched_at={"task-fresh": _utcnow_iso()},
        )
        result = arbitrate(store, session)
        assert result.primary == "task-fresh"

    def test_mixed_decay(self, store):
        """One stale secondary removed, one fresh kept."""
        _create_active_node(store, "task-pri")
        _create_active_node(store, "task-fresh")
        _create_active_node(store, "task-stale")
        now = _utcnow_iso()
        session = _session_with_focus(
            primary="task-pri",
            secondaries=["task-fresh", "task-stale"],
            touched_at={
                "task-pri": now,
                "task-fresh": now,
                "task-stale": _days_ago_iso(4),
            },
        )
        result = arbitrate(store, session)
        assert result.primary == "task-pri"
        assert "task-fresh" in result.secondaries
        assert "task-stale" not in result.secondaries


# ── shift_focus ──────────────────────────────────────────────────


class TestShiftFocus:
    def test_shift_to_new_node(self, store):
        _create_active_node(store, "task-aaaa")
        result = shift_focus(store, "task-aaaa")
        assert result.primary == "task-aaaa"

    def test_shift_nonexistent_node_errors(self, store):
        with pytest.raises(ValueError, match="not found"):
            shift_focus(store, "task-9999")

    def test_shift_demotes_old_primary(self, store):
        _create_active_node(store, "task-aaaa")
        _create_active_node(store, "task-bbbb")
        # Set initial focus
        shift_focus(store, "task-aaaa")
        # Shift to new
        result = shift_focus(store, "task-bbbb")
        assert result.primary == "task-bbbb"
        assert "task-aaaa" in result.secondaries

    def test_shift_lru_eviction(self, store):
        """4 shifts → oldest should be evicted (only 3 slots)."""
        for suffix in ["aaaa", "bbbb", "cccc", "dddd"]:
            _create_active_node(store, f"task-{suffix}")

        shift_focus(store, "task-aaaa")
        shift_focus(store, "task-bbbb")
        shift_focus(store, "task-cccc")
        result = shift_focus(store, "task-dddd")

        total = [result.primary] + result.secondaries
        assert len(total) <= 3
        # task-aaaa was touched earliest, should be evicted
        assert "task-aaaa" not in total
        assert result.primary == "task-dddd"

    def test_shift_updates_touched_at(self, store):
        _create_active_node(store, "task-aaaa")
        shift_focus(store, "task-aaaa")
        # Read back from session_state (stored as {"v": {node_id: timestamp}})
        raw = store.get_session("focus_touched_at")
        assert raw is not None
        touched = raw["v"]
        assert "task-aaaa" in touched

    def test_shift_same_node_is_noop(self, store):
        """Shifting to current primary should not duplicate it."""
        _create_active_node(store, "task-aaaa")
        shift_focus(store, "task-aaaa")
        result = shift_focus(store, "task-aaaa")
        assert result.primary == "task-aaaa"
        assert "task-aaaa" not in result.secondaries
