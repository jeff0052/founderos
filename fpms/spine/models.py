"""Data models for FPMS: internal dataclasses + Pydantic input validation."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, field_validator


# --- Pydantic Models (Tool Call input validation) ---

class CreateNodeInput(BaseModel):
    """create_node Tool Call 的输入。Pydantic 自动做类型强转和校验。"""
    title: str
    node_type: str = "unknown"
    parent_id: Optional[str] = None
    is_root: bool = False
    summary: Optional[str] = None
    why: Optional[str] = None
    next_step: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None

    @field_validator("node_type")
    @classmethod
    def check_node_type(cls, v: str) -> str:
        allowed = {"goal", "project", "milestone", "task", "unknown"}
        if v not in allowed:
            raise ValueError(f"node_type 必须是 {allowed} 之一，收到 '{v}'")
        return v

    @field_validator("deadline")
    @classmethod
    def check_deadline_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            from datetime import datetime as dt
            try:
                dt.fromisoformat(v)
            except ValueError:
                raise ValueError(
                    f"deadline 必须是 ISO 8601 格式，收到 '{v}'。"
                    f"示例: '2026-03-20T18:00:00+08:00'"
                )
        return v


class UpdateStatusInput(BaseModel):
    """update_status Tool Call 的输入。"""
    node_id: str
    new_status: str
    reason: Optional[str] = None
    is_root: Optional[bool] = None

    @field_validator("new_status")
    @classmethod
    def check_status(cls, v: str) -> str:
        allowed = {"inbox", "active", "waiting", "done", "dropped"}
        if v not in allowed:
            raise ValueError(f"status 必须是 {allowed} 之一，收到 '{v}'")
        return v


class UpdateFieldInput(BaseModel):
    """update_field Tool Call 的输入。"""
    node_id: str
    field: str
    value: Optional[str] = None

    @field_validator("field")
    @classmethod
    def check_field(cls, v: str) -> str:
        allowed = {"title", "summary", "why", "next_step", "owner", "deadline", "node_type"}
        if v not in allowed:
            raise ValueError(f"可修改字段: {allowed}，收到 '{v}'")
        return v


# --- Internal Dataclasses ---

@dataclass
class Node:
    id: str
    title: str
    status: str  # inbox|active|waiting|done|dropped
    node_type: str  # goal|project|milestone|task|unknown
    is_root: bool = False
    parent_id: Optional[str] = None
    summary: Optional[str] = None
    why: Optional[str] = None
    next_step: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None  # ISO 8601
    is_persistent: bool = False
    created_at: str = ""      # ISO 8601 UTC
    updated_at: str = ""
    status_changed_at: str = ""
    archived_at: Optional[str] = None


@dataclass
class Edge:
    source_id: str
    target_id: str
    edge_type: str  # parent|depends_on
    created_at: str = ""


@dataclass
class ToolResult:
    success: bool
    command_id: str
    event_id: Optional[str] = None
    data: Optional[dict] = None
    error: Optional[str] = None
    suggestion: Optional[str] = None
    affected_nodes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Alert:
    node_id: str
    alert_type: str  # blocked|at_risk|stale|anti_amnesia
    message: str
    severity: int  # 1=highest
    first_seen: str  # ISO 8601


@dataclass
class ContextBundle:
    l0_dashboard: str
    l_alert: str
    l1_neighborhood: str
    l2_focus: str
    total_tokens: int
    focus_node_id: Optional[str] = None
