"""Memory layer: CRUD, event sourcing, validation, decay.

Source of Truth: memory_events (append-only)
Projection: memories table (rebuildable)

PRD reference: PRD-memory-v2.2.md
"""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from .models import Memory, AddMemoryInput

if TYPE_CHECKING:
    from .store import Store


# ── Constants ────────────────────────────────────────────────────

_LAYERS = {"fact", "judgment", "scratch"}
_SUB_TYPES = {"preference", "decision", "lesson", "pattern"}
_VERIFICATIONS = {"user_confirmed", "system_verified", "auto_extracted"}
_SOURCES = {"auto", "manual", "system"}
_PRIORITIES = {"P0", "P1", "P2"}

# PRD §2.5: source × verification legal combos
_SOURCE_VERIFICATION_MAP = {
    "auto": "auto_extracted",
    "manual": "user_confirmed",
    "system": "system_verified",
}

# PRD §FR-1: forbidden words for auto source
_FORBIDDEN_WORDS_AUTO = re.compile(
    r"可能|也许|大概|推测|应该|似乎|看起来|大概率|或许|估计"
)

# PRD §2.2: fact must not contain comparative/tendency words
_FACT_FORBIDDEN_WORDS = re.compile(
    r"更好|更适合|通常|倾向于|一般来说|往往|大多数|比较"
)

# Layer weight for sorting (higher = more trusted)
_LAYER_WEIGHT = {"fact": 3, "judgment": 2, "scratch": 1}
_VERIFICATION_WEIGHT = {"user_confirmed": 3, "system_verified": 2, "auto_extracted": 1}


# ── Errors ───────────────────────────────────────────────────────

class MemoryValidationError(Exception):
    """Validation error for memory operations."""
    pass


class MemoryStateError(Exception):
    """Invalid state transition."""
    pass


# ── Helpers ──────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_memory_id(conn: sqlite3.Connection) -> str:
    for _ in range(100):
        hex6 = secrets.token_hex(3)
        mid = f"mem-{hex6}"
        cur = conn.execute("SELECT 1 FROM memories WHERE id=?", (mid,))
        if cur.fetchone() is None:
            return mid
    raise RuntimeError("Failed to generate unique memory id after 100 retries")


