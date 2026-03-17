"""v0 验收清单第3层: 端到端冒烟测试 — 全部场景。"""

import json
import os
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
    r = env["executor"].execute(cmd_id, tool, args)
    return r


class TestScenarioA_BasicLifecycle:
    """场景A: goal→project→task 完整生命周期。"""

    def test_full_lifecycle(self, env):
        ex = env["executor"]
        store = env["store"]

        # 创建 goal (is_root=true)
        r = _exec(env, "a1", "create_node", {
            "title": "Launch Product", "node_type": "goal", "is_root": True,
            "summary": "Ship MVP"
        })
        assert r.success
        goal_id = r.data["id"]
        assert goal_id.startswith("goal-")

        # 创建 project, attach to goal
        r = _exec(env, "a2", "create_node", {
            "title": "Backend", "node_type": "project", "summary": "API layer"
        })
        proj_id = r.data["id"]
        _exec(env, "a3", "attach_node", {"node_id": proj_id, "parent_id": goal_id})

        # 创建 task, attach to project
        r = _exec(env, "a4", "create_node", {
            "title": "Auth module", "node_type": "task", "summary": "JWT auth"
        })
        task_id = r.data["id"]
        _exec(env, "a5", "attach_node", {"node_id": task_id, "parent_id": proj_id})

        # 验证三层树结构
        children = store.get_children(proj_id)
        assert any(c.id == task_id for c in children)
        parent = store.get_parent(task_id)
        assert parent.id == proj_id
        gp = store.get_parent(proj_id)
        assert gp.id == goal_id

        # task: inbox → active
        r = _exec(env, "a6", "update_status", {"node_id": task_id, "new_status": "active"})
        assert r.success

        # task: active → done
        r = _exec(env, "a7", "update_status", {"node_id": task_id, "new_status": "done"})
        assert r.success

        # project: inbox → active → done (task已终态)
        r = _exec(env, "a8", "update_status", {"node_id": proj_id, "new_status": "active"})
        assert r.success
        r = _exec(env, "a9", "update_status", {"node_id": proj_id, "new_status": "done"})
        assert r.success

        # goal: inbox → active → done (project已终态)
        r = _exec(env, "a10", "update_status", {"node_id": goal_id, "new_status": "active"})
        assert r.success
        r = _exec(env, "a11", "update_status", {"node_id": goal_id, "new_status": "done"})
        assert r.success

        assert store.get_node(goal_id).status == "done"
        assert store.get_node(proj_id).status == "done"
        assert store.get_node(task_id).status == "done"


class TestScenarioB_DependencyAndBlocking:
    """场景B: 依赖关系与阻塞。"""

    def test_dependency_lifecycle(self, env):
        store = env["store"]

        r1 = _exec(env, "b1", "create_node", {"title": "A", "node_type": "task", "is_root": True, "summary": "A"})
        r2 = _exec(env, "b2", "create_node", {"title": "B", "node_type": "task", "is_root": True, "summary": "B"})
        a_id, b_id = r1.data["id"], r2.data["id"]

        # B depends on A
        r = _exec(env, "b3", "add_dependency", {"source_id": b_id, "target_id": a_id})
        assert r.success

        # Activate both
        _exec(env, "b4", "update_status", {"node_id": a_id, "new_status": "active"})
        _exec(env, "b5", "update_status", {"node_id": b_id, "new_status": "active"})

        # Check B is blocked (via risk engine)
        from spine.risk import compute_risks
        b_node = store.get_node(b_id)
        deps = store.get_dependencies(b_id)
        risks = compute_risks(b_node, deps)
        assert risks.blocked is True

        # Complete A
        _exec(env, "b6", "update_status", {"node_id": a_id, "new_status": "done"})

        # B should no longer be blocked
        b_node = store.get_node(b_id)
        deps = store.get_dependencies(b_id)
        risks = compute_risks(b_node, deps)
        assert risks.blocked is False

        # Reverse dependency (cycle) → must fail
        r = _exec(env, "b7", "add_dependency", {"source_id": a_id, "target_id": b_id})
        assert r.success is False


class TestScenarioC_StatusRollback:
    """场景C: 状态回退。"""

    def test_done_to_active_with_reason(self, env):
        r = _exec(env, "c1", "create_node", {"title": "Rollback", "node_type": "task", "is_root": True, "summary": "test"})
        nid = r.data["id"]
        _exec(env, "c2", "update_status", {"node_id": nid, "new_status": "active"})
        _exec(env, "c3", "update_status", {"node_id": nid, "new_status": "done"})

        # done → active (needs reason)
        r = _exec(env, "c4", "update_status", {"node_id": nid, "new_status": "active"})
        assert r.success is False  # missing reason

        r = _exec(env, "c5", "update_status", {"node_id": nid, "new_status": "active", "reason": "Found a bug"})
        assert r.success
        assert env["store"].get_node(nid).status == "active"

    def test_dropped_to_inbox_with_reason(self, env):
        r = _exec(env, "c6", "create_node", {"title": "Drop", "node_type": "task", "is_root": True})
        nid = r.data["id"]
        _exec(env, "c7", "update_status", {"node_id": nid, "new_status": "dropped"})

        # dropped → inbox (needs reason)
        r = _exec(env, "c8", "update_status", {"node_id": nid, "new_status": "inbox"})
        assert r.success is False

        r = _exec(env, "c9", "update_status", {"node_id": nid, "new_status": "inbox", "reason": "Revived"})
        assert r.success


