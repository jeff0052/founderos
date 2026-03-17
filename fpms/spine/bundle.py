"""Context bundle assembly: L0/L_Alert/L1/L2 with trim."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .models import ContextBundle, Node
from .focus import FocusResult
from .narrative import read_narrative

if TYPE_CHECKING:
    from .store import Store


# ── Token estimation ─────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """估算 token 数。len(text) // 2 近似。"""
    return len(text) // 2


# ── Renderers ────────────────────────────────────────────────────

def _render_node_summary(node: Node) -> str:
    """Render a single node as a compact summary line."""
    parts = [f"- [{node.status}] {node.id}: {node.title}"]
    if node.summary:
        parts.append(f"  summary: {node.summary}")
    return "\n".join(parts)


def _render_node_full(node: Node) -> str:
    """Render all non-empty fields of a node for L2."""
    lines = [f"# {node.id}: {node.title}"]
    fields = [
        ("status", node.status),
        ("node_type", node.node_type),
        ("summary", node.summary),
        ("why", node.why),
        ("next_step", node.next_step),
        ("owner", node.owner),
        ("deadline", node.deadline),
        ("parent_id", node.parent_id),
        ("is_root", str(node.is_root) if node.is_root else None),
        ("created_at", node.created_at),
        ("updated_at", node.updated_at),
        ("status_changed_at", node.status_changed_at),
    ]
    for name, value in fields:
        if value:
            lines.append(f"{name}: {value}")
    return "\n".join(lines)


# ── L1 builders (each returns a section string) ─────────────────

_TERMINAL = {"done", "dropped"}


def _build_parent_section(store: "Store", node_id: str) -> str:
    parent = store.get_parent(node_id)
    if parent is None:
        return ""
    return "### Parent\n" + _render_node_summary(parent)


def _build_children_section(store: "Store", node_id: str) -> str:
    children = store.get_children(node_id)
    active_children = [c for c in children if c.status not in _TERMINAL]
    if not active_children:
        return ""
    lines = ["### Children (non-terminal)"]
    for c in active_children[:15]:
        lines.append(_render_node_summary(c))
    return "\n".join(lines)


def _build_depends_on_section(store: "Store", node_id: str) -> str:
    deps = store.get_dependencies(node_id)
    if not deps:
        return ""
    lines = ["### Depends On"]
    for d in deps[:10]:
        lines.append(_render_node_summary(d))
    return "\n".join(lines)


def _build_depended_by_section(store: "Store", node_id: str) -> str:
    dependents = store.get_dependents(node_id)
    if not dependents:
        return ""
    lines = ["### Depended By"]
    for d in dependents[:10]:
        lines.append(_render_node_summary(d))
    return "\n".join(lines)


def _build_siblings_section(store: "Store", node_id: str) -> str:
    siblings = store.get_siblings(node_id)
    if not siblings:
        return ""
    lines = ["### Siblings"]
    for s in siblings[:10]:
        lines.append(_render_node_summary(s))
    return "\n".join(lines)


def _build_secondary_section(store: "Store", node_ids: list[str]) -> str:
    """Render secondary focus nodes as L1 summaries."""
    if not node_ids:
        return ""
    lines = ["### Secondary Focus"]
    for nid in node_ids:
        node = store.get_node(nid)
        if node is not None:
            lines.append(_render_node_summary(node))
    return "\n".join(lines) if len(lines) > 1 else ""


# ── L1 assembly with trim ───────────────────────────────────────

# Trim order: siblings → children → depended_by → depends_on → parent
_TRIM_ORDER = ["siblings", "children", "depended_by", "depends_on", "parent"]


def _assemble_l1(store: "Store", node_id: str,
                 secondaries: list[str], budget: int) -> str:
    """Build L1 neighborhood, trimming sections if over budget."""
    sections: dict[str, str] = {}
    sections["parent"] = _build_parent_section(store, node_id)
    sections["children"] = _build_children_section(store, node_id)
    sections["depends_on"] = _build_depends_on_section(store, node_id)
    sections["depended_by"] = _build_depended_by_section(store, node_id)
    sections["siblings"] = _build_siblings_section(store, node_id)

    secondary_text = _build_secondary_section(store, secondaries)

    # Combine all non-empty sections
    def _combine() -> str:
        parts = []
        for key in ["parent", "children", "depends_on", "depended_by", "siblings"]:
            if sections[key]:
                parts.append(sections[key])
        if secondary_text:
            parts.append(secondary_text)
        return "\n\n".join(parts)

    result = _combine()
    if estimate_tokens(result) <= budget:
        return result

    # Trim in order until within budget
    for key in _TRIM_ORDER:
        sections[key] = ""
        result = _combine()
        if estimate_tokens(result) <= budget:
            return result

    return result


# ── L2 assembly ──────────────────────────────────────────────────

def _assemble_l2(store: "Store", node_id: str,
                 narratives_dir: str, last_n: int = 5) -> str:
    """Build L2: full node fields + recent narrative."""
    node = store.get_node(node_id)
    if node is None:
        return ""

    parts = [_render_node_full(node)]

    narrative_text = read_narrative(narratives_dir, node_id,
                                   last_n_entries=last_n)
    if narrative_text:
        parts.append("### Recent Narrative\n" + narrative_text)

    return "\n\n".join(parts)


# ── Main assembly ────────────────────────────────────────────────

def assemble(store: "Store", focus: FocusResult,
             dashboard_md: str, alerts_md: str,
             narratives_dir: str = "",
             max_tokens: int = 10000) -> ContextBundle:
    """组装完整认知包。裁剪铁律: 因果 > 关系。"""

    l0 = dashboard_md
    l_alert = alerts_md

    # No focus → L0 + L_Alert only
    if focus.primary is None:
        total = estimate_tokens(l0 + l_alert)
        return ContextBundle(
            l0_dashboard=l0,
            l_alert=l_alert,
            l1_neighborhood="",
            l2_focus="",
            total_tokens=total,
            focus_node_id=None,
        )

    focus_id = focus.primary

    # Budget: max_tokens minus L0 + L_Alert overhead
    base_tokens = estimate_tokens(l0 + l_alert)
    remaining = max(0, max_tokens - base_tokens)

    # Build L2 first (higher priority than L1)
    l2 = _assemble_l2(store, focus_id, narratives_dir)
    l2_tokens = estimate_tokens(l2)

    # L1 budget = remaining minus L2
    l1_budget = max(0, remaining - l2_tokens)
    l1 = _assemble_l1(store, focus_id, focus.secondaries, l1_budget)
    l1_tokens = estimate_tokens(l1)

    # If still over budget, trim L2 as last resort
    total = base_tokens + l1_tokens + l2_tokens
    if total > max_tokens and l2:
        # Truncate L2 text to fit
        allowed_l2_chars = max(0, (max_tokens - base_tokens - l1_tokens) * 2)
        l2 = l2[:allowed_l2_chars]
        l2_tokens = estimate_tokens(l2)

    total = estimate_tokens(l0 + l_alert + l1 + l2)

    return ContextBundle(
        l0_dashboard=l0,
        l_alert=l_alert,
        l1_neighborhood=l1,
        l2_focus=l2,
        total_tokens=total,
        focus_node_id=focus_id,
    )