def _row_to_memory(row: sqlite3.Row) -> Memory:
    return Memory(
        id=row["id"],
        layer=row["layer"],
        sub_type=row["sub_type"],
        content=row["content"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        node_id=row["node_id"],
        based_on=json.loads(row["based_on"]) if row["based_on"] else [],
        confidence=row["confidence"],
        verification=row["verification"],
        source=row["source"],
        priority=row["priority"],
        needs_review=bool(row["needs_review"]),
        created_at=row["created_at"],
        last_accessed_at=row["last_accessed_at"],
        access_count=row["access_count"],
        conflict_count=row["conflict_count"],
        similar_to=row["similar_to"],
        archived_at=row["archived_at"],
    )


def _memory_to_dict(mem: Memory) -> dict:
    d = asdict(mem)
    return d


# ── Validation ───────────────────────────────────────────────────

def _validate_source_verification(source: str, verification: str) -> None:
    """PRD §2.5: enforce legal source × verification combos."""
    expected = _SOURCE_VERIFICATION_MAP.get(source)
    if expected and verification != expected:
        raise MemoryValidationError(
            f"source={source} requires verification={expected}, got {verification}"
        )


def _validate_write(inp: AddMemoryInput, verification: str) -> None:
    """PRD §FR-1: validate write rules."""
    # source × verification
    _validate_source_verification(inp.source, verification)

    # sub_type only for judgment
    if inp.sub_type and inp.layer != "judgment":
        raise MemoryValidationError("sub_type is only valid for layer=judgment")

    # fact confidence gate
    if inp.layer == "fact" and inp.confidence < 0.5:
        raise MemoryValidationError(
            f"fact requires confidence ≥ 0.5, got {inp.confidence}"
        )

    # auto source: forbidden words
    if inp.source == "auto" and _FORBIDDEN_WORDS_AUTO.search(inp.content):
        raise MemoryValidationError(
            "auto source content contains forbidden words (推断类内容不可自动入库)"
        )

    # auto + fact: no comparative/tendency words
    if inp.source == "auto" and inp.layer == "fact" and _FACT_FORBIDDEN_WORDS.search(inp.content):
        raise MemoryValidationError(
            "auto fact content contains comparative/tendency words (事实不接受比较级/倾向性内容)"
        )


def _check_similarity(conn: sqlite3.Connection, layer: str, content: str) -> Optional[str]:
    """Character n-gram overlap check for dedup. Works for CJK and latin.
    Returns similar memory ID or None."""
    def _bigrams(text: str) -> set:
        """Generate character bigrams for similarity comparison."""
        text = text.strip()
        if len(text) < 2:
            return {text}
        return {text[i:i+2] for i in range(len(text) - 1)}

    cur = conn.execute(
        "SELECT id, content FROM memories WHERE layer=? AND archived_at IS NULL",
        (layer,)
    )
    content_bg = _bigrams(content)
    if not content_bg:
        return None

    for row in cur.fetchall():
        existing_bg = _bigrams(row["content"])
        if not existing_bg:
            continue
        overlap = len(content_bg & existing_bg) / max(len(content_bg), len(existing_bg))
        if overlap > 0.7:
            return row["id"]
    return None


# ── MemoryStore ──────────────────────────────────────────────────

class MemoryStore:
    """Memory layer backed by the same SQLite DB as FPMS Store."""

    def __init__(self, store: "Store") -> None:
        self._conn = store._conn
        self._store = store

    # ── Write ────────────────────────────────────────────────────

    def add_memory(self, inp: AddMemoryInput) -> Memory:
        """PRD §FR-1: create a new memory."""
        # Determine verification from source if not explicitly set
        verification = inp.verification
        if verification is None:
            verification = _SOURCE_VERIFICATION_MAP[inp.source]

        _validate_write(inp, verification)

        now = _utcnow_iso()
        mid = _generate_memory_id(self._conn)

        # Similarity check
        similar_to = _check_similarity(self._conn, inp.layer, inp.content)

        self._conn.execute(
            """INSERT INTO memories
               (id, layer, sub_type, content, tags, node_id, based_on,
                confidence, verification, source, priority, needs_review,
                created_at, last_accessed_at, access_count, conflict_count,
                similar_to, archived_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                mid, inp.layer, inp.sub_type, inp.content,
                json.dumps(inp.tags), inp.node_id, json.dumps(inp.based_on),
                inp.confidence, verification, inp.source, inp.priority,
                0,  # needs_review
                now, now, 0, 0,
                similar_to, None,
            ),
        )

        # Event sourcing
        self._write_event(mid, "memory_created", {
            "layer": inp.layer,
            "sub_type": inp.sub_type,
            "content": inp.content,
            "tags": inp.tags,
            "source": inp.source,
            "verification": verification,
            "priority": inp.priority,
            "similar_to": similar_to,
        })

        self._conn.commit()
        return self.get_memory(mid)  # type: ignore

    def add_memories(self, inputs: List[AddMemoryInput]) -> List[Memory]:
        """Batch add. Returns list of created memories."""
        results = []
        for inp in inputs:
            results.append(self.add_memory(inp))
        return results

    # ── Read ─────────────────────────────────────────────────────

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        cur = self._conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,))
        row = cur.fetchone()
        return _row_to_memory(row) if row else None

    def search_memories(
        self,
        layer: Optional[str] = None,
        sub_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        node_id: Optional[str] = None,
        keyword: Optional[str] = None,
        priority: Optional[str] = None,
        verification: Optional[str] = None,
        needs_review: Optional[bool] = None,
        include_archived: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Memory]:
        """PRD §FR-3: deterministic search with trust-based sorting."""
        clauses: list[str] = []
        params: list = []

        if not include_archived:
            clauses.append("archived_at IS NULL")

        if layer:
            clauses.append("layer=?")
            params.append(layer)
        if sub_type:
            clauses.append("sub_type=?")
            params.append(sub_type)
        if node_id:
            clauses.append("node_id=?")
            params.append(node_id)
        if priority:
            clauses.append("priority=?")
            params.append(priority)
        if verification:
            clauses.append("verification=?")
            params.append(verification)
        if needs_review is not None:
            clauses.append("needs_review=?")
            params.append(1 if needs_review else 0)
        if keyword:
            clauses.append("content LIKE ?")
            params.append(f"%{keyword}%")
        if tags:
            for tag in tags:
                clauses.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        sql = "SELECT * FROM memories"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)

        # PRD §FR-3: trust-based sorting
        sql += """
            ORDER BY
                CASE layer WHEN 'fact' THEN 3 WHEN 'judgment' THEN 2 ELSE 1 END DESC,
                CASE verification WHEN 'user_confirmed' THEN 3 WHEN 'system_verified' THEN 2 ELSE 1 END DESC,
                confidence DESC,
                conflict_count ASC,
                last_accessed_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cur = self._conn.execute(sql, params)
        results = [_row_to_memory(r) for r in cur.fetchall()]

        # Update access_count for returned results
        now = _utcnow_iso()
        for mem in results:
            self._conn.execute(
                "UPDATE memories SET access_count=access_count+1, last_accessed_at=? WHERE id=?",
                (now, mem.id),
            )
            self._write_event(mem.id, "memory_accessed", {})
        if results:
            self._conn.commit()

        return results

    # ── Update ───────────────────────────────────────────────────

    def update_memory(self, memory_id: str, fields: dict) -> Memory:
        """PRD §4.3: update with field mutability rules."""
        mem = self.get_memory(memory_id)
        if mem is None:
            raise MemoryValidationError(f"Memory not found: {memory_id}")
        if mem.archived_at:
            raise MemoryStateError("Cannot update archived memory")

        # auto_extracted must be confirmed first
        if mem.verification == "auto_extracted":
            raise MemoryStateError(
                "Cannot update auto_extracted memory. Use confirm_memory first."
            )

        # Immutable fields
        immutable = {"id", "layer", "verification", "source", "created_at",
                     "access_count", "conflict_count", "needs_review",
                     "last_accessed_at", "archived_at", "similar_to"}
        for k in fields:
            if k in immutable:
                raise MemoryStateError(f"Field '{k}' is immutable via update_memory")

        # Validate content if changing
        if "content" in fields:
            content = fields["content"]
            if not content or not content.strip():
                raise MemoryValidationError("content must not be empty")
            if len(content) > 600:
                raise MemoryValidationError("content must be ≤200 chars (~600 bytes)")

        now = _utcnow_iso()
        old_values = {}
        set_parts: list[str] = []
        values: list = []

        for k, v in fields.items():
            if k == "tags":
                old_values[k] = mem.tags
                set_parts.append("tags=?")
                values.append(json.dumps(v))
            elif k == "based_on":
                old_values[k] = mem.based_on
                set_parts.append("based_on=?")
                values.append(json.dumps(v))
            else:
                old_values[k] = getattr(mem, k, None)
                set_parts.append(f"{k}=?")
                values.append(v)

        values.append(memory_id)
        sql = f"UPDATE memories SET {', '.join(set_parts)} WHERE id=?"
        self._conn.execute(sql, values)

        self._write_event(memory_id, "memory_updated", {
            "old": old_values,
            "new": fields,
        })

        self._conn.commit()
        return self.get_memory(memory_id)  # type: ignore

    # ── Forget (archive) ────────────────────────────────────────

    def forget(self, memory_id: str) -> Memory:
        """PRD §FR-2: archive a memory (soft delete)."""
        mem = self.get_memory(memory_id)
        if mem is None:
            raise MemoryValidationError(f"Memory not found: {memory_id}")
        if mem.archived_at:
            raise MemoryStateError("Memory already archived")

        now = _utcnow_iso()
        self._conn.execute(
            "UPDATE memories SET archived_at=? WHERE id=?",
            (now, memory_id),
        )

        # Negative feedback: bump conflict_count on similar_to chain
        if mem.similar_to:
            self._conn.execute(
                "UPDATE memories SET conflict_count=conflict_count+1 WHERE id=?",
                (mem.similar_to,),
            )
            self._check_needs_review(mem.similar_to)

        self._write_event(memory_id, "memory_archived", {"reason": "manual_forget"})
        self._conn.commit()
        return self.get_memory(memory_id)  # type: ignore

    # ── Promote (scratch → fact/judgment) ────────────────────────

    def promote_memory(
        self, memory_id: str, target_layer: str,
        sub_type: Optional[str] = None,
        confidence: Optional[float] = None,
        priority: Optional[str] = None,
    ) -> Memory:
        """PRD §4.1: promote scratch to fact/judgment with re-validation."""
        mem = self.get_memory(memory_id)
        if mem is None:
            raise MemoryValidationError(f"Memory not found: {memory_id}")
        if mem.archived_at:
            raise MemoryStateError("Cannot promote archived memory")
        if mem.layer != "scratch":
            raise MemoryStateError("Only scratch memories can be promoted")
        if target_layer not in ("fact", "judgment"):
            raise MemoryValidationError(f"target_layer must be fact or judgment, got {target_layer}")

        # Re-validate against target layer admission rules
        new_confidence = confidence if confidence is not None else mem.confidence
        new_priority = priority if priority is not None else mem.priority

        if target_layer == "fact" and new_confidence < 0.5:
            raise MemoryValidationError(
                f"fact requires confidence ≥ 0.5, got {new_confidence}"
            )

        if target_layer == "fact" and _FACT_FORBIDDEN_WORDS.search(mem.content):
            raise MemoryValidationError(
                "fact content contains comparative/tendency words"
            )

        if target_layer == "judgment" and sub_type and sub_type not in _SUB_TYPES:
            raise MemoryValidationError(f"sub_type must be one of {_SUB_TYPES}")

        now = _utcnow_iso()
        updates = {
            "layer": target_layer,
        }
        if sub_type:
            updates["sub_type"] = sub_type
        if confidence is not None:
            updates["confidence"] = confidence
        if priority is not None:
            updates["priority"] = priority

        set_parts = [f"{k}=?" for k in updates]
        values = list(updates.values())
        values.append(memory_id)

        sql = f"UPDATE memories SET {', '.join(set_parts)} WHERE id=?"
        self._conn.execute(sql, values)

        self._write_event(memory_id, "memory_promoted", {
            "from_layer": "scratch",
            "to_layer": target_layer,
            "sub_type": sub_type,
        })

        self._conn.commit()
        return self.get_memory(memory_id)  # type: ignore

    # ── Confirm (auto_extracted → user_confirmed) ────────────────

    def confirm_memory(self, memory_id: str) -> Memory:
        """PRD §4.2: upgrade verification status."""
        mem = self.get_memory(memory_id)
        if mem is None:
            raise MemoryValidationError(f"Memory not found: {memory_id}")
        if mem.archived_at:
            raise MemoryStateError("Cannot confirm archived memory")
        if mem.verification != "auto_extracted":
            raise MemoryStateError(
                f"Only auto_extracted can be confirmed, got {mem.verification}"
            )

        now = _utcnow_iso()
        self._conn.execute(
            "UPDATE memories SET verification='user_confirmed' WHERE id=?",
            (memory_id,),
        )

        self._write_event(memory_id, "memory_confirmed", {
            "from": "auto_extracted",
            "to": "user_confirmed",
        })

        self._conn.commit()
        return self.get_memory(memory_id)  # type: ignore

    # ── Decay ────────────────────────────────────────────────────

    def run_decay(self) -> dict:
        """PRD §FR-5: automated memory decay. Returns summary."""
        now = _utcnow_iso()
        now_dt = datetime.fromisoformat(now)
        archived_count = 0
        review_count = 0

        cur = self._conn.execute(
            "SELECT * FROM memories WHERE archived_at IS NULL"
        )
        for row in cur.fetchall():
            mem = _row_to_memory(row)
            created_dt = datetime.fromisoformat(mem.created_at)
            age_days = (now_dt - created_dt).days

            should_archive = False
            reason = ""

            # scratch + 7 days unpromoted
            if mem.layer == "scratch" and age_days >= 7:
                should_archive = True
                reason = "scratch_expired_7d"

            # P2 + 30 days + low access
            elif mem.priority == "P2" and age_days >= 30 and mem.access_count < 3:
                should_archive = True
                reason = "P2_expired_30d"

            # P1 + 90 days + low access
            elif mem.priority == "P1" and age_days >= 90 and mem.access_count < 5:
                should_archive = True
                reason = "P1_expired_90d"

            if should_archive:
                self._conn.execute(
                    "UPDATE memories SET archived_at=? WHERE id=?",
                    (now, mem.id),
                )
                self._write_event(mem.id, "memory_archived", {"reason": reason})
                archived_count += 1

            # conflict_count > 3 → needs_review
            if mem.conflict_count > 3 and not mem.needs_review:
                self._conn.execute(
                    "UPDATE memories SET needs_review=1 WHERE id=?",
                    (mem.id,),
                )
                review_count += 1

        self._conn.commit()
        return {"archived": archived_count, "flagged_review": review_count}

    # ── Bundle: get memories for L_Memory injection ──────────────

    def get_resident_memories(self, max_count: int = 5) -> List[Memory]:
        """PRD §FR-4: get memories for bootstrap constant injection.

        Returns up to max_count memories:
        - fact + user_confirmed + P0 (top 3 by access_count)
        - judgment + user_confirmed + P0 + sub_type=preference (top 2)
        Excludes needs_review and archived.
        """
        results: list[Memory] = []

        # Top 3 facts
        cur = self._conn.execute(
            """SELECT * FROM memories
               WHERE layer='fact' AND verification='user_confirmed' AND priority='P0'
                     AND needs_review=0 AND archived_at IS NULL
               ORDER BY access_count DESC LIMIT 3"""
        )
        for row in cur.fetchall():
            results.append(_row_to_memory(row))

        # Top 2 preferences
        remaining = max_count - len(results)
        if remaining > 0:
            cur = self._conn.execute(
                """SELECT * FROM memories
                   WHERE layer='judgment' AND verification='user_confirmed' AND priority='P0'
                         AND sub_type='preference' AND needs_review=0 AND archived_at IS NULL
                   ORDER BY access_count DESC LIMIT ?""",
                (remaining,),
            )
            for row in cur.fetchall():
                results.append(_row_to_memory(row))

        return results

    # ── Internal helpers ─────────────────────────────────────────

    def _write_event(self, memory_id: str, event_type: str, payload: dict) -> None:
        now = _utcnow_iso()
        self._conn.execute(
            "INSERT INTO memory_events (memory_id, event_type, payload, created_at) VALUES (?,?,?,?)",
            (memory_id, event_type, json.dumps(payload, ensure_ascii=False), now),
        )

    def _check_needs_review(self, memory_id: str) -> None:
        cur = self._conn.execute(
            "SELECT conflict_count FROM memories WHERE id=?", (memory_id,)
        )
        row = cur.fetchone()
        if row and row["conflict_count"] > 3:
            self._conn.execute(
                "UPDATE memories SET needs_review=1 WHERE id=?",
                (memory_id,),
            )
