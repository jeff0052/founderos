"""Tool Call handlers for the 14 FPMS tools."""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from .models import Node, Edge, ToolResult, CreateNodeInput, UpdateStatusInput, UpdateFieldInput
from .validator import ValidationError

if TYPE_CHECKING:
    from .store import Store


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node_to_dict(node: Node) -> dict:
    return asdict(node)


class ToolHandler:
    def __init__(self, store: "Store", validator_module=None, narrative_module=None,
                 risk_module=None, rollup_module=None, dashboard_module=None,
                 narratives_dir: Optional[str] = None) -> None:
        self.store = store
        self.validator = validator_module
        self.narrative = narrative_module
        self.risk_module = risk_module
        self.rollup_module = rollup_module
        self.dashboard_module = dashboard_module
        if narratives_dir:
            self.narratives_dir = narratives_dir
        else:
            # Derive from store.db_path
            self.narratives_dir = os.path.join(os.path.dirname(store.db_path), "narratives")

    def handle(self, tool_name: str, params: dict) -> ToolResult:
        handler = getattr(self, "handle_{}".format(tool_name), None)
        if not handler:
            return ToolResult(success=False, command_id="",
                              error="Unknown tool: {}".format(tool_name))
        try:
            return handler(params)
        except ValidationError as e:
            return ToolResult(success=False, command_id="",
                              error=e.message, suggestion=e.suggestion)
        except Exception as e:
            return ToolResult(success=False, command_id="",
                              error=str(e))

    def _write_narrative(self, node_id: str, event_type: str, content: str) -> None:
        if self.narrative:
            self.narrative.append_narrative(
                self.narratives_dir, node_id, _utcnow_iso(), event_type, content
            )

    # --- Write Tools ---

    def handle_create_node(self, params: dict) -> ToolResult:
        try:
            inp = CreateNodeInput(**params)
        except Exception as e:
            return ToolResult(success=False, command_id="", error=str(e),
                              suggestion="Check required fields: title is required.")

        # XOR check
        if self.validator:
            self.validator.validate_xor_constraint(inp.is_root, inp.parent_id)

        # If has parent_id, not root; if no parent_id and not is_root, default to unknown type standalone
        node = Node(
            id="",
            title=inp.title,
            status="inbox",
            node_type=inp.node_type,
            is_root=inp.is_root if not inp.parent_id else False,
            parent_id=inp.parent_id,
            summary=inp.summary,
            why=inp.why,
            next_step=inp.next_step,
            owner=inp.owner,
            deadline=inp.deadline,
        )

        with self.store.transaction():
            created = self.store.create_node(node)
            # If parent_id, also add parent edge
            if inp.parent_id:
                edge = Edge(source_id=created.id, target_id=inp.parent_id, edge_type="parent")
                self.store.add_edge(edge)

        self._write_narrative(created.id, "create_node",
                              "Created node: {}".format(created.title))

        return ToolResult(
            success=True, command_id="",
            data=_node_to_dict(created),
            affected_nodes=[created.id],
        )

    def handle_update_status(self, params: dict) -> ToolResult:
        try:
            inp = UpdateStatusInput(**params)
        except Exception as e:
            return ToolResult(success=False, command_id="", error=str(e))

        node = self.store.get_node(inp.node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(inp.node_id))

        # Reason required for done->active, dropped->inbox
        if (node.status == "done" and inp.new_status == "active") or \
           (node.status == "dropped" and inp.new_status == "inbox"):
            if not inp.reason:
                return ToolResult(
                    success=False, command_id="",
                    error="Reason required for {} -> {} transition.".format(node.status, inp.new_status),
                    suggestion="Pass reason parameter explaining why this node is being reopened.",
                )

        # Validate transition
        children = self.store.get_children(node.id, include_archived=True)
        if self.validator:
            self.validator.validate_status_transition(node.status, inp.new_status, node, children)

        fields = {
            "status": inp.new_status,
            "status_changed_at": _utcnow_iso(),
        }
        if inp.is_root is not None:
            fields["is_root"] = inp.is_root
            if inp.is_root:
                fields["parent_id"] = None

        with self.store.transaction():
            updated = self.store.update_node(inp.node_id, fields)

        self._write_narrative(inp.node_id, "update_status",
                              "Status: {} -> {}".format(node.status, inp.new_status))

        return ToolResult(
            success=True, command_id="",
            data=_node_to_dict(updated),
            affected_nodes=[inp.node_id],
        )

    def handle_update_field(self, params: dict) -> ToolResult:
        try:
            inp = UpdateFieldInput(**params)
        except Exception as e:
            return ToolResult(success=False, command_id="", error=str(e))

        node = self.store.get_node(inp.node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(inp.node_id))

        with self.store.transaction():
            updated = self.store.update_node(inp.node_id, {inp.field: inp.value})

        self._write_narrative(inp.node_id, "update_field",
                              "Updated {}: {}".format(inp.field, inp.value))

        return ToolResult(
            success=True, command_id="",
            data=_node_to_dict(updated),
            affected_nodes=[inp.node_id],
        )

    def handle_attach_node(self, params: dict) -> ToolResult:
        node_id = params.get("node_id", "")
        parent_id = params.get("parent_id", "")

        node = self.store.get_node(node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(node_id))

        # Validate
        if self.validator:
            self.validator.validate_attach(self.store, node_id, parent_id)

        with self.store.transaction():
            # If already has parent, remove old edge
            if node.parent_id:
                self.store.remove_edge(node_id, node.parent_id, "parent")

            edge = Edge(source_id=node_id, target_id=parent_id, edge_type="parent")
            self.store.add_edge(edge)
            self.store.update_node(node_id, {"parent_id": parent_id, "is_root": False})

        self._write_narrative(node_id, "attach_node",
                              "Attached to parent: {}".format(parent_id))

        return ToolResult(
            success=True, command_id="",
            data={"node_id": node_id, "parent_id": parent_id},
            affected_nodes=[node_id, parent_id],
        )

    def handle_detach_node(self, params: dict) -> ToolResult:
        node_id = params.get("node_id", "")

        node = self.store.get_node(node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(node_id))

        if not node.parent_id:
            return ToolResult(success=True, command_id="",
                              data={"node_id": node_id, "detached": False})

        old_parent = node.parent_id
        with self.store.transaction():
            self.store.remove_edge(node_id, old_parent, "parent")
            self.store.update_node(node_id, {"parent_id": None, "is_root": True})

        self._write_narrative(node_id, "detach_node",
                              "Detached from parent: {}".format(old_parent))

        return ToolResult(
            success=True, command_id="",
            data={"node_id": node_id, "detached": True},
            affected_nodes=[node_id],
        )

    def handle_add_dependency(self, params: dict) -> ToolResult:
        source_id = params.get("source_id", "")
        target_id = params.get("target_id", "")

        if self.validator:
            self.validator.validate_dependency(self.store, source_id, target_id)

        with self.store.transaction():
            edge = Edge(source_id=source_id, target_id=target_id, edge_type="depends_on")
            self.store.add_edge(edge)

        self._write_narrative(source_id, "add_dependency",
                              "Added dependency on: {}".format(target_id))

        return ToolResult(
            success=True, command_id="",
            data={"source_id": source_id, "target_id": target_id},
            affected_nodes=[source_id, target_id],
        )

    def handle_remove_dependency(self, params: dict) -> ToolResult:
        source_id = params.get("source_id", "")
        target_id = params.get("target_id", "")

        with self.store.transaction():
            removed = self.store.remove_edge(source_id, target_id, "depends_on")

        return ToolResult(
            success=True, command_id="",
            data={"source_id": source_id, "target_id": target_id, "removed": removed},
            affected_nodes=[source_id, target_id] if removed else [],
        )

    def handle_append_log(self, params: dict) -> ToolResult:
        node_id = params.get("node_id", "")
        content = params.get("content", "")

        node = self.store.get_node(node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(node_id))

        self._write_narrative(node_id, "append_log", content)

        return ToolResult(
            success=True, command_id="",
            data={"node_id": node_id},
            affected_nodes=[node_id],
        )

    def handle_unarchive(self, params: dict) -> ToolResult:
        node_id = params.get("node_id", "")
        new_status = params.get("new_status", None)

        node = self.store.get_node(node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(node_id))

        if node.archived_at is None:
            return ToolResult(success=False, command_id="",
                              error="Node {} is not archived.".format(node_id))

        # Validate new_status if provided
        if new_status is not None:
            allowed = {"inbox", "active", "waiting", "done", "dropped"}
            if new_status not in allowed:
                return ToolResult(
                    success=False, command_id="",
                    error="new_status must be one of {}, got '{}'.".format(allowed, new_status),
                    suggestion="Valid statuses: inbox, active, waiting, done, dropped",
                )
            # Validate status transition from current status
            if self.validator:
                try:
                    children = self.store.get_children(node.id, include_archived=True)
                    self.validator.validate_status_transition(
                        node.status, new_status, node, children
                    )
                except ValidationError as e:
                    return ToolResult(
                        success=False, command_id="",
                        error=e.message, suggestion=e.suggestion,
                    )

        now = _utcnow_iso()
        fields = {
            "archived_at": None,
            "status_changed_at": now,
        }
        if new_status is not None:
            fields["status"] = new_status

        with self.store.transaction():
            updated = self.store.update_node(node_id, fields)

        narrative_msg = "Node unarchived"
        if new_status is not None:
            narrative_msg = "Node unarchived, status set to {}".format(new_status)
        self._write_narrative(node_id, "unarchive", narrative_msg)

        return ToolResult(
            success=True, command_id="",
            data=_node_to_dict(updated),
            affected_nodes=[node_id],
        )

    def handle_set_persistent(self, params: dict) -> ToolResult:
        node_id = params.get("node_id", "")
        is_persistent = params.get("is_persistent", True)

        node = self.store.get_node(node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(node_id))

        with self.store.transaction():
            updated = self.store.update_node(node_id, {"is_persistent": is_persistent})

        return ToolResult(
            success=True, command_id="",
            data=_node_to_dict(updated),
            affected_nodes=[node_id],
        )

    # --- Runtime Tools ---

    def handle_shift_focus(self, params: dict) -> ToolResult:
        node_id = params.get("node_id", "")
        self.store.set_session("focus", {"node_id": node_id})
        return ToolResult(success=True, command_id="",
                          data={"focus_node_id": node_id})

    def handle_expand_context(self, params: dict) -> ToolResult:
        node_id = params.get("node_id", "")
        node = self.store.get_node(node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(node_id))
        return ToolResult(success=True, command_id="",
                          data=_node_to_dict(node))

    # --- Read Tools ---

    def handle_get_node(self, params: dict) -> ToolResult:
        node_id = params.get("node_id", "")
        node = self.store.get_node(node_id)
        if node is None:
            return ToolResult(success=False, command_id="",
                              error="Node not found: {}".format(node_id))
        return ToolResult(success=True, command_id="",
                          data=_node_to_dict(node))

    def handle_search_nodes(self, params: dict) -> ToolResult:
        filters = {}
        for key in ("status", "parent_id", "node_type", "is_root", "owner"):
            if key in params:
                filters[key] = params[key]

        limit = params.get("limit", 50)
        offset = params.get("offset", 0)

        nodes = self.store.list_nodes(filters=filters, limit=limit, offset=offset)
        return ToolResult(
            success=True, command_id="",
            data={"nodes": [_node_to_dict(n) for n in nodes]},
        )
