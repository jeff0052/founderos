"""Validation layer: status transitions, DAG safety, XOR, active domain."""

from __future__ import annotations

import sqlite3
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .store import Store
    from .models import Node


# ---------------------------------------------------------------------------
# Status machine
# ---------------------------------------------------------------------------

_LEGAL_TRANSITIONS = {
    "inbox":    {"active", "waiting", "dropped"},
    "active":   {"waiting", "done", "dropped"},
    "waiting":  {"active", "done", "dropped"},
    "done":     {"active"},
    "dropped":  {"inbox"},
}

_TERMINAL = {"done", "dropped"}


class ValidationError(Exception):
    """校验失败。包含 code, message, suggestion (actionable)。"""

    def __init__(self, code: str, message: str, suggestion: str = "") -> None:
        self.code = code
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_path(store: "Store") -> str:
    for attr in ("db_path", "_db_path"):
        if hasattr(store, attr):
            return getattr(store, attr)
    raise AttributeError("Cannot find db_path on store")


# ---------------------------------------------------------------------------
# validate_status_transition
# ---------------------------------------------------------------------------

def validate_status_transition(
    current: str,
    target: str,
    node: "Node",
    children: List["Node"],
) -> None:
    """校验状态迁移合法性。不合法则 raise ValidationError（含 actionable suggestion）。"""

    # 1. Legal transition check
    allowed = _LEGAL_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValidationError(
            code="ILLEGAL_TRANSITION",
            message=f"Status transition {current!r} -> {target!r} is not allowed.",
            suggestion=f"Allowed transitions from {current!r}: {sorted(allowed)}.",
        )

    # 2. Preconditions for inbox -> active/waiting
    if current == "inbox" and target in ("active", "waiting"):
        if not node.summary:
            raise ValidationError(
                code="MISSING_SUMMARY",
                message=f"Cannot transition to {target!r}: node {node.id!r} has no summary.",
                suggestion=f"请先调用 update_field(node_id='{node.id}', field='summary', value='...') 补充 summary。",
            )
        if not node.parent_id and not node.is_root:
            raise ValidationError(
                code="MISSING_PARENT",
                message=f"Cannot transition to {target!r}: node {node.id!r} has no parent_id and is_root=False.",
                suggestion=f"请先调用 attach_node(node_id='{node.id}', parent_id='...') 或 update_field(node_id='{node.id}', field='is_root', value=true)。",
            )

    # 3. Precondition for -> done: all children must be terminal
    if target == "done" and children:
        non_terminal = [c for c in children if c.status not in _TERMINAL]
        if non_terminal:
            ids = ", ".join(c.id for c in non_terminal)
            raise ValidationError(
                code="CHILDREN_NOT_TERMINAL",
                message=f"Cannot mark as done: non-terminal children: {ids}.",
                suggestion=f"请先将子节点 {ids} 标记为 done 或 dropped。",
            )


# ---------------------------------------------------------------------------
# validate_xor_constraint
# ---------------------------------------------------------------------------

def validate_xor_constraint(is_root: bool, parent_id: Optional[str]) -> None:
    """检查 is_root 和 parent_id 互斥。违反则 raise ValidationError。"""
    if is_root and parent_id is not None:
        raise ValidationError(
            code="XOR_VIOLATION",
            message="is_root=True and parent_id are mutually exclusive.",
            suggestion="Set is_root=False or remove parent_id.",
        )


# ---------------------------------------------------------------------------
# validate_active_domain
# ---------------------------------------------------------------------------

def validate_active_domain(node: "Node") -> None:
    """检查目标节点非归档状态。已归档则 raise ValidationError。"""
    if node.archived_at is not None:
        raise ValidationError(
            code="ARCHIVED_NODE",
            message=f"Node {node.id!r} is archived (archived_at={node.archived_at}).",
            suggestion=f"请先调用 unarchive(node_id='{node.id}') 恢复节点。",
        )


# ---------------------------------------------------------------------------
# validate_dag_safety
# ---------------------------------------------------------------------------

