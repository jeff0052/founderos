"""Data persistence layer: CRUD, transactions, audit outbox, event flush."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Generator, List, Optional

from .models import Node, Edge
from .schema import init_db


# node_type -> id prefix
_PREFIX_MAP = {
    "goal": "goal",
    "project": "project",
    "milestone": "milestone",
    "task": "task",
    "unknown": "unknown",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_id(node_type: str, conn: sqlite3.Connection) -> str:
    prefix = _PREFIX_MAP.get(node_type, "node")
    for _ in range(100):
        hex4 = secrets.token_hex(2)  # 4 hex chars
        nid = "{}-{}".format(prefix, hex4)
        cur = conn.execute("SELECT 1 FROM nodes WHERE id=?", (nid,))
        if cur.fetchone() is None:
            return nid
    raise RuntimeError("Failed to generate unique node id after 100 retries")


def _row_to_node(row: sqlite3.Row) -> Node:
    return Node(
        id=row["id"],
        title=row["title"],
        status=row["status"],
        node_type=row["node_type"],
        is_root=bool(row["is_root"]),
        parent_id=row["parent_id"],
        summary=row["summary"],
        why=row["why"],
        next_step=row["next_step"],
        owner=row["owner"],
        deadline=row["deadline"],
        is_persistent=bool(row["is_persistent"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        status_changed_at=row["status_changed_at"],
        archived_at=row["archived_at"],
    )


def _row_to_edge(row: sqlite3.Row) -> Edge:
    return Edge(
        source_id=row["source_id"],
        target_id=row["target_id"],
        edge_type=row["edge_type"],
        created_at=row["created_at"],
    )


class Store:
    def __init__(self, db_path: str, events_path: str) -> None:
        self.db_path = db_path
        self._conn = init_db(db_path)
        self._conn.row_factory = sqlite3.Row
        # Disable autocommit so we control transactions manually
        self._conn.isolation_level = "DEFERRED"
        self._events_path = events_path
        self._in_transaction = False

    # --- Node CRUD ---
    def create_node(self, node: Node) -> Node:
        now = _utcnow_iso()
        nid = node.id if node.id else _generate_id(node.node_type, self._conn)
        self._conn.execute(
            """INSERT INTO nodes
               (id, title, status, node_type, is_root, parent_id,
                summary, why, next_step, owner, deadline,
                is_persistent, created_at, updated_at, status_changed_at, archived_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                nid, node.title, node.status, node.node_type,
                1 if node.is_root else 0,
                node.parent_id,
                node.summary, node.why, node.next_step, node.owner, node.deadline,
                1 if node.is_persistent else 0,
                now, now, now, node.archived_at,
            ),
        )
        # Atomic: facts + audit in same transaction
        self._conn.execute(
            "INSERT INTO audit_outbox (event_json, created_at, flushed) VALUES (?,?,0)",
            (json.dumps({"tool_name": "create_node", "node_id": nid, "timestamp": now}), now),
        )
        if not self._in_transaction:
            self._conn.commit()
        return self.get_node(nid)  # type: ignore

    def get_node(self, node_id: str) -> Optional[Node]:
        cur = self._conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_node(row)

    def update_node(self, node_id: str, fields: dict) -> Node:
        existing = self.get_node(node_id)
        if existing is None:
            raise ValueError("Node not found: {}".format(node_id))

        fields = dict(fields)  # copy
        fields["updated_at"] = _utcnow_iso()

        set_parts = []  # type: List[str]
        values = []  # type: List
        for k, v in fields.items():
            if k == "is_root":
                set_parts.append("is_root=?")
                values.append(1 if v else 0)
            elif k == "is_persistent":
                set_parts.append("is_persistent=?")
                values.append(1 if v else 0)
            else:
                set_parts.append("{}=?".format(k))
                values.append(v)
        values.append(node_id)

        sql = "UPDATE nodes SET {} WHERE id=?".format(", ".join(set_parts))
        self._conn.execute(sql, values)
        if not self._in_transaction:
            self._conn.commit()
        return self.get_node(node_id)  # type: ignore

    def list_nodes(self, filters: Optional[dict] = None,
                   order_by: str = "updated_at",
                   limit: int = 50, offset: int = 0) -> List[Node]:
        clauses = []  # type: List[str]
        params = []  # type: List
        if filters:
            for k, v in filters.items():
                if k == "is_root":
                    clauses.append("is_root=?")
                    params.append(1 if v else 0)
                elif k == "archived":
                    if v:
                        clauses.append("archived_at IS NOT NULL")
                    else:
                        clauses.append("archived_at IS NULL")
                else:
                    clauses.append("{}=?".format(k))
                    params.append(v)

        sql = "SELECT * FROM nodes"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY {}".format(order_by)
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur = self._conn.execute(sql, params)
        return [_row_to_node(r) for r in cur.fetchall()]

    # --- Edge CRUD ---
    def add_edge(self, edge: Edge) -> Edge:
        now = _utcnow_iso()
        try:
            self._conn.execute(
                "INSERT INTO edges (source_id, target_id, edge_type, created_at) VALUES (?,?,?,?)",
                (edge.source_id, edge.target_id, edge.edge_type, now),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError("Duplicate edge: {}".format(e))
        # Sync parent_id if edge_type is 'parent'
        if edge.edge_type == "parent":
            self._conn.execute(
                "UPDATE nodes SET parent_id=?, is_root=0 WHERE id=?",
                (edge.target_id, edge.source_id),
            )
        if not self._in_transaction:
            self._conn.commit()
        return Edge(
            source_id=edge.source_id,
            target_id=edge.target_id,
            edge_type=edge.edge_type,
            created_at=now,
        )

    def remove_edge(self, source_id: str, target_id: str, edge_type: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM edges WHERE source_id=? AND target_id=? AND edge_type=?",
            (source_id, target_id, edge_type),
        )
        if cur.rowcount > 0:
            # Sync parent_id if edge_type is 'parent'
            if edge_type == "parent":
                self._conn.execute(
                    "UPDATE nodes SET parent_id=NULL WHERE id=? AND parent_id=?",
                    (source_id, target_id),
                )
            if not self._in_transaction:
                self._conn.commit()
            return True
        return False

    def get_edges(self, node_id: str, edge_type: Optional[str] = None,
                  direction: str = "outgoing") -> List[Edge]:
        clauses = []  # type: List[str]
        params = []  # type: List
        if direction == "outgoing":
            clauses.append("source_id=?")
            params.append(node_id)
        elif direction == "incoming":
            clauses.append("target_id=?")
            params.append(node_id)
        else:  # both
            clauses.append("(source_id=? OR target_id=?)")
            params.extend([node_id, node_id])

        if edge_type is not None:
            clauses.append("edge_type=?")
            params.append(edge_type)

        sql = "SELECT * FROM edges WHERE " + " AND ".join(clauses)
        cur = self._conn.execute(sql, params)
        return [_row_to_edge(r) for r in cur.fetchall()]

    # --- Graph Queries ---
    def get_children(self, node_id: str, include_archived: bool = False) -> List[Node]:
        if include_archived:
            cur = self._conn.execute(
                "SELECT * FROM nodes WHERE parent_id=?", (node_id,)
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM nodes WHERE parent_id=? AND archived_at IS NULL",
                (node_id,),
            )
        return [_row_to_node(r) for r in cur.fetchall()]

    def get_parent(self, node_id: str) -> Optional[Node]:
        node = self.get_node(node_id)
        if node is None or node.parent_id is None:
            return None
        return self.get_node(node.parent_id)

    def get_dependencies(self, node_id: str) -> List[Node]:
        cur = self._conn.execute(
            "SELECT target_id FROM edges WHERE source_id=? AND edge_type='depends_on'",
            (node_id,),
        )
        result = []
        for row in cur.fetchall():
            n = self.get_node(row["target_id"])
            if n is not None:
                result.append(n)
        return result

    def get_dependents(self, node_id: str) -> List[Node]:
        cur = self._conn.execute(
            "SELECT source_id FROM edges WHERE target_id=? AND edge_type='depends_on'",
            (node_id,),
        )
        result = []
        for row in cur.fetchall():
            n = self.get_node(row["source_id"])
            if n is not None:
                result.append(n)
        return result

    def get_siblings(self, node_id: str) -> List[Node]:
        node = self.get_node(node_id)
        if node is None or node.parent_id is None:
            return []
        cur = self._conn.execute(
            "SELECT * FROM nodes WHERE parent_id=? AND id!=?",
            (node.parent_id, node_id),
        )
        return [_row_to_node(r) for r in cur.fetchall()]

    def get_all_edges(self) -> List[Edge]:
        cur = self._conn.execute("SELECT * FROM edges")
        return [_row_to_edge(r) for r in cur.fetchall()]

    def get_ancestors(self, node_id: str) -> List[str]:
        cur = self._conn.execute(
            """WITH RECURSIVE anc(nid) AS (
                 SELECT parent_id FROM nodes WHERE id=?
                 UNION
                 SELECT n.parent_id FROM nodes n JOIN anc a ON n.id=a.nid
               )
               SELECT nid FROM anc WHERE nid IS NOT NULL""",
            (node_id,),
        )
        return [row[0] for row in cur.fetchall()]

    def get_descendants(self, node_id: str) -> List[str]:
        cur = self._conn.execute(
            """WITH RECURSIVE desc_nodes(nid) AS (
                 SELECT id FROM nodes WHERE parent_id=?
                 UNION
                 SELECT n.id FROM nodes n JOIN desc_nodes d ON n.parent_id=d.nid
               )
               SELECT nid FROM desc_nodes""",
            (node_id,),
        )
        return [row[0] for row in cur.fetchall()]

    # --- Session State ---
    def get_session(self, key: str) -> Optional[dict]:
        cur = self._conn.execute(
            "SELECT value FROM session_state WHERE key=?", (key,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return json.loads(row["value"])

    def set_session(self, key: str, value: dict) -> None:
        now = _utcnow_iso()
        self._conn.execute(
            """INSERT INTO session_state (key, value, updated_at)
               VALUES (?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (key, json.dumps(value), now),
        )
        if not self._in_transaction:
            self._conn.commit()

    # --- Transaction (Context Manager) ---
    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        was_in_transaction = self._in_transaction
        if not was_in_transaction:
            self._conn.execute("BEGIN")
            self._in_transaction = True
        try:
            yield
            if not was_in_transaction:
                self._conn.commit()
                self._in_transaction = False
        except BaseException:
            if not was_in_transaction:
                self._conn.rollback()
                self._in_transaction = False
            raise

    # --- Audit Outbox ---
    def write_event(self, event: dict) -> None:
        now = _utcnow_iso()
        self._conn.execute(
            "INSERT INTO audit_outbox (event_json, created_at, flushed) VALUES (?,?,0)",
            (json.dumps(event), now),
        )

    def flush_events(self) -> int:
        cur = self._conn.execute(
            "SELECT id, event_json FROM audit_outbox WHERE flushed=0 ORDER BY id"
        )
        rows = cur.fetchall()
        if not rows:
            return 0

        with open(self._events_path, "a") as f:
            for row in rows:
                f.write(row["event_json"] + "\n")

        ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in ids)
        self._conn.execute(
            "UPDATE audit_outbox SET flushed=1 WHERE id IN ({})".format(placeholders),
            ids,
        )
        self._conn.commit()
        return len(rows)