class TestScenarioD_ArchiveBoundary:
    """场景D: 归档边界。"""

    def test_attach_to_archived_rejected(self, env):
        store = env["store"]

        r = _exec(env, "d1", "create_node", {"title": "Target", "node_type": "task", "is_root": True, "summary": "t"})
        target_id = r.data["id"]
        _exec(env, "d2", "update_status", {"node_id": target_id, "new_status": "active"})
        _exec(env, "d3", "update_status", {"node_id": target_id, "new_status": "done"})

        # Manually archive it
        from spine.archive import archive_nodes
        store.update_node(target_id, {"status_changed_at": "2020-01-01T00:00:00+00:00"})
        archive_nodes(store, [target_id])

        # Try to attach to archived
        r2 = _exec(env, "d4", "create_node", {"title": "Child", "node_type": "task"})
        child_id = r2.data["id"]
        r = _exec(env, "d5", "attach_node", {"node_id": child_id, "parent_id": target_id})
        assert r.success is False

    def test_dependency_to_archived_rejected(self, env):
        store = env["store"]

        r1 = _exec(env, "d6", "create_node", {"title": "Archived", "node_type": "task", "is_root": True, "summary": "a"})
        r2 = _exec(env, "d7", "create_node", {"title": "Active", "node_type": "task", "is_root": True, "summary": "b"})
        arc_id, act_id = r1.data["id"], r2.data["id"]

        _exec(env, "d8", "update_status", {"node_id": arc_id, "new_status": "active"})
        _exec(env, "d9", "update_status", {"node_id": arc_id, "new_status": "done"})

        from spine.archive import archive_nodes
        store.update_node(arc_id, {"status_changed_at": "2020-01-01T00:00:00+00:00"})
        archive_nodes(store, [arc_id])

        r = _exec(env, "d10", "add_dependency", {"source_id": act_id, "target_id": arc_id})
        assert r.success is False

    def test_unarchive_resets_status_changed_at(self, env):
        store = env["store"]

        r = _exec(env, "d11", "create_node", {"title": "Unarch", "node_type": "task", "is_root": True, "summary": "u"})
        nid = r.data["id"]
        _exec(env, "d12", "update_status", {"node_id": nid, "new_status": "active"})
        _exec(env, "d13", "update_status", {"node_id": nid, "new_status": "done"})

        store.update_node(nid, {"status_changed_at": "2020-01-01T00:00:00+00:00"})
        from spine.archive import archive_nodes
        archive_nodes(store, [nid])
        assert store.get_node(nid).archived_at is not None

        r = _exec(env, "d14", "unarchive", {"node_id": nid})
        assert r.success
        node = store.get_node(nid)
        assert node.archived_at is None
        assert node.status_changed_at > "2026-01-01"


class TestScenarioE_AuditCompleteness:
    """场景E: 审计完整性。"""

    def test_audit_trail_complete(self, env):
        store = env["store"]

        _exec(env, "e1", "create_node", {"title": "A1", "node_type": "task", "is_root": True, "summary": "a1"})
        _exec(env, "e2", "create_node", {"title": "A2", "node_type": "task", "is_root": True})
        _exec(env, "e3", "update_field", {"node_id": store.list_nodes()[0].id, "field": "summary", "value": "updated"})

        count = store.flush_events()
        assert count >= 3

        with open(env["events_path"]) as f:
            lines = f.readlines()
        assert len(lines) >= 3

        for line in lines:
            event = json.loads(line)
            assert "tool_name" in event or "node_id" in event
            assert "timestamp" in event or "ts" in event


class TestScenarioF_Idempotency:
    """场景F: 幂等与崩溃安全。"""

    def test_idempotent_create(self, env):
        r1 = _exec(env, "f1", "create_node", {"title": "Idem", "node_type": "task", "is_root": True})
        r2 = _exec(env, "f1", "create_node", {"title": "Idem", "node_type": "task", "is_root": True})
        assert r1.data["id"] == r2.data["id"]

        nodes = [n for n in env["store"].list_nodes() if n.title == "Idem"]
        assert len(nodes) == 1


class TestScenarioG_ActionableErrors:
    """场景G: Actionable Errors。"""

    def test_three_distinct_actionable_errors(self, env):
        # Error 1: inbox→active without summary
        r1 = _exec(env, "g1", "create_node", {"title": "NoSum", "node_type": "task", "is_root": True})
        nid = r1.data["id"]
        r = _exec(env, "g2", "update_status", {"node_id": nid, "new_status": "active"})
        assert not r.success
        assert r.suggestion is not None or "summary" in (r.error or "").lower()

        # Error 2: illegal transition inbox→done
        r = _exec(env, "g3", "update_status", {"node_id": nid, "new_status": "done"})
        assert not r.success

        # Error 3: invalid field
        r = _exec(env, "g4", "update_field", {"node_id": nid, "field": "id", "value": "hacked"})
        assert not r.success
