"""Serial command executor with idempotency."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

from .models import ToolResult, CreateNodeInput, UpdateStatusInput, UpdateFieldInput, AddMemoryInput
from .tools import ToolHandler

if TYPE_CHECKING:
    from .store import Store


# Tools that require Pydantic validation
_PYDANTIC_MAP = {
    "create_node": CreateNodeInput,
    "update_status": UpdateStatusInput,
    "update_field": UpdateFieldInput,
    "memory_add": AddMemoryInput,
}

# Read-only tools: no audit, no transaction wrapping
_READ_TOOLS = {"get_node", "search_nodes", "memory_search"}

# Memory tools: own audit via memory_events, skip FPMS audit_outbox
_MEMORY_TOOLS = {
    "memory_add", "memory_search", "memory_update",
    "memory_forget", "memory_promote", "memory_confirm",
}

# Write tools that produce audit events
_WRITE_TOOLS = {
    "create_node", "update_status", "update_field",
    "attach_node", "detach_node", "add_dependency", "remove_dependency",
    "append_log", "unarchive", "set_persistent",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CommandExecutor:
    def __init__(self, store: "Store", narratives_dir: str = "") -> None:
        self.store = store
        # Import modules for ToolHandler
        from spine import validator as validator_module
        from spine import narrative as narrative_module
        try:
            from spine import risk as risk_module
        except ImportError:
            risk_module = None
        try:
            from spine import rollup as rollup_module
        except ImportError:
            rollup_module = None
        try:
            from spine import dashboard as dashboard_module
        except ImportError:
            dashboard_module = None
        try:
            from spine import focus as focus_module
        except ImportError:
            focus_module = None

        self.handler = ToolHandler(
            store=store,
            validator_module=validator_module,
            narrative_module=narrative_module,
            risk_module=risk_module,
            rollup_module=rollup_module,
            dashboard_module=dashboard_module,
            focus_module=focus_module,
            narratives_dir=narratives_dir if narratives_dir else None,
        )

    def execute(self, command_id: str, tool_name: str, params: dict) -> ToolResult:
        # 1. Idempotency check
        existing = self.store._conn.execute(
            "SELECT result_json FROM recent_commands WHERE command_id = ?",
            (command_id,),
        ).fetchone()
        if existing:
            data = json.loads(existing["result_json"])
            return ToolResult(**data)

        # 2. Pydantic validation for write tools
        pydantic_cls = _PYDANTIC_MAP.get(tool_name)
        if pydantic_cls:
            try:
                pydantic_cls(**params)
            except Exception as e:
                result = ToolResult(
                    success=False, command_id=command_id,
                    error=str(e),
                    suggestion="Fix the input parameters and retry.",
                )
                self._record_command(command_id, tool_name, result)
                return result

        # 3. Route to handler
        result = self.handler.handle(tool_name, params)
        result.command_id = command_id

        # 4. Write audit event for write tools
        if tool_name in _WRITE_TOOLS and result.success:
            self.store.write_event({
                "event_type": tool_name,
                "tool_name": tool_name,
                "command_id": command_id,
                "timestamp": _utcnow_iso(),
                "params": params,
                "success": result.success,
            })
            if not self.store._in_transaction:
                self.store._conn.commit()

        # 5. Record to recent_commands
        self._record_command(command_id, tool_name, result)

        return result

    def _record_command(self, command_id: str, tool_name: str, result: ToolResult) -> None:
        now = _utcnow_iso()
        expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        result_dict = {
            "success": result.success,
            "command_id": result.command_id,
            "event_id": result.event_id,
            "data": result.data,
            "error": result.error,
            "suggestion": result.suggestion,
            "affected_nodes": result.affected_nodes,
            "warnings": result.warnings,
        }
        self.store._conn.execute(
            "INSERT OR REPLACE INTO recent_commands (command_id, tool_name, result_json, created_at, expires_at) VALUES (?,?,?,?,?)",
            (command_id, tool_name, json.dumps(result_dict), now, expires),
        )
        self.store._conn.commit()
