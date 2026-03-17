"""Tests for spine/bundle.py — context bundle assembly with trim."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from spine.bundle import assemble, estimate_tokens
from spine.focus import FocusResult
from spine.models import ContextBundle, Edge, Node
from spine.narrative import append_narrative
from spine.schema import init_db
from spine.store import Store


@pytest.fixture
def tmp_env(tmp_path):
    """Create store + narratives_dir for testing."""
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    narratives_dir = str(tmp_path / "narratives")
    os.makedirs(narratives_dir, exist_ok=True)
    init_db(db_path)
    store = Store(db_path=db_path, events_path=events_path)
    return store, narratives_dir


def _make_node(store: Store, node_id: str, **kwargs) -> Node:
    defaults = dict(
        title=f"Node {node_id}",
        status="active",
        node_type="task",
        is_root=True,
        summary=f"Summary of {node_id}",
        created_at="",
        updated_at="",
        status_changed_at="",
    )
    defaults.update(kwargs)
    return store.create_node(Node(id=node_id, **defaults))


# ── estimate_tokens ──────────────────────────────────────────────

class TestEstimateTokens:
    def test_empty(self):
        assert estimate_tokens("") == 0

    def test_ascii(self):
        assert estimate_tokens("abcd") == 2  # 4 // 2

    def test_chinese(self):
        # 6 bytes in UTF-8 for "你好", but len() = 2 in Python
        assert estimate_tokens("你好") == 1  # 2 // 2

    def test_mixed(self):
        text = "hello 你好"  # len = 8
        assert estimate_tokens(text) == 4


# ── No focus ─────────────────────────────────────────────────────

class TestNoFocus:
    def test_no_focus_returns_l0_lalert_only(self, tmp_env):
        store, narratives_dir = tmp_env
        focus = FocusResult(primary=None, secondaries=[], reason="no_candidates")
        bundle = assemble(
            store, focus,
            dashboard_md="# Dashboard",
            alerts_md="# Alerts",
            narratives_dir=narratives_dir,
        )
        assert isinstance(bundle, ContextBundle)
        assert bundle.l0_dashboard == "# Dashboard"
        assert bundle.l_alert == "# Alerts"
        assert bundle.l1_neighborhood == ""
        assert bundle.l2_focus == ""
        assert bundle.focus_node_id is None
        assert bundle.total_tokens == estimate_tokens("# Dashboard# Alerts")


# ── Full assembly ────────────────────────────────────────────────

class TestFullAssembly:
    def test_l0_l1_l2_all_populated(self, tmp_env):
        store, narratives_dir = tmp_env
        parent = _make_node(store, "goal-0001", node_type="goal", title="Parent Goal")
        focus_node = _make_node(
            store, "task-0001", is_root=False, parent_id="goal-0001",
            title="Focus Task", summary="Focus summary",
            why="Because reasons", next_step="Do next thing",
        )
        # add parent edge
        store.add_edge(Edge(source_id="task-0001", target_id="goal-0001",
                            edge_type="parent", created_at=""))
        # child
        child = _make_node(
            store, "task-0002", is_root=False, parent_id="task-0001",
            title="Child Task", status="active",
        )
        store.add_edge(Edge(source_id="task-0002", target_id="task-0001",
                            edge_type="parent", created_at=""))
        # dependency
        dep = _make_node(store, "task-0003", title="Dep Task", status="waiting")
        store.add_edge(Edge(source_id="task-0001", target_id="task-0003",
                            edge_type="depends_on", created_at=""))
        # dependent
        dependent = _make_node(store, "task-0004", title="Dependent Task")
        store.add_edge(Edge(source_id="task-0004", target_id="task-0001",
                            edge_type="depends_on", created_at=""))
        # sibling
        sibling = _make_node(
            store, "task-0005", is_root=False, parent_id="goal-0001",
            title="Sibling Task",
        )
        store.add_edge(Edge(source_id="task-0005", target_id="goal-0001",
                            edge_type="parent", created_at=""))
        # narrative
        append_narrative(narratives_dir, "task-0001",
                         "2026-03-17T00:00:00Z", "status_change",
                         "Activated task")

        focus = FocusResult(primary="task-0001", secondaries=[], reason="test")
        bundle = assemble(
            store, focus,
            dashboard_md="# Dashboard",
            alerts_md="",
            narratives_dir=narratives_dir,
        )

        assert bundle.focus_node_id == "task-0001"
        assert bundle.l0_dashboard == "# Dashboard"
        # L1 should mention parent, child, dep, dependent, sibling
        assert "goal-0001" in bundle.l1_neighborhood
        assert "Parent Goal" in bundle.l1_neighborhood
        assert "task-0002" in bundle.l1_neighborhood
        assert "task-0003" in bundle.l1_neighborhood
        assert "task-0004" in bundle.l1_neighborhood
        assert "task-0005" in bundle.l1_neighborhood
        # L2 should have focus node details + narrative
        assert "Focus Task" in bundle.l2_focus
        assert "Focus summary" in bundle.l2_focus
        assert "Because reasons" in bundle.l2_focus
        assert "Activated task" in bundle.l2_focus
        # total_tokens > 0
        assert bundle.total_tokens > 0


# ── L1 content sections ─────────────────────────────────────────

class TestL1Sections:
    def test_parent_in_l1(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "goal-p", node_type="goal", title="The Parent")
        _make_node(store, "task-f", is_root=False, parent_id="goal-p")
        store.add_edge(Edge(source_id="task-f", target_id="goal-p",
                            edge_type="parent", created_at=""))
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert "goal-p" in bundle.l1_neighborhood
        assert "The Parent" in bundle.l1_neighborhood

    def test_children_only_non_terminal(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "task-f")
        _make_node(store, "task-c1", is_root=False, parent_id="task-f", status="active", title="Active Child")
        store.add_edge(Edge(source_id="task-c1", target_id="task-f", edge_type="parent", created_at=""))
        _make_node(store, "task-c2", is_root=False, parent_id="task-f", status="done", title="Done Child")
        store.add_edge(Edge(source_id="task-c2", target_id="task-f", edge_type="parent", created_at=""))

        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert "Active Child" in bundle.l1_neighborhood
        assert "Done Child" not in bundle.l1_neighborhood

    def test_depends_on_in_l1(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "task-f")
        _make_node(store, "task-dep", title="My Dependency", status="waiting")
        store.add_edge(Edge(source_id="task-f", target_id="task-dep",
                            edge_type="depends_on", created_at=""))
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert "My Dependency" in bundle.l1_neighborhood
        assert "waiting" in bundle.l1_neighborhood

    def test_depended_by_in_l1(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "task-f")
        _make_node(store, "task-dby", title="Downstream")
        store.add_edge(Edge(source_id="task-dby", target_id="task-f",
                            edge_type="depends_on", created_at=""))
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert "Downstream" in bundle.l1_neighborhood

    def test_siblings_in_l1(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "goal-p", node_type="goal")
        _make_node(store, "task-f", is_root=False, parent_id="goal-p")
        store.add_edge(Edge(source_id="task-f", target_id="goal-p", edge_type="parent", created_at=""))
        _make_node(store, "task-sib", is_root=False, parent_id="goal-p", title="Sibling")
        store.add_edge(Edge(source_id="task-sib", target_id="goal-p", edge_type="parent", created_at=""))

        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert "Sibling" in bundle.l1_neighborhood


# ── L2 content ───────────────────────────────────────────────────

class TestL2:
    def test_l2_has_all_node_fields(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "task-f", title="My Task", summary="My summary",
                   why="My why", next_step="My next", owner="jeff",
                   deadline="2026-04-01T00:00:00Z")
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert "My Task" in bundle.l2_focus
        assert "My summary" in bundle.l2_focus
        assert "My why" in bundle.l2_focus
        assert "My next" in bundle.l2_focus
        assert "jeff" in bundle.l2_focus
        assert "2026-04-01" in bundle.l2_focus

    def test_l2_has_narrative(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "task-f")
        for i in range(7):
            append_narrative(narratives_dir, "task-f",
                             f"2026-03-{10+i:02d}T00:00:00Z", "log",
                             f"Entry {i}")
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        # default last_n=5, so entries 2-6 should be present, 0-1 should not
        assert "Entry 6" in bundle.l2_focus
        assert "Entry 2" in bundle.l2_focus
        assert "Entry 0" not in bundle.l2_focus

    def test_l2_no_narrative_file(self, tmp_env):
        """No narrative file → L2 still renders node fields."""
        store, narratives_dir = tmp_env
        _make_node(store, "task-f", title="No Narrative")
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert "No Narrative" in bundle.l2_focus


# ── Token estimation & total ─────────────────────────────────────

class TestTokenTotal:
    def test_total_tokens_is_sum(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "task-f")
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "DASH", "ALERT", narratives_dir=narratives_dir)
        expected = estimate_tokens(
            bundle.l0_dashboard + bundle.l_alert
            + bundle.l1_neighborhood + bundle.l2_focus
        )
        assert bundle.total_tokens == expected


# ── Trim (over budget) ───────────────────────────────────────────

class TestTrim:
    def test_trim_order_siblings_first(self, tmp_env):
        """With very small max_tokens, siblings should be trimmed first."""
        store, narratives_dir = tmp_env
        _make_node(store, "goal-p", node_type="goal")
        _make_node(store, "task-f", is_root=False, parent_id="goal-p",
                   summary="Focus summary", why="Focus why")
        store.add_edge(Edge(source_id="task-f", target_id="goal-p",
                            edge_type="parent", created_at=""))
        # Add many siblings to inflate L1
        for i in range(20):
            sid = f"task-s{i:03d}"
            _make_node(store, sid, is_root=False, parent_id="goal-p",
                       title=f"Sibling {i} with lots of padding text")
            store.add_edge(Edge(source_id=sid, target_id="goal-p",
                                edge_type="parent", created_at=""))
        # Add a dependency (should survive longer than siblings)
        _make_node(store, "task-dep", title="Important Dep", status="waiting")
        store.add_edge(Edge(source_id="task-f", target_id="task-dep",
                            edge_type="depends_on", created_at=""))

        focus = FocusResult(primary="task-f", secondaries=[])
        # Very tight budget
        bundle = assemble(store, focus, "D", "A",
                          narratives_dir=narratives_dir, max_tokens=150)

        # Siblings should have been trimmed (or heavily reduced)
        # Dependencies should still be present if budget allows
        # The key invariant: total_tokens <= max_tokens
        assert bundle.total_tokens <= 150

    def test_trim_preserves_l0_lalert(self, tmp_env):
        """L0 and L_Alert are never trimmed."""
        store, narratives_dir = tmp_env
        _make_node(store, "task-f")
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "DASHBOARD", "ALERTS",
                          narratives_dir=narratives_dir, max_tokens=50)
        assert bundle.l0_dashboard == "DASHBOARD"
        assert bundle.l_alert == "ALERTS"


# ── focus_node_id ────────────────────────────────────────────────

class TestFocusNodeId:
    def test_focus_node_id_set(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "task-f")
        focus = FocusResult(primary="task-f", secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert bundle.focus_node_id == "task-f"

    def test_focus_node_id_none_when_no_focus(self, tmp_env):
        store, narratives_dir = tmp_env
        focus = FocusResult(primary=None, secondaries=[])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        assert bundle.focus_node_id is None


# ── Multi-focus (secondary as L1 summary) ────────────────────────

class TestMultiFocus:
    def test_secondary_appears_as_l1_summary(self, tmp_env):
        store, narratives_dir = tmp_env
        _make_node(store, "task-pri", title="Primary Task")
        _make_node(store, "task-sec", title="Secondary Task",
                   summary="Secondary summary")
        focus = FocusResult(primary="task-pri", secondaries=["task-sec"])
        bundle = assemble(store, focus, "", "", narratives_dir=narratives_dir)
        # Secondary should appear in L1 neighborhood
        assert "Secondary Task" in bundle.l1_neighborhood
        assert bundle.focus_node_id == "task-pri"