def validate_dag_safety(
    store: "Store",
    source_id: str,
    target_id: str,
    edge_type: str,
) -> None:
    """统一 DAG 环路检测（WITH RECURSIVE CTE）。有环则 raise ValidationError。"""
    db = _db_path(store)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        # Check: can source_id be reached from target_id via existing edges?
        # If yes, adding source->target would create a cycle.
        row = conn.execute(
            """
            WITH RECURSIVE reachable(id) AS (
                SELECT ?
                UNION
                SELECT e.target_id FROM edges e
                JOIN reachable r ON e.source_id = r.id
                WHERE e.edge_type IN ('parent', 'depends_on')
            )
            SELECT 1 FROM reachable WHERE id = ?
            """,
            (target_id, source_id),
        ).fetchone()
        if row:
            raise ValidationError(
                code="CYCLE_DETECTED",
                message=f"Adding edge {source_id!r} -> {target_id!r} ({edge_type}) would create a cycle.",
                suggestion="Review the dependency/parent graph and remove a conflicting edge first.",
            )

        # Cross-dimensional deadlock: child depends_on ancestor
        if edge_type == "depends_on":
            ancestors = conn.execute(
                """
                WITH RECURSIVE anc(id) AS (
                    SELECT parent_id FROM nodes WHERE id = ?
                    UNION
                    SELECT n.parent_id FROM nodes n
                    JOIN anc a ON n.id = a.id
                    WHERE n.parent_id IS NOT NULL
                )
                SELECT id FROM anc WHERE id IS NOT NULL
                """,
                (source_id,),
            ).fetchall()
            ancestor_ids = {r[0] for r in ancestors}
            if target_id in ancestor_ids:
                raise ValidationError(
                    code="CROSS_DIMENSION_DEADLOCK",
                    message=f"Node {source_id!r} depends_on its ancestor {target_id!r} — cross-dimensional deadlock.",
                    suggestion="A child node cannot depend on its own ancestor via depends_on.",
                )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# validate_attach (composite)
# ---------------------------------------------------------------------------

def validate_attach(store: "Store", node_id: str, new_parent_id: str) -> None:
    """综合校验 attach: 活跃域 + DAG 安全。"""
    # Check parent is not archived
    db = _db_path(store)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        row = conn.execute(
            "SELECT id, title, status, node_type, is_root, parent_id, summary, "
            "why, next_step, owner, deadline, is_persistent, created_at, updated_at, "
            "status_changed_at, archived_at FROM nodes WHERE id = ?",
            (new_parent_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValidationError(
            code="NODE_NOT_FOUND",
            message=f"Parent node {new_parent_id!r} not found.",
            suggestion="Check the node_id and try again.",
        )

    from .models import Node
    parent_node = Node(
        id=row[0], title=row[1], status=row[2], node_type=row[3],
        is_root=bool(row[4]), parent_id=row[5], summary=row[6],
        why=row[7], next_step=row[8], owner=row[9], deadline=row[10],
        is_persistent=bool(row[11]), created_at=row[12], updated_at=row[13],
        status_changed_at=row[14], archived_at=row[15],
    )
    validate_active_domain(parent_node)

    # DAG safety: adding node_id -> new_parent_id (parent edge)
    validate_dag_safety(store, node_id, new_parent_id, "parent")


# ---------------------------------------------------------------------------
# validate_dependency (composite)
# ---------------------------------------------------------------------------

def validate_dependency(store: "Store", source_id: str, target_id: str) -> None:
    """综合校验 add_dependency: 不能自依赖 + 活跃域 + DAG 安全。"""
    # Self-dependency check
    if source_id == target_id:
        raise ValidationError(
            code="SELF_DEPENDENCY",
            message=f"Node {source_id!r} cannot depend on itself.",
            suggestion="Use a different target node.",
        )

    # Check target is not archived
    db = _db_path(store)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        row = conn.execute(
            "SELECT id, title, status, node_type, is_root, parent_id, summary, "
            "why, next_step, owner, deadline, is_persistent, created_at, updated_at, "
            "status_changed_at, archived_at FROM nodes WHERE id = ?",
            (target_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValidationError(
            code="NODE_NOT_FOUND",
            message=f"Target node {target_id!r} not found.",
            suggestion="Check the node_id and try again.",
        )

    from .models import Node
    target_node = Node(
        id=row[0], title=row[1], status=row[2], node_type=row[3],
        is_root=bool(row[4]), parent_id=row[5], summary=row[6],
        why=row[7], next_step=row[8], owner=row[9], deadline=row[10],
        is_persistent=bool(row[11]), created_at=row[12], updated_at=row[13],
        status_changed_at=row[14], archived_at=row[15],
    )
    validate_active_domain(target_node)

    # DAG safety
    validate_dag_safety(store, source_id, target_id, "depends_on")
