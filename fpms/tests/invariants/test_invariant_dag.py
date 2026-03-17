"""Invariant: DAG must never contain cycles.

Covers:
- Parent edge cycles (A→B→C→A)
- Depends_on edge cycles
- Cross-dimensional deadlock (child depends_on ancestor)
- Unified check merges both edge types

Source: PRD Invariant #2, Appendix 7 Topo Safety
"""

import pytest
from spine.models import Node, Edge
from spine.validator import validate_dag_safety, validate_attach, validate_dependency, ValidationError


class TestParentCycles:
    """Parent edge cycle detection."""

    def test_direct_parent_cycle_rejected(self, store):
        """A is parent of B, try to make B parent of A → reject."""
        # Create A and B
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="task", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="task"))

        # A is parent of B
        store.add_edge(Edge(source_id=b.id, target_id=a.id, edge_type="parent"))

        # Try to make B parent of A → should reject
        with pytest.raises(ValidationError) as exc_info:
            validate_attach(store, a.id, b.id)
        assert "cycle" in exc_info.value.message.lower() or "环" in exc_info.value.message

    def test_indirect_parent_cycle_rejected(self, store):
        """A→B→C (parent chain), try to make C parent of A → reject."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="goal", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="project"))
        c = store.create_node(Node(id="", title="C", status="inbox", node_type="task"))

        store.add_edge(Edge(source_id=b.id, target_id=a.id, edge_type="parent"))
        store.add_edge(Edge(source_id=c.id, target_id=b.id, edge_type="parent"))

        with pytest.raises(ValidationError):
            validate_attach(store, a.id, c.id)

    def test_valid_parent_accepted(self, store):
        """Non-cyclic parent relationship → accept."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="goal", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="task"))

        # This should not raise
        validate_attach(store, b.id, a.id)


class TestDependsCycles:
    """Depends_on edge cycle detection."""

    def test_direct_depends_cycle_rejected(self, store):
        """A depends_on B, try B depends_on A → reject."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="task", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="task", is_root=True))

        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))

        with pytest.raises(ValidationError):
            validate_dependency(store, b.id, a.id)

    def test_indirect_depends_cycle_rejected(self, store):
        """A→B→C (depends chain), try C depends_on A → reject."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="task", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="task", is_root=True))
        c = store.create_node(Node(id="", title="C", status="inbox", node_type="task", is_root=True))

        store.add_edge(Edge(source_id=a.id, target_id=b.id, edge_type="depends_on"))
        store.add_edge(Edge(source_id=b.id, target_id=c.id, edge_type="depends_on"))

        with pytest.raises(ValidationError):
            validate_dependency(store, c.id, a.id)

    def test_self_dependency_rejected(self, store):
        """A depends_on A → reject."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="task", is_root=True))

        with pytest.raises(ValidationError):
            validate_dependency(store, a.id, a.id)

    def test_valid_dependency_accepted(self, store):
        """Non-cyclic dependency → accept."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="task", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="task", is_root=True))

        # Should not raise
        validate_dependency(store, a.id, b.id)


class TestCrossDimensionalDeadlock:
    """Child depends_on ancestor → cross-dimensional deadlock."""

    def test_child_depends_on_parent_rejected(self, store):
        """B is child of A, B depends_on A → deadlock (parent waits child done via rollup, child waits parent done via depends)."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="goal", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="task"))
        store.add_edge(Edge(source_id=b.id, target_id=a.id, edge_type="parent"))

        with pytest.raises(ValidationError):
            validate_dependency(store, b.id, a.id)

    def test_grandchild_depends_on_grandparent_rejected(self, store):
        """C is grandchild of A (A→B→C), C depends_on A → reject."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="goal", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="project"))
        c = store.create_node(Node(id="", title="C", status="inbox", node_type="task"))

        store.add_edge(Edge(source_id=b.id, target_id=a.id, edge_type="parent"))
        store.add_edge(Edge(source_id=c.id, target_id=b.id, edge_type="parent"))

        with pytest.raises(ValidationError):
            validate_dependency(store, c.id, a.id)

    def test_parent_depends_on_unrelated_accepted(self, store):
        """A has child B, A depends_on C (unrelated) → accept."""
        a = store.create_node(Node(id="", title="A", status="inbox", node_type="goal", is_root=True))
        b = store.create_node(Node(id="", title="B", status="inbox", node_type="task"))
        c = store.create_node(Node(id="", title="C", status="inbox", node_type="task", is_root=True))

        store.add_edge(Edge(source_id=b.id, target_id=a.id, edge_type="parent"))

        # A depends on C (unrelated) should be fine
        validate_dependency(store, a.id, c.id)
