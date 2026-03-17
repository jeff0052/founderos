"""Heartbeat scan: alert generation, dedup, Anti-Amnesia."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from .models import Alert
from .risk import batch_compute_risks, RiskMarks, _parse_iso, AT_RISK_THRESHOLD

if TYPE_CHECKING:
    from .store import Store

_MAX_ALERTS = 3
_ANTI_AMNESIA_THRESHOLD = timedelta(hours=24)
_URGENT_DEADLINE_THRESHOLD = timedelta(hours=24)


@dataclass
class HeartbeatResult:
    alerts: list[Alert] = field(default_factory=list)
    focus_candidates: list[str] = field(default_factory=list)
    suppressed_count: int = 0


def _classify_alert(
    node_id: str,
    marks: RiskMarks,
    node: "Node",
    store: "Store",
) -> Alert | None:
    """Map risk marks to the highest-priority alert for this node.

    Returns only the single highest-priority alert per node.
    Priority: urgent_deadline(1) > critical_blocked(2) > deadline_warning(3)
              > stale_warning(4) > inbox_cleanup(5)
    """
    from .models import Node  # avoid circular

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # Priority 1: at-risk + deadline < 24h
    if marks.at_risk and node.deadline:
        deadline_dt = _parse_iso(node.deadline)
        if deadline_dt < now + _URGENT_DEADLINE_THRESHOLD:
            return Alert(
                node_id=node_id,
                alert_type="urgent_deadline",
                message=f"Deadline in <24h: {node.title}",
                severity=1,
                first_seen=now_iso,
            )

    # Priority 2: blocked + at least one active dependent
    if marks.blocked:
        dependents = store.get_dependents(node_id)
        active_dependents = [d for d in dependents
                             if d.status not in ("done", "dropped")]
        if active_dependents:
            return Alert(
                node_id=node_id,
                alert_type="critical_blocked",
                message=f"Blocked node depended on by {len(active_dependents)} active node(s): {node.title}",
                severity=2,
                first_seen=now_iso,
            )

    # Priority 3: at-risk (48h window, but >24h since priority 1 already caught <24h)
    if marks.at_risk:
        return Alert(
            node_id=node_id,
            alert_type="deadline_warning",
            message=f"Deadline within 48h: {node.title}",
            severity=3,
            first_seen=now_iso,
        )

    # Priority 4: stale (active/waiting)
    if marks.stale and node.status in ("active", "waiting"):
        return Alert(
            node_id=node_id,
            alert_type="stale_warning",
            message=f"Stale node (>7d no status change): {node.title}",
            severity=4,
            first_seen=now_iso,
        )

    # Priority 5: inbox + stale (created_at > 7d)
    if marks.stale and node.status == "inbox":
        return Alert(
            node_id=node_id,
            alert_type="inbox_cleanup",
            message=f"Inbox item stale (>7d): {node.title}",
            severity=5,
            first_seen=now_iso,
        )

    return None


def _dedup_key(alert: Alert) -> str:
    return f"{alert.alert_type}_{alert.node_id}"


def _should_suppress(
    alert: Alert,
    last_alerts: dict,
    node_status_changed_at: str,
) -> bool:
    """Check if this alert should be suppressed by dedup logic.

    Returns True if alert should be suppressed (not pushed).
    """
    key = _dedup_key(alert)
    prev = last_alerts.get(key)
    if prev is None:
        return False

    prev_status_changed = prev.get("status_changed_at", "")
    # If node status changed since last push → re-push
    if node_status_changed_at != prev_status_changed:
        return False

    # Anti-Amnesia: high severity (<=2) pushed >24h ago + no substantive action → re-push
    if alert.severity <= 2:
        pushed_at = prev.get("pushed_at", "")
        if pushed_at:
            pushed_dt = _parse_iso(pushed_at)
            now = datetime.now(timezone.utc)
            if now - pushed_dt > _ANTI_AMNESIA_THRESHOLD:
                # Check if status_changed_at is after pushed_at
                sc_dt = _parse_iso(node_status_changed_at)
                if sc_dt <= pushed_dt:
                    # No substantive action → re-push (anti-amnesia)
                    return False

    # Same alert, no status change, not anti-amnesia → suppress
    return True


def scan(store: "Store", session_state: dict) -> HeartbeatResult:
    """执行心跳扫描。复用 risk 计算，去重，Anti-Amnesia。"""
    risks = batch_compute_risks(store)

    # Generate candidate alerts
    candidates: list[Alert] = []
    for node_id, marks in risks.items():
        node = store.get_node(node_id)
        if node is None:
            continue
        alert = _classify_alert(node_id, marks, node, store)
        if alert is not None:
            candidates.append(alert)

    # Sort by severity (ascending = highest priority first)
    candidates.sort(key=lambda a: a.severity)

    # Dedup
    last_alerts = session_state.get("last_alerts", {})
    pushed: list[Alert] = []
    suppressed = 0

    for alert in candidates:
        node = store.get_node(alert.node_id)
        sc_at = node.status_changed_at if node else ""

        if _should_suppress(alert, last_alerts, sc_at):
            suppressed += 1
            continue

        if len(pushed) < _MAX_ALERTS:
            pushed.append(alert)
        else:
            suppressed += 1

    # Update session_state with pushed alerts
    new_last_alerts = dict(last_alerts)
    now_iso = datetime.now(timezone.utc).isoformat()
    for alert in pushed:
        node = store.get_node(alert.node_id)
        sc_at = node.status_changed_at if node else ""
        key = _dedup_key(alert)
        new_last_alerts[key] = {
            "pushed_at": now_iso,
            "status_changed_at": sc_at,
            "severity": alert.severity,
        }
    session_state["last_alerts"] = new_last_alerts

    # Focus candidates: all severity<=2 alerts (from all candidates, not just top 3)
    focus = []
    seen_focus = set()
    for alert in candidates:
        if alert.severity <= 2 and alert.node_id not in seen_focus:
            focus.append(alert.node_id)
            seen_focus.add(alert.node_id)

    return HeartbeatResult(
        alerts=pushed,
        focus_candidates=focus,
        suppressed_count=suppressed,
    )
