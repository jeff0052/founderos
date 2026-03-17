"""Invariant: Archive operations don't break the hot zone.

Active domain isolation: attach/dependency targets must be non-archived.

Source: PRD FR-6, Appendix 7 Topo Safety
"""

import pytest
from spine.models import Node, Edge
from spine.validator import validate_active_domain, validate_attach, validate_dependency, ValidationError


class TestActiveDomainIsolation:
    """Cannot create relationships targeting archived nodes."""

    def test_attach_to_archived_node_rejected(self, store):
        """attach_node to archived target → reject."""
        parent = store.create_node(Node(id="", title="Archived Parent", status="done", node_type="goal", is_root=True))
        # Archive the parent
        store.update_node(parent.id, {"archived_at": "2026-01-01T00:00:00Z"})

        child = store.create_node(Node(id="", title="Child", status="inbox", node_type="task"))

        with pytest.raises(ValidationError) as exc_info:
            validate_attach(store, child.id, parent.id)
        assert "归档" in exc_info.value.message or "archived" in exc_info.value.message.lower()

    def test_dependency_to_archived_node_rejected(self, store):
        """add_dependency to archived target → reject."""
        target = store.create_node(Node(id="", title="Archived Target", status="done", node_type="task", is_root=True))
        store.update_node(target.id, {"archived_at": "2026-01-01T00:00:00Z"})

        source = store.create_node(Node(id="", title="Source", status="inbox", node_type="task", is_root=True))

        with pytest.raises(ValidationError):
            validate_dependency(store, source.id, target.id)

    def test_attach_to_non_archived_accepted(self, store):
        """attach_node to active target → accept."""
        parent = store.create_node(Node(id="", title="Active Parent", status="inbox", node_type="goal", is_root=True))
        child = store.create_node(Node(id="", title="Child", status="inbox", node_type="task"))

        # Should not raise
        validate_attach(store, child.id, parent.id)

    def test_validate_active_domain_archived(self, store):
        """validate_active_domain on archived node → reject."""
        node = store.create_node(Node(id="", title="Archived", status="done", node_type="task", is_root=True))
        store.update_node(node.id, {"archived_at": "2026-01-01T00:00:00Z"})

        archived = store.get_node(node.id)
        with pytest.raises(ValidationError):
            validate_active_domain(archived)

    def test_validate_active_domain_non_archived(self, store):
        """validate_active_domain on non-archived node → accept."""
        node = store.create_node(Node(id="", title="Active", status="inbox", node_type="task", is_root=True))

        active = store.get_node(node.id)
        validate_active_domain(active)  # Should not raise


class TestParentDoneChildBlock:
    """Parent → done requires all children terminal."""

    def test_parent_done_active_child_rejected(self, store):
        """Parent → done while child is active → reject."""
        from spine.validator import validate_status_transition

        parent = Node(id="parent-1", title="Parent", status="active", node_type="goal",
                      is_root=True, summary="Test")
        active_child = Node(id="child-1", title="Child", status="active", node_type="task")

        with pytest.raises(ValidationError):
            validate_status_transition("active", "done", parent, children=[active_child])

    def test_parent_done_all_children_terminal_accepted(self, store):
        """Parent → done while all children are done/dropped → accept."""
        from spine.validator import validate_status_transition

        parent = Node(id="parent-1", title="Parent", status="active", node_type="goal",
                      is_root=True, summary="Test")
        done_child = Node(id="child-1", title="Child1", status="done", node_type="task")
        dropped_child = Node(id="child-2", title="Child2", status="dropped", node_type="task")

        validate_status_transition("active", "done", parent, children=[done_child, dropped_child])
