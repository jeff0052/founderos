"""Tests for spine/models.py — Pydantic input validation + dataclass completeness."""

import dataclasses

import pytest
from pydantic import ValidationError

from spine.models import (
    CreateNodeInput,
    Edge,
    Node,
    ToolResult,
    UpdateFieldInput,
    UpdateStatusInput,
)


# ── CreateNodeInput ───────────────────────────────────────────


class TestCreateNodeInput:
    """Pydantic validation for create_node inputs."""

    def test_minimal_valid_input(self):
        inp = CreateNodeInput(title="My Task")
        assert inp.title == "My Task"
        assert inp.node_type == "unknown"
        assert inp.is_root is False
        assert inp.parent_id is None

    def test_full_valid_input(self):
        inp = CreateNodeInput(
            title="Ship v1",
            node_type="milestone",
            parent_id="proj-abc",
            is_root=False,
            summary="First release",
            why="Customer deadline",
            next_step="Write tests",
            owner="jeff",
            deadline="2026-06-01T00:00:00+08:00",
        )
        assert inp.node_type == "milestone"
        assert inp.deadline == "2026-06-01T00:00:00+08:00"

    def test_all_valid_node_types(self):
        for nt in ("goal", "project", "milestone", "task", "unknown"):
            inp = CreateNodeInput(title="x", node_type=nt)
            assert inp.node_type == nt

    def test_is_root_coercion_from_string(self):
        """Pydantic should coerce string 'true' to bool True."""
        inp = CreateNodeInput(title="Root", is_root="true")
        assert inp.is_root is True

    def test_invalid_node_type_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateNodeInput(title="x", node_type="epic")
        assert "node_type" in str(exc_info.value)

    def test_invalid_deadline_format_raises_with_example(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateNodeInput(title="x", deadline="next-friday")
        error_text = str(exc_info.value)
        assert "ISO 8601" in error_text or "示例" in error_text

    def test_none_deadline_accepted(self):
        inp = CreateNodeInput(title="x", deadline=None)
        assert inp.deadline is None

    def test_valid_deadline_formats(self):
        for d in ("2026-03-20", "2026-03-20T18:00:00", "2026-03-20T18:00:00+08:00"):
            inp = CreateNodeInput(title="x", deadline=d)
            assert inp.deadline == d


# ── UpdateStatusInput ─────────────────────────────────────────


class TestUpdateStatusInput:
    """Pydantic validation for update_status inputs."""

    def test_valid_statuses(self):
        for s in ("inbox", "active", "waiting", "done", "dropped"):
            inp = UpdateStatusInput(node_id="t-1", new_status=s)
            assert inp.new_status == s

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            UpdateStatusInput(node_id="t-1", new_status="deleted")
        assert "status" in str(exc_info.value)

    def test_optional_reason(self):
        inp = UpdateStatusInput(node_id="t-1", new_status="active", reason="reopen")
        assert inp.reason == "reopen"

    def test_optional_is_root(self):
        inp = UpdateStatusInput(node_id="t-1", new_status="active", is_root=True)
        assert inp.is_root is True


# ── UpdateFieldInput ──────────────────────────────────────────


class TestUpdateFieldInput:
    """Pydantic validation for update_field inputs."""

    def test_all_valid_fields(self):
        for f in ("title", "summary", "why", "next_step", "owner", "deadline", "node_type"):
            inp = UpdateFieldInput(node_id="t-1", field=f, value="x")
            assert inp.field == f

    def test_invalid_field_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            UpdateFieldInput(node_id="t-1", field="status", value="done")
        assert "field" in str(exc_info.value).lower() or "可修改字段" in str(exc_info.value)

    def test_value_none_accepted(self):
        inp = UpdateFieldInput(node_id="t-1", field="summary", value=None)
        assert inp.value is None


# ── Dataclass completeness ────────────────────────────────────


class TestNodeDataclass:
    """Node dataclass has all 16 fields from the schema."""

    EXPECTED_FIELDS = [
        "id", "title", "status", "node_type",
        "is_root", "parent_id", "summary", "why",
        "next_step", "owner", "deadline", "is_persistent",
        "created_at", "updated_at", "status_changed_at", "archived_at",
    ]

    def test_has_16_fields(self):
        fields = [f.name for f in dataclasses.fields(Node)]
        assert len(fields) == 16

    def test_field_names_match(self):
        fields = [f.name for f in dataclasses.fields(Node)]
        assert fields == self.EXPECTED_FIELDS


class TestEdgeDataclass:
    """Edge dataclass has all required fields."""

    def test_fields(self):
        fields = [f.name for f in dataclasses.fields(Edge)]
        assert fields == ["source_id", "target_id", "edge_type", "created_at"]


class TestToolResultDataclass:
    """ToolResult has command_id, event_id, and warnings."""

    def test_fields_complete(self):
        fields = {f.name for f in dataclasses.fields(ToolResult)}
        assert "command_id" in fields
        assert "event_id" in fields
        assert "warnings" in fields
        assert "success" in fields
        assert "data" in fields
        assert "error" in fields
        assert "suggestion" in fields
        assert "affected_nodes" in fields

    def test_default_values(self):
        tr = ToolResult(success=True, command_id="cmd-001")
        assert tr.event_id is None
        assert tr.warnings == []
        assert tr.affected_nodes == []
        assert tr.data is None
        assert tr.error is None
