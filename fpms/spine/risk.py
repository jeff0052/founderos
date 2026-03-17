"""Risk mark computation: blocked, at-risk, stale. Pure functions, no side effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .store import Store
    from .models import Node

TERMINAL_STATUSES = frozenset({"done", "dropped"})
STALE_THRESHOLD = timedelta(days=7)
AT_RISK_THRESHOLD = timedelta(hours=48)


@dataclass
class RiskMarks:
    blocked: bool = False
    at_risk: bool = False
    stale: bool = False
    blocked_by: list[str] = field(default_factory=list)


def _parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def compute_risks(node: "Node", dependencies: list["Node"]) -> RiskMarks:
    """计算单个节点的风险标记。纯函数，无副作用。"""
    now = datetime.now(timezone.utc)
    marks = RiskMarks()

    is_terminal = node.status in TERMINAL_STATUSES

    # blocked: 非终态 + 存在 depends_on 目标 status ≠ done
    if not is_terminal and dependencies:
        blocked_by = [d.id for d in dependencies if d.status != "done"]
        if blocked_by:
            marks.blocked = True
            marks.blocked_by = blocked_by

    # at_risk: deadline < NOW()+48h 且非终态
    if not is_terminal and node.deadline:
        deadline_dt = _parse_iso(node.deadline)
        if deadline_dt < now + AT_RISK_THRESHOLD:
            marks.at_risk = True

    # stale: active/waiting 看 status_changed_at, inbox 看 created_at
    if node.status in ("active", "waiting"):
        ref_dt = _parse_iso(node.status_changed_at)
        if ref_dt < now - STALE_THRESHOLD:
            marks.stale = True
    elif node.status == "inbox":
        ref_dt = _parse_iso(node.created_at)
        if ref_dt < now - STALE_THRESHOLD:
            marks.stale = True

    return marks


def batch_compute_risks(store: "Store", node_ids: Optional[list[str]] = None) -> dict[str, RiskMarks]:
    """批量计算风险标记。node_ids=None 时计算所有活跃节点。"""
    if node_ids is not None:
        nodes = [store.get_node(nid) for nid in node_ids]
        nodes = [n for n in nodes if n is not None]
    else:
        # All non-terminal, non-archived nodes
        nodes = []
        for status in ("inbox", "active", "waiting"):
            nodes.extend(store.list_nodes(filters={"status": status}))

    result: dict[str, RiskMarks] = {}
    for node in nodes:
        deps = store.get_dependencies(node.id)
        result[node.id] = compute_risks(node, deps)

    return result
