"""End-to-end smoke test: full lifecycle through CommandExecutor."""

import json
import os
import tempfile
import pytest
from spine.schema import init_db
from spine.store import Store
from spine.command_executor import CommandExecutor


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


class TestFullLifecycle:
    """Create goal→project→task, transitions, dependency, archive-readiness."""

    def test_create_hierarchy(self, env):
        ex = env["executor"]

        # Create goal
        r1 = ex.execute("cmd-1", "create_node", {
            "title": "Launch Product", "node_type": "goal", "is_root": True,
            "summary": "Ship MVP by Q2"
        })
        assert r1.success
        goal_id = r1.data["id"]
        assert goal_id.startswith("goal-")

        # Create project under goal
        r2 = ex.execute("cmd-2", "create_node", {
            "title": "Backend API", "node_type": "project"
        })
        assert r2.success
        proj_id = r2.data["id"]

        # Attach project to goal
        r3 = ex.execute("cmd-3", "attach_node", {
            "node_id": proj_id, "parent_id": goal_id
        })
        assert r3.success

        # Create task under project
        r4 = ex.execute("cmd-4", "create_node", {
            "title": "Implement auth", "node_type": "task",
            "summary": "JWT-based auth"
        })
        assert r4.success
        task_id = r4.data["id"]

        r5 = ex.execute("cmd-5", "attach_node", {
            "node_id": task_id, "parent_id": proj_id
        })
        assert r5.success

        # Verify hierarchy
        store = env["store"]
        task = store.get_node(task_id)
        assert task.parent_id == proj_id
        assert task.is_root is False

        proj = store.get_node(proj_id)
        assert proj.parent_id == goal_id

        children = store.get_children(proj_id)
        assert any(c.id == task_id for c in children)

    def test_status_lifecycle(self, env):
        ex = env["executor"]

        # Create and activate
        r1 = ex.execute("cmd-10", "create_node", {
            "title": "Write docs", "node_type": "task", "is_root": True,
            "summary": "API documentation"
        })
        node_id = r1.data["id"]

        r2 = ex.execute("cmd-11", "update_status", {
            "node_id": node_id, "new_status": "active"
        })
        assert r2.success

        # Active → done
        r3 = ex.execute("cmd-12", "update_status", {
            "node_id": node_id, "new_status": "done"
        })
        assert r3.success

        node = env["store"].get_node(node_id)
        assert node.status == "done"

    def test_dependency_and_cycle_rejection(self, env):
        ex = env["executor"]

        r1 = ex.execute("cmd-20", "create_node", {
            "title": "A", "node_type": "task", "is_root": True
        })
        r2 = ex.execute("cmd-21", "create_node", {
            "title": "B", "node_type": "task", "is_root": True
        })
        a_id = r1.data["id"]
        b_id = r2.data["id"]

        # A depends on B
        r3 = ex.execute("cmd-22", "add_dependency", {
            "source_id": a_id, "target_id": b_id
        })
        assert r3.success

        # B depends on A → cycle → must fail
        r4 = ex.execute("cmd-23", "add_dependency", {
            "source_id": b_id, "target_id": a_id
        })
        assert r4.success is False
        assert "cycle" in r4.error.lower() or "环" in r4.error

    def test_idempotency(self, env):
        ex = env["executor"]

        r1 = ex.execute("cmd-30", "create_node", {
            "title": "Idempotent", "node_type": "task", "is_root": True
        })
        r2 = ex.execute("cmd-30", "create_node", {
            "title": "Idempotent", "node_type": "task", "is_root": True
        })

        assert r1.data["id"] == r2.data["id"]
        nodes = env["store"].list_nodes()
        matching = [n for n in nodes if n.title == "Idempotent"]
        assert len(matching) == 1

    def test_narrative_generated(self, env):
        ex = env["executor"]

        r1 = ex.execute("cmd-40", "create_node", {
            "title": "Narrative Test", "node_type": "task", "is_root": True
        })
        node_id = r1.data["id"]

        # Check narrative file exists
        narr_path = os.path.join(env["narratives_dir"], "{}.md".format(node_id))
        assert os.path.exists(narr_path)

        with open(narr_path) as f:
            content = f.read()
        assert "Narrative Test" in content or "create" in content.lower()

    def test_audit_trail(self, env):
        ex = env["executor"]

        r1 = ex.execute("cmd-50", "create_node", {
            "title": "Audit Test", "node_type": "task", "is_root": True
        })

        # Flush events
        count = env["store"].flush_events()
        assert count >= 1

        # Check events.jsonl
        with open(env["events_path"]) as f:
            lines = f.readlines()
        assert len(lines) >= 1
        event = json.loads(lines[0])
        assert "tool_name" in event or "node_id" in event

    def test_append_log(self, env):
        ex = env["executor"]

        r1 = ex.execute("cmd-60", "create_node", {
            "title": "Log Test", "node_type": "task", "is_root": True
        })
        node_id = r1.data["id"]

        r2 = ex.execute("cmd-61", "append_log", {
            "node_id": node_id, "content": "Had a meeting about this"
        })
        assert r2.success

    def test_search_nodes(self, env):
        ex = env["executor"]

        ex.execute("cmd-70", "create_node", {
            "title": "Search A", "node_type": "goal", "is_root": True
        })
        ex.execute("cmd-71", "create_node", {
            "title": "Search B", "node_type": "task", "is_root": True
        })

        r = ex.execute("cmd-72", "search_nodes", {"status": "inbox"})
        assert r.success
        assert len(r.data["nodes"]) >= 2
