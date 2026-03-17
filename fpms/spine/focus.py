"""Focus scheduler: arbitration, LRU eviction, decay."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .store import Store

MAX_FOCUS_SLOTS = 3
DECAY_DAYS = 3


@dataclass
class FocusResult:
    primary: Optional[str] = None
    secondaries: list[str] = field(default_factory=list)
    reason: str = ""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _node_exists(store: "Store", node_id: str) -> bool:
    return store.get_node(node_id) is not None


def _load_focus_state(session: dict) -> tuple[Optional[str], list[str], dict[str, str]]:
    """Extract focus state from session_state dict."""
    primary = session.get("focus_primary")
    raw_sec = session.get("focus_secondaries")
    secondaries = json.loads(raw_sec) if isinstance(raw_sec, str) else (raw_sec or [])
    raw_touched = session.get("focus_touched_at")
    touched_at = json.loads(raw_touched) if isinstance(raw_touched, str) else (raw_touched or {})
    return primary, secondaries, touched_at


def _apply_decay(candidates: list[str], touched_at: dict[str, str], now: datetime) -> list[str]:
    """Remove candidates whose touched_at is older than DECAY_DAYS."""
    cutoff = now - timedelta(days=DECAY_DAYS)
    result = []
    for nid in candidates:
        ts_str = touched_at.get(nid)
        if ts_str is None:
            continue  # no touch record → decayed
        if _parse_iso(ts_str) >= cutoff:
            result.append(nid)
    return result


def _apply_lru(candidates: list[str], touched_at: dict[str, str]) -> list[str]:
    """Keep only MAX_FOCUS_SLOTS candidates, evicting least-recently-touched."""
    if len(candidates) <= MAX_FOCUS_SLOTS:
        return candidates

    def sort_key(nid: str) -> str:
        return touched_at.get(nid, "")

    # Sort by touched_at descending (most recent first), keep top N
    ranked = sorted(candidates, key=sort_key, reverse=True)
    return ranked[:MAX_FOCUS_SLOTS]


def _save_focus(store: "Store", result: FocusResult, touched_at: dict[str, str]) -> None:
    """Persist focus state into session_state."""
    store.set_session("focus_primary", {"v": result.primary})
    store.set_session("focus_secondaries", {"v": result.secondaries})
    store.set_session("focus_touched_at", {"v": touched_at})


def _read_session_focus(store: "Store") -> tuple[Optional[str], list[str], dict[str, str]]:
    """Read focus state from store's session_state."""
    raw_p = store.get_session("focus_primary")
    primary = raw_p["v"] if raw_p else None
    raw_s = store.get_session("focus_secondaries")
    secondaries = raw_s["v"] if raw_s else []
    raw_t = store.get_session("focus_touched_at")
    touched_at = raw_t["v"] if raw_t else {}
    return primary, secondaries, touched_at


