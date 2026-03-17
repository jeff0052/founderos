"""Recursive bottom-up rollup_status computation."""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .store import Store

_TERMINAL = frozenset({"done", "dropped"})


def compute_rollup(store: "Store", node_id: str, _cache: Optional[dict[str, str]] = None) -> str:
    """递归计算 rollup_status。返回 status 字符串。

    Rules (first match wins):
    1. No participating children → own status
    2. Any child rollup = active → active
    3. Any child rollup = waiting → waiting
    4. All terminal, at least one done → done
    5. All dropped → dropped

    inbox children are excluded. Archived children are included.
    """
    if _cache is not None and node_id in _cache:
        return _cache[node_id]

    node = store.get_node(node_id)
    if node is None:
        raise ValueError(f"Node not found: {node_id}")

    children = store.get_children(node_id, include_archived=True)
    # Filter out inbox children (FR-7 isolation)
    participating = [c for c in children if c.status != "inbox"]

    if not participating:
        # Rule 1: no participating children → own status
        result = node.status
    else:
        # Recursively compute rollup for each participating child
        child_rollups = []
        for child in participating:
            child_rollups.append(compute_rollup(store, child.id, _cache))

        # Rule 2: any active → active
        if "active" in child_rollups:
            result = "active"
        # Rule 3: any waiting → waiting
        elif "waiting" in child_rollups:
            result = "waiting"
        # All must be terminal at this point
        elif all(s in _TERMINAL for s in child_rollups):
            # Rule 4: at least one done → done
            if "done" in child_rollups:
                result = "done"
            else:
                # Rule 5: all dropped
                result = "dropped"
        else:
            # Shouldn't reach here with valid statuses, fallback to own
            result = node.status

    if _cache is not None:
        _cache[node_id] = result
    return result


def batch_compute_rollup(store: "Store", root_ids: Optional[list[str]] = None) -> dict[str, str]:
    """批量计算 rollup。root_ids=None 时计算所有根节点的子树。

    Returns dict mapping node_id → rollup_status for all nodes in the subtrees.
    """
    if root_ids is None:
        roots = store.list_nodes(filters={"is_root": True}, limit=10000)
        root_ids = [r.id for r in roots]

    cache: dict[str, str] = {}

    def _walk(nid: str) -> None:
        """Post-order walk: compute children first, then self."""
        children = store.get_children(nid, include_archived=True)
        for child in children:
            if child.id not in cache:
                _walk(child.id)
        compute_rollup(store, nid, cache)

    for rid in root_ids:
        _walk(rid)

    return cache
