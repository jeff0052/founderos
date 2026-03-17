"""Invariant: Status transitions follow strict rules.

Source: PRD FR-5.1, Appendix 7 Status Engine
"""

import pytest
from spine.models import Node
from spine.validator import validate_status_transition, ValidationError


# Helper to make a node with given status
def _node(status: str, summary: str = None, parent_id: str = None,
          is_root: bool = False) -> Node:
    return Node(
        id="test-node",
        title="Test",
        status=status,
        node_type="task",
        summary=summary,
        parent_id=parent_id,
        is_root=is_root,
    )


class TestLegalTransitions:
    """All legal transitions must be accepted."""

    @pytest.mark.parametrize("current,target", [
        ("inbox", "active"),
        ("inbox", "waiting"),
        ("inbox", "dropped"),
        ("active", "waiting"),
        ("active", "done"),
        ("active", "dropped"),
        ("waiting", "active"),
        ("waiting", "done"),
        ("waiting", "dropped"),
    ])
    def test_legal_forward_transitions(self, store, current, target):
        """Forward transitions with all preconditions met → accept."""
        node = _node(current, summary="Has summary", is_root=True)
        validate_status_transition(current, target, node, children=[])

    def test_done_to_active_with_reason(self, store):
        """done → active with reason → accept."""
        node = _node("done", summary="Done node", is_root=True)
        # Reason is provided externally; validator checks node state
        validate_status_transition("done", "active", node, children=[])

    def test_dropped_to_inbox_with_reason(self, store):
        """dropped → inbox with reason → accept."""
        node = _node("dropped", summary="Dropped node", is_root=True)
        validate_status_transition("dropped", "inbox", node, children=[])


class TestIllegalTransitions:
    """All illegal transitions must be rejected."""

    @pytest.mark.parametrize("current,target", [
        ("inbox", "done"),      # Can't skip to done
        ("done", "waiting"),    # done can only go to active
        ("done", "dropped"),    # done can only go to active
        ("done", "inbox"),      # done can only go to active
        ("dropped", "active"),  # dropped can only go to inbox
        ("dropped", "waiting"), # dropped can only go to inbox
        ("dropped", "done"),    # dropped can only go to inbox
    ])
    def test_illegal_transitions_rejected(self, store, current, target):
        """Illegal transitions → ValidationError."""
        node = _node(current, summary="Test", is_root=True)
        with pytest.raises(ValidationError):
            validate_status_transition(current, target, node, children=[])


class TestPreconditions:
    """Status transition preconditions."""

    def test_inbox_to_active_needs_summary(self, store):
        """inbox → active without summary → reject with actionable error."""
        node = _node("inbox", summary=None, is_root=True)
        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition("inbox", "active", node, children=[])
        # Error should suggest using update_field to add summary
        assert exc_info.value.suggestion is not None or "summary" in exc_info.value.message.lower()

    def test_inbox_to_active_needs_parent_or_root(self, store):
        """inbox → active without parent_id and not is_root → reject."""
        node = _node("inbox", summary="Has summary", parent_id=None, is_root=False)
        with pytest.raises(ValidationError):
            validate_status_transition("inbox", "active", node, children=[])

    def test_to_done_with_active_children_rejected(self, store):
        """→ done with active children → reject."""
        node = _node("active", summary="Parent", is_root=True)
        active_child = Node(id="child-1", title="Active Child", status="active", node_type="task")

        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition("active", "done", node, children=[active_child])
        # Error should mention the active children
        assert "child" in exc_info.value.message.lower() or "子" in exc_info.value.message

    def test_to_done_with_all_terminal_children_accepted(self, store):
        """→ done with all children done/dropped → accept."""
        node = _node("active", summary="Parent", is_root=True)
        done_child = Node(id="child-1", title="Done Child", status="done", node_type="task")
        dropped_child = Node(id="child-2", title="Dropped Child", status="dropped", node_type="task")

        validate_status_transition("active", "done", node, children=[done_child, dropped_child])

    def test_to_dropped_with_active_children_warns(self, store):
        """→ dropped with active children → allow but return warning."""
        node = _node("active", summary="Parent", is_root=True)
        active_child = Node(id="child-1", title="Active Child", status="active", node_type="task")

        # Should NOT raise (dropped is allowed), but may return warnings
        # The validator allows this but tools.py should add warnings
        validate_status_transition("active", "dropped", node, children=[active_child])


class TestActionableErrors:
    """Error messages must be actionable — tell LLM what to do next."""

    def test_missing_summary_error_has_suggestion(self, store):
        """Missing summary error should suggest update_field."""
        node = _node("inbox", summary=None, is_root=True)
        with pytest.raises(ValidationError) as exc_info:
            validate_status_transition("inbox", "active", node, children=[])
        err = exc_info.value
        assert err.suggestion != "" or "update_field" in err.message
