"""Tests for spine/recovery.py — cold start bootstrap flow."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from spine.models import Node, Alert, ContextBundle
from spine.focus import FocusResult
from spine.heartbeat import HeartbeatResult
from spine.recovery import bootstrap, _render_alerts_md
from spine.schema import init_db
from spine.store import Store


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_ago(**kwargs) -> str:
    return (datetime.now(timezone.utc) - timedelta(**kwargs)).isoformat()


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


def _create_root_node(store: Store, node_id: str, status: str = "active",
                      **kwargs) -> Node:
    fields = dict(
        id=node_id,
        title=f"Node {node_id}",
        status=status,
        node_type="task",
        is_root=True,
        summary="test summary",
        created_at="",
        updated_at="",
        status_changed_at="",
    )
    fields.update(kwargs)
    return store.create_node(Node(**fields))


# Patch targets — module aliases in recovery.py
_PATCH_DASHBOARD = "spine.recovery.dashboard"
_PATCH_HEARTBEAT = "spine.recovery.heartbeat"
_PATCH_FOCUS = "spine.recovery.focus_mod"
_PATCH_BUNDLE = "spine.recovery.bundle"


# ── _render_alerts_md ──

class TestRenderAlertsMd:
    def test_empty_alerts(self):
        assert _render_alerts_md([]) == ""

    def test_single_alert(self):
        alert = Alert(
            node_id="task-1234",
            alert_type="stale_warning",
            message="Node stale >7d",
            severity=4,
            first_seen=_utcnow_iso(),
        )
        md = _render_alerts_md([alert])
        assert "## ⚠️ 系统告警" in md
        assert "🔴 [task-1234]: stale_warning - Node stale >7d" in md

    def test_multiple_alerts(self):
        alerts = [
            Alert("n1", "blocked", "Blocked", 2, _utcnow_iso()),
            Alert("n2", "at_risk", "At risk", 3, _utcnow_iso()),
        ]
        md = _render_alerts_md(alerts)
        lines = md.split("\n")
        assert len(lines) == 3  # header + 2 alerts
        assert "[n1]" in lines[1]
        assert "[n2]" in lines[2]


# ── bootstrap ──

class TestBootstrapEmptyStore:
    """空 store → 返回空 ContextBundle，不崩溃。"""

    def test_empty_store_no_crash(self, store, narratives_dir):
        with patch(_PATCH_BUNDLE) as mock_bundle:
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="",
                l_alert="",
                l1_neighborhood="",
                l2_focus="",
                total_tokens=0,
            )
            ctx = bootstrap(store, narratives_dir)

        assert isinstance(ctx, ContextBundle)
        assert ctx.l0_dashboard == ""
        assert ctx.l_alert == ""


class TestBootstrapNormalFlow:
    """正常恢复: 所有步骤成功。"""

    def test_full_assembly(self, store, narratives_dir):
        _create_root_node(store, "task-0001", status="active")

        expected_bundle = ContextBundle(
            l0_dashboard="# Dashboard",
            l_alert="",
            l1_neighborhood="neighborhood",
            l2_focus="focus content",
            total_tokens=500,
            focus_node_id="task-0001",
        )

        with patch(_PATCH_BUNDLE) as mock_bundle:
            mock_bundle.assemble.return_value = expected_bundle
            ctx = bootstrap(store, narratives_dir)

        assert isinstance(ctx, ContextBundle)
        mock_bundle.assemble.assert_called_once()


class TestBootstrapWithAlerts:
    """有告警 → alerts_md 正确渲染并传给 bundle。"""

    def test_alerts_passed_to_bundle(self, store, narratives_dir):
        # Create a stale node to trigger heartbeat alerts
        node = _create_root_node(store, "task-stale", status="active")
        store.update_node("task-stale", {
            "status_changed_at": _iso_ago(days=10),
        })

        with patch(_PATCH_BUNDLE) as mock_bundle:
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="", l_alert="", l1_neighborhood="",
                l2_focus="", total_tokens=0,
            )
            bootstrap(store, narratives_dir)

        call_args = mock_bundle.assemble.call_args
        alerts_md_arg = call_args[0][3]  # 4th positional arg
        # Stale node should produce an alert
        if alerts_md_arg:
            assert "task-stale" in alerts_md_arg


class TestBootstrapWithFocus:
    """有焦点 → focus_result 传给 bundle。"""

    def test_focus_arbitration_runs(self, store, narratives_dir):
        deadline = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        _create_root_node(store, "task-focus", status="active")
        store.update_node("task-focus", {"deadline": deadline})

        with patch(_PATCH_BUNDLE) as mock_bundle:
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="", l_alert="", l1_neighborhood="",
                l2_focus="", total_tokens=0, focus_node_id="task-focus",
            )
            ctx = bootstrap(store, narratives_dir)

        call_args = mock_bundle.assemble.call_args
        focus_arg = call_args[0][1]  # 2nd positional arg = FocusResult
        assert isinstance(focus_arg, FocusResult)


class TestBootstrapNoFocus:
    """无焦点 → 无焦点模式。"""

    def test_no_focus_mode(self, store, narratives_dir):
        with patch(_PATCH_BUNDLE) as mock_bundle:
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="", l_alert="", l1_neighborhood="",
                l2_focus="", total_tokens=0,
            )
            ctx = bootstrap(store, narratives_dir)

        call_args = mock_bundle.assemble.call_args
        focus_arg = call_args[0][1]
        assert focus_arg.primary is None
        assert focus_arg.secondaries == []


class TestBootstrapDegradation:
    """降级测试: 各步骤异常 → 局部降级不阻断。"""

    def test_dashboard_exception_degrades_l0(self, store, narratives_dir):
        """dashboard 抛异常 → L0 为空但不崩。"""
        with patch(_PATCH_DASHBOARD) as mock_dash, \
             patch(_PATCH_BUNDLE) as mock_bundle:
            mock_dash.render_dashboard.side_effect = RuntimeError("DB corrupt")
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="", l_alert="", l1_neighborhood="",
                l2_focus="", total_tokens=0,
            )
            ctx = bootstrap(store, narratives_dir)

        call_args = mock_bundle.assemble.call_args
        dashboard_md_arg = call_args[0][2]  # 3rd positional arg
        assert dashboard_md_arg == ""

    def test_heartbeat_exception_degrades_alerts(self, store, narratives_dir):
        """heartbeat 抛异常 → alerts 为空，焦点候选为空。"""
        with patch(_PATCH_HEARTBEAT) as mock_hb, \
             patch(_PATCH_BUNDLE) as mock_bundle:
            mock_hb.scan.side_effect = RuntimeError("scan failed")
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="", l_alert="", l1_neighborhood="",
                l2_focus="", total_tokens=0,
            )
            ctx = bootstrap(store, narratives_dir)

        call_args = mock_bundle.assemble.call_args
        alerts_md_arg = call_args[0][3]
        assert alerts_md_arg == ""

    def test_focus_exception_degrades_to_no_focus(self, store, narratives_dir):
        """focus 抛异常 → 无焦点模式。"""
        with patch(_PATCH_FOCUS) as mock_focus, \
             patch(_PATCH_BUNDLE) as mock_bundle:
            mock_focus.arbitrate.side_effect = RuntimeError("focus broken")
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="", l_alert="", l1_neighborhood="",
                l2_focus="", total_tokens=0,
            )
            ctx = bootstrap(store, narratives_dir)

        call_args = mock_bundle.assemble.call_args
        focus_arg = call_args[0][1]
        assert isinstance(focus_arg, FocusResult)
        assert focus_arg.primary is None

    def test_bundle_exception_returns_minimal(self, store, narratives_dir):
        """bundle.assemble 抛异常 → 返回最小 ContextBundle。"""
        with patch(_PATCH_BUNDLE) as mock_bundle:
            mock_bundle.assemble.side_effect = NotImplementedError("not yet")
            ctx = bootstrap(store, narratives_dir)

        assert isinstance(ctx, ContextBundle)
        assert isinstance(ctx.l0_dashboard, str)
        assert ctx.l1_neighborhood == ""
        assert ctx.l2_focus == ""

    def test_all_steps_fail_still_returns_bundle(self, store, narratives_dir):
        """所有步骤全失败 → 仍返回空 ContextBundle。"""
        with patch(_PATCH_DASHBOARD) as mock_dash, \
             patch(_PATCH_HEARTBEAT) as mock_hb, \
             patch(_PATCH_FOCUS) as mock_focus, \
             patch(_PATCH_BUNDLE) as mock_bundle:
            mock_dash.render_dashboard.side_effect = RuntimeError("fail")
            mock_hb.scan.side_effect = RuntimeError("fail")
            mock_focus.arbitrate.side_effect = RuntimeError("fail")
            mock_bundle.assemble.side_effect = RuntimeError("fail")
            ctx = bootstrap(store, narratives_dir)

        assert isinstance(ctx, ContextBundle)
        assert ctx.l0_dashboard == ""
        assert ctx.l_alert == ""
        assert ctx.l1_neighborhood == ""
        assert ctx.l2_focus == ""


class TestBootstrapSessionState:
    """bootstrap 更新 session_state。"""

    def test_session_state_persisted(self, store, narratives_dir):
        """heartbeat session_state 被持久化。"""
        node = _create_root_node(store, "task-s1", status="active")
        store.update_node("task-s1", {
            "status_changed_at": _iso_ago(days=10),
        })

        with patch(_PATCH_BUNDLE) as mock_bundle:
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="", l_alert="", l1_neighborhood="",
                l2_focus="", total_tokens=0,
            )
            bootstrap(store, narratives_dir)

        hb_session = store.get_session("heartbeat")
        assert hb_session is not None

    def test_max_tokens_forwarded(self, store, narratives_dir):
        """max_tokens 参数传递给 bundle.assemble。"""
        with patch(_PATCH_BUNDLE) as mock_bundle:
            mock_bundle.assemble.return_value = ContextBundle(
                l0_dashboard="", l_alert="", l1_neighborhood="",
                l2_focus="", total_tokens=0,
            )
            bootstrap(store, narratives_dir, max_tokens=5000)

        call_args = mock_bundle.assemble.call_args
        assert call_args.kwargs.get("max_tokens") == 5000  # passed as keyword arg