def arbitrate(store: "Store", session_state: dict,
              user_request: Optional[str] = None,
              alert_candidates: Optional[list[str]] = None) -> FocusResult:
    """焦点仲裁。优先级: user > alert > time > historical。"""
    now = _utcnow()
    now_iso = now.isoformat()

    # Load historical focus from session_state
    hist_primary, hist_secondaries, touched_at = _load_focus_state(session_state)

    # --- Priority 1: user_request ---
    if user_request and _node_exists(store, user_request):
        touched_at[user_request] = now_iso
        # Build candidate list: new primary + old slots
        all_candidates = [user_request]
        # Demote old primary to secondary if different
        if hist_primary and hist_primary != user_request and _node_exists(store, hist_primary):
            all_candidates.append(hist_primary)
        for s in hist_secondaries:
            if s != user_request and s not in all_candidates and _node_exists(store, s):
                all_candidates.append(s)

        all_candidates = _apply_decay(all_candidates, touched_at, now)
        all_candidates = _apply_lru(all_candidates, touched_at)

        # First is primary, rest are secondaries
        primary = all_candidates[0] if all_candidates else None
        secondaries = all_candidates[1:] if len(all_candidates) > 1 else []
        result = FocusResult(primary=primary, secondaries=secondaries,
                             reason=f"user_request: {user_request}")
        _save_focus(store, result, touched_at)
        return result

    # --- Priority 2: alert_candidates ---
    if alert_candidates:
        valid_alerts = [a for a in alert_candidates if _node_exists(store, a)]
        if valid_alerts:
            for a in valid_alerts:
                touched_at[a] = now_iso
            # Merge with historical
            all_candidates = list(valid_alerts)
            if hist_primary and hist_primary not in all_candidates and _node_exists(store, hist_primary):
                all_candidates.append(hist_primary)
            for s in hist_secondaries:
                if s not in all_candidates and _node_exists(store, s):
                    all_candidates.append(s)

            all_candidates = _apply_decay(all_candidates, touched_at, now)
            all_candidates = _apply_lru(all_candidates, touched_at)

            primary = all_candidates[0] if all_candidates else None
            secondaries = all_candidates[1:] if len(all_candidates) > 1 else []
            result = FocusResult(primary=primary, secondaries=secondaries,
                                 reason=f"alert: {valid_alerts[0]}")
            _save_focus(store, result, touched_at)
            return result

    # --- Priority 3: time-driven (nearest deadline) ---
    active_nodes = store.list_nodes(
        filters={"status": "active", "archived": False},
        order_by="deadline",
        limit=50,
    )
    deadline_nodes = [n for n in active_nodes if n.deadline]
    if deadline_nodes:
        # Sort by deadline ascending (nearest first)
        deadline_nodes.sort(key=lambda n: n.deadline)  # type: ignore
        primary_node = deadline_nodes[0]
        touched_at[primary_node.id] = now_iso
        all_candidates = [primary_node.id]
        # Add historical as fillers
        if hist_primary and hist_primary != primary_node.id and _node_exists(store, hist_primary):
            all_candidates.append(hist_primary)
        for s in hist_secondaries:
            if s not in all_candidates and _node_exists(store, s):
                all_candidates.append(s)

        all_candidates = _apply_decay(all_candidates, touched_at, now)
        all_candidates = _apply_lru(all_candidates, touched_at)

        primary = all_candidates[0] if all_candidates else None
        secondaries = all_candidates[1:] if len(all_candidates) > 1 else []
        result = FocusResult(primary=primary, secondaries=secondaries,
                             reason=f"deadline: {primary_node.deadline}")
        _save_focus(store, result, touched_at)
        return result

    # --- Priority 4: historical focus ---
    if hist_primary or hist_secondaries:
        all_candidates = []
        if hist_primary and _node_exists(store, hist_primary):
            all_candidates.append(hist_primary)
        for s in hist_secondaries:
            if s not in all_candidates and _node_exists(store, s):
                all_candidates.append(s)

        all_candidates = _apply_decay(all_candidates, touched_at, now)
        all_candidates = _apply_lru(all_candidates, touched_at)

        primary = all_candidates[0] if all_candidates else None
        secondaries = all_candidates[1:] if len(all_candidates) > 1 else []
        result = FocusResult(primary=primary, secondaries=secondaries,
                             reason="historical")
        _save_focus(store, result, touched_at)
        return result

    # --- No focus available ---
    return FocusResult(primary=None, secondaries=[], reason="no_candidates")


def shift_focus(store: "Store", node_id: str) -> FocusResult:
    """用户主动切换焦点。最高优先级。"""
    if not _node_exists(store, node_id):
        raise ValueError(f"Node not found: {node_id}. Use get_node to verify the id.")

    now_iso = _utcnow().isoformat()

    # Read current focus from persisted session_state
    old_primary, old_secondaries, touched_at = _read_session_focus(store)

    touched_at[node_id] = now_iso

    if old_primary == node_id:
        # Already primary — just update touched_at
        result = FocusResult(
            primary=node_id,
            secondaries=old_secondaries,
            reason=f"shift_focus: {node_id} (already primary)",
        )
        _save_focus(store, result, touched_at)
        return result

    # Build new candidate list: new primary first
    all_candidates = [node_id]
    if old_primary and old_primary != node_id and _node_exists(store, old_primary):
        all_candidates.append(old_primary)
    for s in old_secondaries:
        if s != node_id and s not in all_candidates and _node_exists(store, s):
            all_candidates.append(s)

    # LRU eviction
    all_candidates = _apply_lru(all_candidates, touched_at)

    primary = all_candidates[0]
    secondaries = all_candidates[1:]

    result = FocusResult(primary=primary, secondaries=secondaries,
                         reason=f"shift_focus: {node_id}")
    _save_focus(store, result, touched_at)
    return result
