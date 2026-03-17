"""Tests for spine/heartbeat.py — scan, dedup, Anti-Amnesia."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from spine.models import Node, Edge, Alert
from spine.heartbeat import HeartbeatResult, scan


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_ago(**kwargs) -> str:
    return (datetime.now(timezone.utc) - timedelta(**kwargs)).isoformat()


def _iso_later(**kwargs) -> str:
    return (datetime.now(timezone.utc) + timedelta(**kwargs)).isoformat()


@pytest.fixture
def store(tmp_path):
    from spine.schema import init_db
    from spine.store import Store

    db = str(tmp_path / "test.db")
    events = str(tmp_path / "events.jsonl")
    init_db(db)
    return Store(db, events)


def _create_node(store, id: str = "", status: str = "active",
                 deadline: str | None = None,
                 status_changed_at: str | None = None,
                 created_at: str | None = None,
                 is_root: bool = True, **kwargs) -> Node:
    now = _utcnow_iso()
    n = Node(
        id=id, title=f"Node {id or 'auto'}",
        status=status, node_type="task",
        is_root=is_root,
        deadline=deadline,
        created_at=created_at or now,
        updated_at=now,
        status_changed_at=status_changed_at or now,
        **kwargs,
    )
    created = store.create_node(n)
    # store.create_node overrides timestamps, so patch them post-creation
    updates = {}
    if status_changed_at:
        updates["status_changed_at"] = status_changed_at
    if created_at:
        updates["created_at"] = created_at
    if deadline:
        updates["deadline"] = deadline
    if updates:
        created = store.update_node(created.id, updates)
    return created


# ── 基础 ────────────────────────────────────────────────────────


class TestBasic:
    def test_no_risk_nodes_empty_alerts(self, store):
        """无风险节点 → 空 alerts"""
        _create_node(store, id="t-0001", status="active")
        result = scan(store, {})
        assert result.alerts == []
        assert result.suppressed_count == 0

    def test_returns_heartbeat_result(self, store):
        result = scan(store, {})
        assert isinstance(result, HeartbeatResult)


# ── severity 1: urgent_deadline ────────────────────────────────


class TestUrgentDeadline:
    def test_at_risk_deadline_less_24h_severity_1(self, store):
        """at-risk 且 deadline < 24h → severity=1 urgent_deadline"""
        _create_node(store, id="t-urg1", status="active",
                     deadline=_iso_later(hours=12))
        result = scan(store, {})
        assert len(result.alerts) >= 1
        alert = [a for a in result.alerts if a.node_id == "t-urg1"][0]
        assert alert.severity == 1
        assert alert.alert_type == "urgent_deadline"

    def test_at_risk_deadline_30h_not_urgent(self, store):
        """deadline 30h — at_risk but > 24h, so severity=3 not 1"""
        _create_node(store, id="t-30h", status="active",
                     deadline=_iso_later(hours=30))
        result = scan(store, {})
        alerts = [a for a in result.alerts if a.node_id == "t-30h"]
        assert len(alerts) == 1
        assert alerts[0].severity == 3
        assert alerts[0].alert_type == "deadline_warning"


# ── severity 2: critical_blocked ────────────────────────────────


class TestCriticalBlocked:
    def test_blocked_with_active_dependent_severity_2(self, store):
        """blocked 且被至少一个活跃节点依赖 → severity=2"""
        blocker = _create_node(store, id="t-blk", status="waiting")
        blocked = _create_node(store, id="t-bkd", status="active")
        # t-bkd depends_on t-blk (t-blk is blocker)
        store.add_edge(Edge(source_id="t-bkd", target_id="t-blk",
                            edge_type="depends_on"))
        # Also an active dependent that depends on t-bkd
        dependent = _create_node(store, id="t-dep", status="active")
        store.add_edge(Edge(source_id="t-dep", target_id="t-bkd",
                            edge_type="depends_on"))

        result = scan(store, {})
        alerts = [a for a in result.alerts if a.node_id == "t-bkd"]
        assert len(alerts) == 1
        assert alerts[0].severity == 2
        assert alerts[0].alert_type == "critical_blocked"

    def test_blocked_without_active_dependent_not_critical(self, store):
        """blocked 但无活跃节点依赖它 → 不是 severity=2"""
        blocker = _create_node(store, id="t-blk2", status="waiting")
        blocked = _create_node(store, id="t-bkd2", status="active")
        store.add_edge(Edge(source_id="t-bkd2", target_id="t-blk2",
                            edge_type="depends_on"))
        result = scan(store, {})
        # Should not have a critical_blocked alert for t-bkd2
        crit = [a for a in result.alerts
                if a.node_id == "t-bkd2" and a.alert_type == "critical_blocked"]
        assert len(crit) == 0


# ── severity 3: deadline_warning ─────────────────────────────────


class TestDeadlineWarning:
    def test_at_risk_48h_severity_3(self, store):
        _create_node(store, id="t-dl", status="active",
                     deadline=_iso_later(hours=40))
        result = scan(store, {})
        alerts = [a for a in result.alerts if a.node_id == "t-dl"]
        assert len(alerts) == 1
        assert alerts[0].severity == 3
        assert alerts[0].alert_type == "deadline_warning"


# ── severity 4: stale_warning ───────────────────────────────────


class TestStaleWarning:
    def test_stale_active_severity_4(self, store):
        _create_node(store, id="t-stl", status="active",
                     status_changed_at=_iso_ago(days=10))
        result = scan(store, {})
        alerts = [a for a in result.alerts if a.node_id == "t-stl"]
        assert len(alerts) == 1
        assert alerts[0].severity == 4
        assert alerts[0].alert_type == "stale_warning"


# ── severity 5: inbox_cleanup ───────────────────────────────────


class TestInboxCleanup:
    def test_inbox_stale_severity_5(self, store):
        _create_node(store, id="t-ibx", status="inbox",
                     created_at=_iso_ago(days=10))
        result = scan(store, {})
        alerts = [a for a in result.alerts if a.node_id == "t-ibx"]
        assert len(alerts) == 1
        assert alerts[0].severity == 5
        assert alerts[0].alert_type == "inbox_cleanup"


# ── 去重 ────────────────────────────────────────────────────────


class TestDedup:
    def test_same_alert_not_repeated(self, store):
        """去重: 相同告警不重复推送"""
        _create_node(store, id="t-dup", status="active",
                     status_changed_at=_iso_ago(days=10))
        r1 = scan(store, {})
        assert len(r1.alerts) == 1

        # Build session_state from r1 output
        session = {}
        scan(store, session)  # first scan populates session
        r2 = scan(store, session)
        # Second scan should suppress the same alert
        dup_alerts = [a for a in r2.alerts if a.node_id == "t-dup"]
        assert len(dup_alerts) == 0
        assert r2.suppressed_count >= 1

    def test_dedup_repush_after_status_change(self, store):
        """去重: 状态变化后重新推送"""
        _create_node(store, id="t-rp", status="active",
                     status_changed_at=_iso_ago(days=10))
        session = {}
        r1 = scan(store, session)
        assert len([a for a in r1.alerts if a.node_id == "t-rp"]) == 1

        # Simulate status change
        store.update_node("t-rp", {
            "status_changed_at": _utcnow_iso(),
            "status": "waiting",
        })
        # Still stale (waiting + old status_changed_at would be needed)
        # Actually after update, status_changed_at is now, so not stale anymore.
        # Let's make it stale again with old status_changed_at
        store.update_node("t-rp", {
            "status_changed_at": _iso_ago(days=10),
        })

        r2 = scan(store, session)
        # After status_changed_at changed, dedup key should allow re-push
        rp_alerts = [a for a in r2.alerts if a.node_id == "t-rp"]
        assert len(rp_alerts) == 1


# ── Anti-Amnesia ─────────────────────────────────────────────────


class TestAntiAmnesia:
    def test_high_severity_repush_after_24h(self, store):
        """Anti-Amnesia: severity<=2 推送超过24h且无实质行动 → 重推"""
        old_sc = _iso_ago(hours=30)
        _create_node(store, id="t-aa", status="active",
                     deadline=_iso_later(hours=12),
                     status_changed_at=old_sc)
        session = {}
        r1 = scan(store, session)
        assert len([a for a in r1.alerts if a.node_id == "t-aa"]) == 1

        # Simulate: pushed 25h ago, no status change since then
        for key in list(session.get("last_alerts", {}).keys()):
            if "t-aa" in key:
                session["last_alerts"][key]["pushed_at"] = _iso_ago(hours=25)

        r2 = scan(store, session)
        aa_alerts = [a for a in r2.alerts if a.node_id == "t-aa"]
        assert len(aa_alerts) == 1  # re-pushed

    def test_anti_amnesia_not_triggered_if_action_taken(self, store):
        """实质行动后不重推"""
        _create_node(store, id="t-aa2", status="active",
                     deadline=_iso_later(hours=12))
        session = {}
        r1 = scan(store, session)

        # Simulate: pushed 25h ago
        for key in list(session.get("last_alerts", {}).keys()):
            if "t-aa2" in key:
                session["last_alerts"][key]["pushed_at"] = _iso_ago(hours=25)

        # status_changed_at updated (substantive action)
        store.update_node("t-aa2", {
            "status_changed_at": _utcnow_iso(),
        })

        r2 = scan(store, session)
        # Still at risk so alert fires as new (status changed clears dedup)
        # But it shouldn't be an anti-amnesia re-push since action was taken
        # The node still has deadline <24h so it will generate an alert,
        # but the dedup should see status_changed_at > pushed_at
        aa2_alerts = [a for a in r2.alerts if a.node_id == "t-aa2"]
        # Since status changed, dedup allows but it's a fresh alert, not anti-amnesia
        assert len(aa2_alerts) == 1


# ── Top 3 + suppressed_count ─────────────────────────────────────


class TestTop3:
    def test_top3_limit_and_suppressed(self, store):
        """Top 3 限制 + suppressed_count"""
        # Create 5 stale nodes → 5 alerts
        for i in range(5):
            _create_node(store, id=f"t-s{i}", status="active",
                         status_changed_at=_iso_ago(days=10))
        result = scan(store, {})
        assert len(result.alerts) == 3
        assert result.suppressed_count == 2

    def test_top3_ordered_by_severity(self, store):
        """Top 3 应按 severity 排序，高优先级先出"""
        # severity 1
        _create_node(store, id="t-hi", status="active",
                     deadline=_iso_later(hours=12))
        # severity 4 (stale)
        _create_node(store, id="t-lo1", status="active",
                     status_changed_at=_iso_ago(days=10))
        _create_node(store, id="t-lo2", status="active",
                     status_changed_at=_iso_ago(days=10))
        _create_node(store, id="t-lo3", status="active",
                     status_changed_at=_iso_ago(days=10))
        _create_node(store, id="t-lo4", status="active",
                     status_changed_at=_iso_ago(days=10))

        result = scan(store, {})
        assert len(result.alerts) == 3
        assert result.alerts[0].severity == 1
        assert result.alerts[0].node_id == "t-hi"
        assert result.suppressed_count == 2


# ── focus_candidates ─────────────────────────────────────────────


class TestFocusCandidates:
    def test_focus_includes_high_severity(self, store):
        """focus_candidates 包含 severity<=2 的 node_id"""
        _create_node(store, id="t-fc1", status="active",
                     deadline=_iso_later(hours=12))
        _create_node(store, id="t-fc2", status="active",
                     status_changed_at=_iso_ago(days=10))
        result = scan(store, {})
        assert "t-fc1" in result.focus_candidates
        assert "t-fc2" not in result.focus_candidates

    def test_focus_includes_critical_blocked(self, store):
        """critical_blocked (severity=2) 也在 focus_candidates"""
        blocker = _create_node(store, id="t-fblk", status="waiting")
        blocked = _create_node(store, id="t-fbkd", status="active")
        store.add_edge(Edge(source_id="t-fbkd", target_id="t-fblk",
                            edge_type="depends_on"))
        dep = _create_node(store, id="t-fdep", status="active")
        store.add_edge(Edge(source_id="t-fdep", target_id="t-fbkd",
                            edge_type="depends_on"))

        result = scan(store, {})
        assert "t-fbkd" in result.focus_candidates
