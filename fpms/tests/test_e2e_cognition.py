"""E2E integration tests for v1 cognition layer:
cold start → risk → dashboard → heartbeat → focus → bundle → recovery.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from spine.schema import init_db
from spine.store import Store
from spine.command_executor import CommandExecutor
from spine.models import Node


@pytest.fixture
def env(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    narratives_dir = str(tmp_path / "narratives")
    os.makedirs(narratives_dir, exist_ok=True)
    init_db(db_path)
    store = Store(db_path=db_path, events_path=events_path)
    executor = CommandExecutor(store, narratives_dir=narratives_dir)
    return {"store": store, "executor": executor, "events_path": events_path,
            "narratives_dir": narratives_dir}


def _exec(env, cmd_id, tool, args):
    return env["executor"].execute(cmd_id, tool, args)


def _seed_project(env):
    """Create a realistic project: goal → 2 tasks with dependency."""
    _exec(env, "s1", "create_node", {
        "title": "Anext 信贷", "node_type": "goal", "is_root": True,
        "summary": "700万信贷额度"
    })
    goal = env["store"].list_nodes()[0]
    _exec(env, "s2", "update_status", {"node_id": goal.id, "new_status": "active"})

    _exec(env, "s3", "create_node", {
        "title": "法务审核", "node_type": "task", "summary": "审核担保条款"
    })
    _exec(env, "s4", "create_node", {
        "title": "利率谈判", "node_type": "task", "summary": "谈到7.5%以下"
    })
    nodes = env["store"].list_nodes()
    tasks = [n for n in nodes if n.node_type == "task"]
    t1, t2 = tasks[0], tasks[1]

    _exec(env, "s5", "attach_node", {"node_id": t1.id, "parent_id": goal.id})
    _exec(env, "s6", "attach_node", {"node_id": t2.id, "parent_id": goal.id})
    _exec(env, "s7", "update_status", {"node_id": t1.id, "new_status": "active"})
    _exec(env, "s8", "update_status", {"node_id": t2.id, "new_status": "active"})
    _exec(env, "s9", "add_dependency", {"source_id": t2.id, "target_id": t1.id})
    _exec(env, "s10", "append_log", {"node_id": t1.id, "content": "法务团队开始审核"})

    return goal, t1, t2


class TestRiskToDashboard:
    """风险标记 → 看板渲染。"""

    def test_blocked_shows_in_dashboard(self, env):
        goal, t1, t2 = _seed_project(env)

        from spine.dashboard import render_dashboard
        md = render_dashboard(env["store"])

        assert "blocked" in md.lower() or "🚫" in md
        assert t2.id in md  # 被阻塞的节点出现
        assert goal.id in md

    def test_at_risk_shows_in_dashboard(self, env):
        store = env["store"]
        goal, t1, t2 = _seed_project(env)

        # Set deadline to 24h from now
        deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        _exec(env, "ar1", "update_field", {
            "node_id": t1.id, "field": "deadline", "value": deadline
        })

        from spine.dashboard import render_dashboard
        md = render_dashboard(store)
        assert "at-risk" in md.lower() or "🚨" in md

    def test_risk_marks_are_computed_not_stored(self, env):
        """风险标记不在 DB 中，每次实时计算。"""
        goal, t1, t2 = _seed_project(env)

        from spine.risk import batch_compute_risks
        risks = batch_compute_risks(env["store"])

        # t2 should be blocked
        assert risks[t2.id].blocked is True
        assert risks[t1.id].blocked is False

        # Complete t1 → t2 should unblock
        _exec(env, "rb1", "update_status", {"node_id": t1.id, "new_status": "done"})
        risks2 = batch_compute_risks(env["store"])
        assert risks2[t2.id].blocked is False


class TestHeartbeatAlerts:
    """心跳 → 告警生成。"""

    def test_stale_node_generates_alert(self, env):
        store = env["store"]
        r = _exec(env, "h1", "create_node", {
            "title": "Stale Task", "node_type": "task", "is_root": True, "summary": "s"
        })
        nid = r.data["id"]
        _exec(env, "h2", "update_status", {"node_id": nid, "new_status": "active"})

        # Backdate status_changed_at to 10 days ago
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        store.update_node(nid, {"status_changed_at": old_time})

        from spine.heartbeat import scan
        result = scan(store, {})
        assert len(result.alerts) > 0
        stale_alerts = [a for a in result.alerts if "stale" in a.alert_type]
        assert len(stale_alerts) > 0

    def test_dedup_suppresses_repeat_alerts(self, env):
        store = env["store"]
        r = _exec(env, "hd1", "create_node", {
            "title": "Stale2", "node_type": "task", "is_root": True, "summary": "s"
        })
        nid = r.data["id"]
        _exec(env, "hd2", "update_status", {"node_id": nid, "new_status": "active"})
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        store.update_node(nid, {"status_changed_at": old_time})

        from spine.heartbeat import scan
        state = {}
        r1 = scan(store, state)
        r2 = scan(store, state)

        # Second scan should suppress the same alert
        assert r2.suppressed_count > 0 or len(r2.alerts) < len(r1.alerts)


class TestFocusSwitchAndBundle:
    """焦点切换 → Bundle 重建。"""

    def test_shift_focus_rebuilds_l2(self, env):
        goal, t1, t2 = _seed_project(env)
        store = env["store"]

        from spine.focus import shift_focus, FocusResult
        from spine.bundle import assemble

        result = shift_focus(store, t1.id)
        assert result.primary == t1.id

        bundle = assemble(store, result, "# Dashboard", "",
                          env["narratives_dir"], max_tokens=10000)

        assert bundle.focus_node_id == t1.id
        assert t1.id in bundle.l2_focus or "法务审核" in bundle.l2_focus
        assert bundle.l1_neighborhood != ""  # Should have parent/siblings

    def test_focus_switch_changes_l2(self, env):
        goal, t1, t2 = _seed_project(env)
        store = env["store"]

        from spine.focus import shift_focus
        from spine.bundle import assemble

        # Focus on t1
        r1 = shift_focus(store, t1.id)
        b1 = assemble(store, r1, "", "", env["narratives_dir"])
        assert "法务审核" in b1.l2_focus

        # Switch to t2
        r2 = shift_focus(store, t2.id)
        b2 = assemble(store, r2, "", "", env["narratives_dir"])
        assert "利率谈判" in b2.l2_focus
        assert b2.focus_node_id == t2.id


class TestColdStartBootstrap:
    """冷启动 → 完整认知包。"""

    def test_bootstrap_assembles_full_context(self, env):
        goal, t1, t2 = _seed_project(env)

        from spine.recovery import bootstrap
        bundle = bootstrap(env["store"], env["narratives_dir"])

        assert isinstance(bundle.l0_dashboard, str)
        assert len(bundle.l0_dashboard) > 0  # Should have dashboard
        assert bundle.total_tokens > 0

    def test_bootstrap_empty_store_no_crash(self, env):
        from spine.recovery import bootstrap
        bundle = bootstrap(env["store"], env["narratives_dir"])

        assert bundle.l0_dashboard is not None
        assert bundle.total_tokens >= 0

    def test_bootstrap_with_stale_generates_alerts(self, env):
        store = env["store"]
        r = _exec(env, "bs1", "create_node", {
            "title": "Old Task", "node_type": "task", "is_root": True, "summary": "s"
        })
        nid = r.data["id"]
        _exec(env, "bs2", "update_status", {"node_id": nid, "new_status": "active"})
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        store.update_node(nid, {"status_changed_at": old_time})

        from spine.recovery import bootstrap
        bundle = bootstrap(store, env["narratives_dir"])

        # L_alert should contain the stale warning
        assert "告警" in bundle.l_alert or "stale" in bundle.l_alert.lower() or nid in bundle.l_alert


class TestRollupIntegration:
    """Rollup 冒泡集成。"""

    def test_rollup_reflects_child_status(self, env):
        goal, t1, t2 = _seed_project(env)

        from spine.rollup import compute_rollup
        rollup = compute_rollup(env["store"], goal.id)
        assert rollup == "active"  # Has active children

        # Complete both tasks
        _exec(env, "ru1", "update_status", {"node_id": t1.id, "new_status": "done"})
        _exec(env, "ru2", "update_status", {"node_id": t2.id, "new_status": "done"})

        rollup2 = compute_rollup(env["store"], goal.id)
        assert rollup2 == "done"  # All children done


class TestArchiveIntegration:
    """归档全链路。"""

    def test_archive_scan_and_execute(self, env):
        store = env["store"]
        r = _exec(env, "ai1", "create_node", {
            "title": "Archive Me", "node_type": "task", "is_root": True, "summary": "a"
        })
        nid = r.data["id"]
        _exec(env, "ai2", "update_status", {"node_id": nid, "new_status": "active"})
        _exec(env, "ai3", "update_status", {"node_id": nid, "new_status": "done"})

        # Backdate to pass cooldown
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        store.update_node(nid, {"status_changed_at": old_time})

        from spine.archive import scan_archive_candidates, archive_nodes
        candidates = scan_archive_candidates(store)
        assert nid in candidates

        count = archive_nodes(store, [nid])
        assert count == 1
        assert store.get_node(nid).archived_at is not None

        # Should not show in dashboard
        from spine.dashboard import render_dashboard
        md = render_dashboard(store)
        assert nid not in md


class TestCompressionIntegration:
    """叙事压缩集成。"""

    def test_compress_long_narrative(self, env):
        r = _exec(env, "ci1", "create_node", {
            "title": "Compress Me", "node_type": "task", "is_root": True
        })
        nid = r.data["id"]

        # Generate enough narrative to trigger compression
        for i in range(60):
            _exec(env, f"ci-log-{i}", "append_log", {
                "node_id": nid, "content": f"Info update #{i}: 进展正常，无异常"
            })

        from spine.compression import should_compress, compress_narrative
        if should_compress(env["narratives_dir"], nid, threshold_tokens=500):
            result = compress_narrative(env["narratives_dir"], nid)
            assert len(result) > 0
            # Compressed file should exist
            compressed_path = os.path.join(env["narratives_dir"], f"{nid}.compressed.md")
            assert os.path.exists(compressed_path)


class TestSpineCLIIntegration:
    """spine.py CLI 端到端。"""

    def test_cli_tool_roundtrip(self, env):
        """Test that CLI produces valid JSON output."""
        import subprocess
        spine_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spine.py")

        result = subprocess.run(
            ["python3", spine_path, "status"],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": os.path.dirname(spine_path)}
        )
        assert result.returncode == 0
        assert "FPMS Status" in result.stdout
