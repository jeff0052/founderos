"""Tests for spine/dashboard.py — render_dashboard L0 tree rendering."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from spine.models import Node, Edge
from spine.schema import init_db
from spine.store import Store
from spine.dashboard import render_dashboard


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_store(tmp_path) -> Store:
    db = str(tmp_path / "test.db")
    events = str(tmp_path / "events.jsonl")
    init_db(db)
    return Store(db, events)


def _create_node(
    store: Store,
    *,
    id: str = "",
    title: str = "Untitled",
    status: str = "inbox",
    node_type: str = "task",
    is_root: bool = False,
    parent_id: str | None = None,
    deadline: str | None = None,
    archived_at: str | None = None,
    summary: str | None = None,
    status_changed_at: str | None = None,
    created_at: str | None = None,
) -> Node:
    now = _utcnow_iso()
    node = Node(
        id=id,
        title=title,
        status=status,
        node_type=node_type,
        is_root=is_root,
        parent_id=parent_id,
        deadline=deadline,
        archived_at=archived_at,
        summary=summary,
        created_at=created_at or now,
        updated_at=now,
        status_changed_at=status_changed_at or now,
    )
    created = store.create_node(node)
    # store.create_node overrides timestamps with now; patch them if needed
    overrides = {}
    if status_changed_at:
        overrides["status_changed_at"] = status_changed_at
    if created_at:
        overrides["created_at"] = created_at
    if overrides:
        created = store.update_node(created.id, overrides)
    return created


# ── Empty store ─────────────────────────────────────────────────


class TestEmptyStore:
    def test_empty_store_returns_empty_string(self, tmp_path):
        store = _make_store(tmp_path)
        result = render_dashboard(store)
        assert result == ""

    def test_empty_store_with_custom_max_tokens(self, tmp_path):
        store = _make_store(tmp_path)
        result = render_dashboard(store, max_tokens=500)
        assert result == ""


# ── Zone 0 only (inbox floating) ───────────────────────────────


class TestZone0:
    def test_inbox_no_parent_shows_in_zone0(self, tmp_path):
        store = _make_store(tmp_path)
        n = _create_node(store, title="打电话给会计", status="inbox", is_root=True)
        result = render_dashboard(store)
        assert "📥" in result
        assert n.id in result
        assert "打电话给会计" in result

    def test_multiple_inbox_floating(self, tmp_path):
        store = _make_store(tmp_path)
        n1 = _create_node(store, title="任务A", status="inbox", is_root=True)
        n2 = _create_node(store, title="任务B", status="inbox", is_root=True)
        result = render_dashboard(store)
        assert n1.id in result
        assert n2.id in result

    def test_inbox_with_parent_not_in_zone0(self, tmp_path):
        """inbox node with parent should appear in tree (Zone 1), not Zone 0."""
        store = _make_store(tmp_path)
        parent = _create_node(
            store, title="Parent", status="active", node_type="goal", is_root=True
        )
        child = _create_node(
            store, title="Child inbox", status="inbox", parent_id=parent.id
        )
        result = render_dashboard(store)
        # The child inbox node should be indented (in tree), not at top level
        child_line = [l for l in result.split("\n") if child.id in l]
        assert len(child_line) == 1
        # It should have a tree connector (it's a child in Zone 1)
        assert "├─" in child_line[0] or "└─" in child_line[0]


# ── Zone 1 (tree) ──────────────────────────────────────────────


class TestZone1Tree:
    def test_single_root_active(self, tmp_path):
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="Project Alpha", status="active",
            node_type="goal", is_root=True, summary="test"
        )
        result = render_dashboard(store)
        assert "🔵" in result
        assert root.id in result
        assert "Project Alpha" in result

    def test_tree_indentation(self, tmp_path):
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="Root Goal", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        child = _create_node(
            store, title="Child Task", status="active",
            node_type="task", parent_id=root.id, summary="s"
        )
        result = render_dashboard(store)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        # Find lines with our nodes
        root_line = [l for l in lines if root.id in l][0]
        child_line = [l for l in lines if child.id in l][0]
        # Child should have tree connector (├─ or └─)
        assert "├─" in child_line or "└─" in child_line

    def test_deep_nesting(self, tmp_path):
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="L0", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        l1 = _create_node(
            store, title="L1", status="active",
            node_type="project", parent_id=root.id, summary="s"
        )
        l2 = _create_node(
            store, title="L2", status="active",
            node_type="task", parent_id=l1.id, summary="s"
        )
        result = render_dashboard(store)
        assert l2.id in result

    def test_multiple_children_connectors(self, tmp_path):
        """Last child uses └─, others use ├─."""
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="Root", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        c1 = _create_node(
            store, title="C1", status="active",
            parent_id=root.id, summary="s"
        )
        c2 = _create_node(
            store, title="C2", status="done",
            parent_id=root.id, summary="s"
        )
        result = render_dashboard(store)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        child_lines = [l for l in lines if c1.id in l or c2.id in l]
        assert len(child_lines) == 2
        # Exactly one └─ (the last child)
        assert sum("└─" in l for l in child_lines) == 1


# ── Status icons ────────────────────────────────────────────────


class TestStatusIcons:
    def test_all_status_icons(self, tmp_path):
        store = _make_store(tmp_path)
        statuses = {
            "inbox": "📥",
            "active": "🔵",
            "waiting": "⏳",
            "done": "✅",
            "dropped": "❌",
        }
        nodes = {}
        for status, icon in statuses.items():
            n = _create_node(
                store, title=f"Node {status}", status=status,
                is_root=True, summary="s"
            )
            nodes[status] = (n, icon)

        result = render_dashboard(store)
        for status, (n, icon) in nodes.items():
            line = [l for l in result.split("\n") if n.id in l]
            assert len(line) >= 1, f"Node {status} not found in dashboard"
            assert icon in line[0], f"Icon {icon} not found for {status}"


# ── Risk marks ──────────────────────────────────────────────────


class TestRiskMarks:
    def test_at_risk_displayed(self, tmp_path):
        store = _make_store(tmp_path)
        deadline = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        n = _create_node(
            store, title="Urgent", status="active",
            is_root=True, summary="s", deadline=deadline
        )
        result = render_dashboard(store)
        # at-risk with deadline shows 🚨deadline:M/D format
        assert "🚨" in result

    def test_stale_displayed(self, tmp_path):
        store = _make_store(tmp_path)
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        n = _create_node(
            store, title="Old task", status="active",
            is_root=True, summary="s", status_changed_at=old
        )
        result = render_dashboard(store)
        assert "stale" in result

    def test_blocked_displayed(self, tmp_path):
        store = _make_store(tmp_path)
        n1 = _create_node(
            store, title="Blocked", status="active",
            is_root=True, summary="s"
        )
        n2 = _create_node(
            store, title="Dep", status="waiting",
            is_root=True, summary="s"
        )
        edge = Edge(source_id=n1.id, target_id=n2.id, edge_type="depends_on")
        store.add_edge(edge)
        result = render_dashboard(store)
        assert "blocked" in result

    def test_deadline_shown_for_at_risk(self, tmp_path):
        store = _make_store(tmp_path)
        deadline = "2026-03-18T18:00:00+08:00"
        n = _create_node(
            store, title="Due soon", status="active",
            is_root=True, summary="s", deadline=deadline
        )
        result = render_dashboard(store)
        # Should show deadline info
        assert "3/18" in result or "deadline" in result.lower()

    def test_no_risk_no_marks(self, tmp_path):
        store = _make_store(tmp_path)
        n = _create_node(
            store, title="Healthy", status="active",
            is_root=True, summary="s"
        )
        result = render_dashboard(store)
        line = [l for l in result.split("\n") if n.id in l][0]
        assert "blocked" not in line
        assert "at-risk" not in line
        assert "stale" not in line


# ── Sorting ─────────────────────────────────────────────────────


class TestSorting:
    def test_high_risk_root_first(self, tmp_path):
        """Root with blocked child should appear before clean root."""
        store = _make_store(tmp_path)
        # Clean root
        clean = _create_node(
            store, title="Clean Project", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        # Risky root (has at-risk child)
        risky = _create_node(
            store, title="Risky Project", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        deadline = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        _create_node(
            store, title="Urgent child", status="active",
            parent_id=risky.id, summary="s", deadline=deadline
        )
        result = render_dashboard(store)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        # Find positions
        risky_pos = next(i for i, l in enumerate(lines) if risky.id in l)
        clean_pos = next(i for i, l in enumerate(lines) if clean.id in l)
        assert risky_pos < clean_pos, "Risky root should appear before clean root"

    def test_siblings_sorted_by_risk(self, tmp_path):
        """Among siblings, higher risk should come first."""
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="Root", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        healthy = _create_node(
            store, title="Healthy", status="active",
            parent_id=root.id, summary="s"
        )
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        stale = _create_node(
            store, title="Stale", status="active",
            parent_id=root.id, summary="s", status_changed_at=old
        )
        result = render_dashboard(store)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        stale_pos = next(i for i, l in enumerate(lines) if stale.id in l)
        healthy_pos = next(i for i, l in enumerate(lines) if healthy.id in l)
        assert stale_pos < healthy_pos


# ── Archived nodes ──────────────────────────────────────────────


class TestArchived:
    def test_archived_not_displayed(self, tmp_path):
        store = _make_store(tmp_path)
        n = _create_node(
            store, title="Archived", status="done",
            is_root=True, archived_at=_utcnow_iso()
        )
        result = render_dashboard(store)
        assert n.id not in result

    def test_archived_child_not_displayed(self, tmp_path):
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="Root", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        archived = _create_node(
            store, title="Archived child", status="done",
            parent_id=root.id, archived_at=_utcnow_iso()
        )
        result = render_dashboard(store)
        assert archived.id not in result


# ── Truncation ──────────────────────────────────────────────────


class TestTruncation:
    def test_truncation_with_tiny_budget(self, tmp_path):
        """With a very small token budget, some nodes get folded."""
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="Big Project", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        # Create many healthy children
        for i in range(20):
            _create_node(
                store, title=f"Task {i}", status="active",
                parent_id=root.id, summary="s"
            )
        # Very small budget forces truncation
        result = render_dashboard(store, max_tokens=200)
        assert "折叠" in result or "..." in result

    def test_risky_nodes_survive_truncation(self, tmp_path):
        """Risky nodes should survive truncation even with small budget."""
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="Big Project", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        # Many healthy children
        for i in range(15):
            _create_node(
                store, title=f"Healthy {i}", status="active",
                parent_id=root.id, summary="s"
            )
        # One risky child
        deadline = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        risky = _create_node(
            store, title="RISKY TASK", status="active",
            parent_id=root.id, summary="s", deadline=deadline
        )
        result = render_dashboard(store, max_tokens=200)
        # Risky node must survive
        assert risky.id in result

    def test_no_truncation_within_budget(self, tmp_path):
        store = _make_store(tmp_path)
        root = _create_node(
            store, title="Small", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        _create_node(
            store, title="Child", status="active",
            parent_id=root.id, summary="s"
        )
        result = render_dashboard(store, max_tokens=5000)
        assert "折叠" not in result


# ── Mixed zones ─────────────────────────────────────────────────


class TestMixedZones:
    def test_zone0_before_zone1(self, tmp_path):
        """Zone 0 (inbox floating) should appear before Zone 1 (tree)."""
        store = _make_store(tmp_path)
        inbox_node = _create_node(
            store, title="Floating inbox", status="inbox", is_root=True
        )
        tree_root = _create_node(
            store, title="Tree root", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        result = render_dashboard(store)
        inbox_pos = result.index(inbox_node.id)
        tree_pos = result.index(tree_root.id)
        assert inbox_pos < tree_pos

    def test_only_inbox_roots_in_zone0(self, tmp_path):
        """Active root nodes should be in Zone 1, not Zone 0."""
        store = _make_store(tmp_path)
        active_root = _create_node(
            store, title="Active root", status="active",
            node_type="goal", is_root=True, summary="s"
        )
        result = render_dashboard(store)
        # Should show tree icon, not just inbox icon
        assert "📁" in result or "🔵" in result
