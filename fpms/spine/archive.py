"""Archive management: scan candidates, archive, unarchive."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

from .models import Node

if TYPE_CHECKING:
    from .store import Store

_TERMINAL = {"done", "dropped"}
_COOLDOWN_DAYS = 7


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def scan_archive_candidates(store: "Store") -> list[str]:
    """扫描满足归档条件的节点 id 列表。

    条件（全部满足）：
    1. status ∈ {done, dropped}
    2. status_changed_at < NOW() - 7 days
    3. 无未归档节点 depends_on 此节点
    4. 无未归档子孙节点
    5. is_persistent = false
    6. 未已归档 (archived_at IS NULL)
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_COOLDOWN_DAYS)).isoformat()

    # Step 1: SQL gets basic candidates (terminal, cooled, non-persistent, non-archived)
    cur = store._conn.execute(
        """
        SELECT id FROM nodes
        WHERE status IN ('done', 'dropped')
          AND status_changed_at < ?
          AND is_persistent = 0
          AND archived_at IS NULL
        """,
        (cutoff,),
    )
    basic_candidates = [row[0] for row in cur.fetchall()]

    # Step 2: filter out nodes with non-archived dependents
    result = []
    for nid in basic_candidates:
        # Check: any non-archived node depends_on this node?
        dependents = store.get_dependents(nid)
        if any(d.archived_at is None for d in dependents):
            continue

        # Check: any non-archived descendant?
        desc_ids = store.get_descendants(nid)
        if desc_ids:
            has_active_desc = False
            for did in desc_ids:
                desc_node = store.get_node(did)
                if desc_node is not None and desc_node.archived_at is None:
                    has_active_desc = True
                    break
            if has_active_desc:
                continue

        result.append(nid)

    return result


def archive_nodes(store: "Store", node_ids: list[str]) -> int:
    """执行归档。设置 archived_at=NOW()。返回归档数量。"""
    if not node_ids:
        return 0
    now = _utcnow_iso()
    count = 0
    with store.transaction():
        for nid in node_ids:
            node = store.get_node(nid)
            if node is None or node.archived_at is not None:
                continue
            store.update_node(nid, {"archived_at": now})
            store.write_event({
                "tool_name": "archive_node",
                "node_id": nid,
                "timestamp": now,
            })
            count += 1
    return count


def unarchive_node(store: "Store", node_id: str,
                    new_status: Optional[str] = None) -> Node:
    """解封节点。强制 status_changed_at=NOW()。可选原子状态转换。"""
    node = store.get_node(node_id)
    if node is None:
        raise ValueError(
            f"Node not found: {node_id}. "
            f"Use search_nodes to find the correct id."
        )
    if node.archived_at is None:
        raise ValueError(
            f"Node {node_id} is not archived. "
            f"Use get_node to check current state."
        )

    now = _utcnow_iso()
    fields: dict = {
        "archived_at": None,
        "status_changed_at": now,
    }
    if new_status is not None:
        fields["status"] = new_status

    with store.transaction():
        store.update_node(node_id, fields)
        store.write_event({
            "tool_name": "unarchive_node",
            "node_id": node_id,
            "new_status": new_status,
            "timestamp": now,
        })

    return store.get_node(node_id)  # type: ignore
