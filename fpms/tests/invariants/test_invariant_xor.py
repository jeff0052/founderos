"""Invariant: is_root and parent_id are mutually exclusive (XOR).

Source: PRD Invariant #1b, Appendix 7 Topo Safety
"""

import pytest
from spine.models import Node, Edge
from spine.validator import validate_xor_constraint, ValidationError


class TestXORConstraint:
    """is_root=True and parent_id≠None must never coexist."""

    def test_root_true_parent_none_valid(self, store):
        """is_root=True, parent_id=None → valid."""
        validate_xor_constraint(is_root=True, parent_id=None)

    def test_root_false_parent_set_valid(self, store):
        """is_root=False, parent_id='some-id' → valid."""
        validate_xor_constraint(is_root=False, parent_id="goal-1234")

    def test_root_false_parent_none_valid(self, store):
        """is_root=False, parent_id=None → valid (inbox node, not yet attached)."""
        validate_xor_constraint(is_root=False, parent_id=None)

    def test_root_true_parent_set_rejected(self, store):
        """is_root=True, parent_id≠None → must reject."""
        with pytest.raises(ValidationError) as exc_info:
            validate_xor_constraint(is_root=True, parent_id="goal-1234")
        assert exc_info.value.code == "XOR_VIOLATION" or "互斥" in exc_info.value.message or "XOR" in exc_info.value.message


class TestXORAutoCorrection:
    """API auto-corrects XOR violations instead of rejecting."""

    def test_attach_clears_root(self, store):
        """attach_node on is_root=True node → is_root becomes False."""
        parent = store.create_node(Node(id="", title="Parent", status="inbox", node_type="goal", is_root=True))
        child = store.create_node(Node(id="", title="Child", status="inbox", node_type="task", is_root=True))

        # After attach, child.is_root should be False
        store.add_edge(Edge(source_id=child.id, target_id=parent.id, edge_type="parent"))
        # Re-fetch to verify
        updated = store.get_node(child.id)
        assert updated is not None
        assert updated.is_root is False
        assert updated.parent_id == parent.id

    def test_set_root_clears_parent(self, store):
        """update_status(is_root=true) on attached node → parent_id becomes None."""
        parent = store.create_node(Node(id="", title="Parent", status="inbox", node_type="goal", is_root=True))
        child = store.create_node(Node(id="", title="Child", status="inbox", node_type="task"))
        store.add_edge(Edge(source_id=child.id, target_id=parent.id, edge_type="parent"))

        # Set child as root → should clear parent
        store.update_node(child.id, {"is_root": True, "parent_id": None})
        updated = store.get_node(child.id)
        assert updated is not None
        assert updated.is_root is True
        assert updated.parent_id is None
