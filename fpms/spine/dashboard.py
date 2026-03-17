"""Global dashboard generation: L0 tree rendering."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from .risk import RiskMarks, batch_compute_risks

if TYPE_CHECKING:
    from .store import Store
    from .models import Node

_STATUS_ICON = {
    "inbox": "📥",
    "active": "🔵",
    "waiting": "⏳",
    "done": "✅",
    "dropped": "❌",
}

# Risk severity for sorting: higher = more severe
_RISK_SEVERITY = {"blocked": 3, "at_risk": 2, "stale": 1}


def _estimate_tokens(text: str) -> int:
    """len(text) / 2 — 中英混合近似。"""
    return max(1, len(text) // 2)


def _max_risk_score(marks: RiskMarks) -> int:
    """Return the highest risk severity for a node's marks."""
    score = 0
    if marks.blocked:
        score = max(score, _RISK_SEVERITY["blocked"])
    if marks.at_risk:
        score = max(score, _RISK_SEVERITY["at_risk"])
    if marks.stale:
        score = max(score, _RISK_SEVERITY["stale"])
    return score


def _subtree_max_risk(
    node_id: str,
    children_map: Dict[str, List["Node"]],
    risk_map: Dict[str, RiskMarks],
) -> int:
    """Recursively compute the max risk severity in a subtree."""
    score = _max_risk_score(risk_map.get(node_id, RiskMarks()))
    for child in children_map.get(node_id, []):
        score = max(score, _subtree_max_risk(child.id, children_map, risk_map))
    return score


def _format_risk_suffix(node: "Node", marks: RiskMarks) -> str:
    """Build the risk/deadline suffix string for a node line."""
    parts: List[str] = []
    if marks.blocked:
        parts.append("🚫blocked")
    if marks.at_risk:
        if node.deadline:
            try:
                dt = datetime.fromisoformat(node.deadline)
                parts.append(f"🚨deadline:{dt.month}/{dt.day}")
            except ValueError:
                parts.append("🚨at-risk")
        else:
            parts.append("🚨at-risk")
    if marks.stale:
        parts.append("💤stale")
    return " ".join(parts)


def _format_node_line(node: "Node", marks: RiskMarks, prefix: str = "") -> str:
    """Format a single node line: prefix + icon + id: title [status] risks."""
    icon = _STATUS_ICON.get(node.status, "❓")
    suffix = _format_risk_suffix(node, marks)
    status_tag = f"[{icon}{node.status}]"
    line = f"{prefix}{icon} {node.id}: {node.title} {status_tag}"
    if suffix:
        line += f" {suffix}"
    return line


def _render_tree(
    node: "Node",
    children_map: Dict[str, List["Node"]],
    risk_map: Dict[str, RiskMarks],
    prefix: str = "",
    connector: str = "",
) -> List[str]:
    """Recursively render a tree node and its children as lines."""
    marks = risk_map.get(node.id, RiskMarks())
    line = _format_node_line(node, marks, prefix=connector)
    lines = [line]

    children = children_map.get(node.id, [])
    # Sort children by subtree risk (high first)
    children = sorted(
        children,
        key=lambda c: _subtree_max_risk(c.id, children_map, risk_map),
        reverse=True,
    )

    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        child_connector = prefix + ("└─ " if is_last else "├─ ")
        child_prefix = prefix + ("   " if is_last else "│  ")
        lines.extend(
            _render_tree(child, children_map, risk_map, child_prefix, child_connector)
        )
    return lines


def _collect_children_map(
    store: "Store", root_ids: List[str]
) -> Dict[str, List["Node"]]:
    """Build a map of node_id -> non-archived children for all reachable nodes."""
    children_map: Dict[str, List["Node"]] = {}
    queue = list(root_ids)
    visited = set()
    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        children = store.get_children(nid, include_archived=False)
        children_map[nid] = children
        for c in children:
            queue.append(c.id)
    return children_map


def _node_has_risk(node_id: str, children_map: Dict[str, List["Node"]],
                   risk_map: Dict[str, RiskMarks]) -> bool:
    """Check if node or any descendant has a risk mark."""
    return _subtree_max_risk(node_id, children_map, risk_map) > 0


