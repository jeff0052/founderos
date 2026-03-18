#!/usr/bin/env python3
"""MCP Server for FPMS - Exposes all 14 FPMS tools via stdio transport.

Usage:
    python mcp_server.py

Does NOT: HTTP/SSE transport, authentication, MCP resources/prompts, modify existing files.
"""

from __future__ import annotations

import os
import sys
import uuid
from typing import Dict, Any, Optional

# Add current dir to path so spine/ package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from spine.schema import init_db
from spine.store import Store
from spine.command_executor import CommandExecutor

# ── Paths (same as spine.py) ──

FPMS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FPMS_DIR, "db", "fpms.db")
EVENTS_PATH = os.path.join(FPMS_DIR, "events.jsonl")
NARRATIVES_DIR = os.path.join(FPMS_DIR, "narratives")


def _ensure_dirs():
    os.makedirs(os.path.join(FPMS_DIR, "db"), exist_ok=True)
    os.makedirs(NARRATIVES_DIR, exist_ok=True)


def _get_store() -> Store:
    _ensure_dirs()
    init_db(DB_PATH)
    return Store(db_path=DB_PATH, events_path=EVENTS_PATH)


def _get_executor() -> tuple[Store, CommandExecutor]:
    store = _get_store()
    executor = CommandExecutor(store, narratives_dir=NARRATIVES_DIR)
    return store, executor


# Initialize FPMS
store, executor = _get_executor()

# Create FastMCP app
app = FastMCP("FPMS MCP Server")


# ── Tool Definitions ──

@app.tool()
def create_node(
    title: str,
    node_type: str = "unknown",
    parent_id: Optional[str] = None,
    is_root: bool = False,
    summary: Optional[str] = None,
    why: Optional[str] = None,
    next_step: Optional[str] = None,
    owner: Optional[str] = None,
    deadline: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new node in FPMS."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {
        "title": title,
        "node_type": node_type,
        "parent_id": parent_id,
        "is_root": is_root,
        "summary": summary,
        "why": why,
        "next_step": next_step,
        "owner": owner,
        "deadline": deadline
    }
    result = executor.execute(command_id, "create_node", tool_args)
    
    # Convert ToolResult to dict
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def update_status(
    node_id: str,
    new_status: str,
    reason: Optional[str] = None,
    is_root: Optional[bool] = None
) -> Dict[str, Any]:
    """Update the status of a node."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {
        "node_id": node_id,
        "new_status": new_status,
        "reason": reason,
        "is_root": is_root
    }
    result = executor.execute(command_id, "update_status", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def update_field(
    node_id: str,
    field: str,
    value: Optional[str] = None
) -> Dict[str, Any]:
    """Update a specific field of a node."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {
        "node_id": node_id,
        "field": field,
        "value": value
    }
    result = executor.execute(command_id, "update_field", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def attach_node(node_id: str, parent_id: str) -> Dict[str, Any]:
    """Attach a node to a parent."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"node_id": node_id, "parent_id": parent_id}
    result = executor.execute(command_id, "attach_node", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def detach_node(node_id: str) -> Dict[str, Any]:
    """Detach a node from its parent."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"node_id": node_id}
    result = executor.execute(command_id, "detach_node", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def add_dependency(source_id: str, target_id: str) -> Dict[str, Any]:
    """Add a dependency between two nodes."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"source_id": source_id, "target_id": target_id}
    result = executor.execute(command_id, "add_dependency", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def remove_dependency(source_id: str, target_id: str) -> Dict[str, Any]:
    """Remove a dependency between two nodes."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"source_id": source_id, "target_id": target_id}
    result = executor.execute(command_id, "remove_dependency", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def append_log(node_id: str, content: str) -> Dict[str, Any]:
    """Append a log entry to a node."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"node_id": node_id, "content": content}
    result = executor.execute(command_id, "append_log", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def unarchive(node_id: str) -> Dict[str, Any]:
    """Unarchive a node."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"node_id": node_id}
    result = executor.execute(command_id, "unarchive", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def set_persistent(node_id: str, is_persistent: bool) -> Dict[str, Any]:
    """Set the persistent flag for a node."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"node_id": node_id, "is_persistent": is_persistent}
    result = executor.execute(command_id, "set_persistent", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def shift_focus(node_id: str) -> Dict[str, Any]:
    """Shift focus to a specific node."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"node_id": node_id}
    result = executor.execute(command_id, "shift_focus", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def expand_context(node_id: str) -> Dict[str, Any]:
    """Expand context view."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"node_id": node_id}
    result = executor.execute(command_id, "expand_context", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def get_node(node_id: str) -> Dict[str, Any]:
    """Get details of a specific node."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {"node_id": node_id}
    result = executor.execute(command_id, "get_node", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


@app.tool()
def search_nodes(
    status: Optional[str] = None,
    parent_id: Optional[str] = None,
    node_type: Optional[str] = None,
    is_root: Optional[bool] = None,
    owner: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> Dict[str, Any]:
    """Search for nodes."""
    command_id = f"mcp-{uuid.uuid4().hex[:8]}"
    tool_args = {
        "status": status,
        "parent_id": parent_id,
        "node_type": node_type,
        "is_root": is_root,
        "owner": owner,
        "limit": limit,
        "offset": offset
    }
    result = executor.execute(command_id, "search_nodes", tool_args)
    
    return {
        "success": result.success,
        "command_id": result.command_id,
        "data": result.data,
        "error": result.error,
        "suggestion": result.suggestion,
        "affected_nodes": result.affected_nodes,
        "warnings": result.warnings
    }


# ── Main Entry Point ──

if __name__ == "__main__":
    app.run()