def _truncate_tree(
    root: "Node",
    children_map: Dict[str, List["Node"]],
    risk_map: Dict[str, RiskMarks],
    max_tokens: int,
) -> List[str]:
    """Render tree with truncation: fold healthy branches when over budget."""
    # First try full render
    full_lines = _render_tree(root, children_map, risk_map, prefix="  ")
    full_text = "\n".join(full_lines)
    if _estimate_tokens(full_text) <= max_tokens:
        return full_lines

    # Need truncation: render root + risky children, fold healthy ones
    return _render_tree_truncated(root, children_map, risk_map, prefix="  ", connector="")


def _render_tree_truncated(
    node: "Node",
    children_map: Dict[str, List["Node"]],
    risk_map: Dict[str, RiskMarks],
    prefix: str = "",
    connector: str = "",
) -> List[str]:
    """Render with truncation: risky nodes expanded, healthy branches folded."""
    marks = risk_map.get(node.id, RiskMarks())
    line = _format_node_line(node, marks, prefix=connector)
    lines = [line]

    children = children_map.get(node.id, [])
    children = sorted(
        children,
        key=lambda c: _subtree_max_risk(c.id, children_map, risk_map),
        reverse=True,
    )

    risky = [c for c in children if _node_has_risk(c.id, children_map, risk_map)]
    healthy = [c for c in children if not _node_has_risk(c.id, children_map, risk_map)]

    all_visible = risky  # risky always shown
    folded_count = len(healthy)

    for i, child in enumerate(all_visible):
        is_last = i == len(all_visible) - 1 and folded_count == 0
        child_connector = prefix + ("└─ " if is_last else "├─ ")
        child_prefix = prefix + ("   " if is_last else "│  ")
        lines.extend(
            _render_tree_truncated(child, children_map, risk_map, child_prefix, child_connector)
        )

    if folded_count > 0:
        fold_line = prefix + f"└─ ... [折叠] {folded_count} 个正常推进子项"
        lines.append(fold_line)

    return lines


def render_dashboard(store: "Store", max_tokens: int = 1000) -> str:
    """生成 L0 全局看板 markdown。树形缩进 + 风险排序 + 截断。"""
    # Get all non-archived nodes
    all_nodes = store.list_nodes(filters={"archived": False}, limit=10000)
    if not all_nodes:
        return ""

    # Compute risks for all non-terminal nodes
    all_ids = [n.id for n in all_nodes]
    risk_map = batch_compute_risks(store, all_ids)

    # Zone 0: inbox + is_root (no parent) — floating inbox
    zone0_nodes = [n for n in all_nodes if n.status == "inbox" and n.parent_id is None]

    # Zone 1: root nodes that are NOT inbox-floating (active/waiting/done/dropped roots)
    zone1_roots = [
        n for n in all_nodes
        if n.parent_id is None and n.is_root and n not in zone0_nodes
    ]

    # Build children map for Zone 1 trees
    root_ids = [r.id for r in zone1_roots]
    children_map = _collect_children_map(store, root_ids)

    # Sort zone1 roots by subtree max risk
    zone1_roots.sort(
        key=lambda r: _subtree_max_risk(r.id, children_map, risk_map),
        reverse=True,
    )

    output_lines: List[str] = []

    # ── Zone 0 ──
    for n in zone0_nodes:
        marks = risk_map.get(n.id, RiskMarks())
        output_lines.append(_format_node_line(n, marks))

    # Separator between zones
    if zone0_nodes and zone1_roots:
        output_lines.append("")

    # ── Zone 1 ──
    remaining_tokens = max_tokens
    if output_lines:
        zone0_text = "\n".join(output_lines)
        remaining_tokens -= _estimate_tokens(zone0_text)

    for root in zone1_roots:
        tree_lines = _truncate_tree(root, children_map, risk_map, remaining_tokens)
        # Check if adding this tree would exceed budget
        tree_text = "\n".join(tree_lines)
        tree_tokens = _estimate_tokens(tree_text)
        if remaining_tokens - tree_tokens < 0 and output_lines:
            # Try truncated version
            tree_lines = _render_tree_truncated(
                root, children_map, risk_map, prefix="  ", connector=""
            )
            tree_text = "\n".join(tree_lines)
            tree_tokens = _estimate_tokens(tree_text)

        # Add tree icon prefix to root line
        if tree_lines:
            root_line = tree_lines[0]
            # Replace the status icon at start with 📁 prefix
            tree_lines[0] = "📁 " + root_line.lstrip()

        output_lines.extend(tree_lines)
        remaining_tokens -= tree_tokens

    return "\n".join(output_lines)
