#!/usr/bin/env python3
"""FPMS Spine CLI — Agent 通过 exec 调用的唯一入口。

Usage:
    python3 spine.py tool <tool_name> <json_args> [--command-id <id>]
    python3 spine.py bootstrap [--max-tokens <n>]
    python3 spine.py heartbeat
    python3 spine.py dashboard
    python3 spine.py status
"""

from __future__ import annotations

import json
import os
import sys
import uuid

# Add parent dir to path so spine/ package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spine.schema import init_db
from spine.store import Store
from spine.command_executor import CommandExecutor


# ── Paths ──

FPMS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FPMS_DIR, "db", "fpms.db")
EVENTS_PATH = os.path.join(FPMS_DIR, "events.jsonl")
NARRATIVES_DIR = os.path.join(FPMS_DIR, "narratives")


def _ensure_dirs():
    os.makedirs(os.path.join(FPMS_DIR, "db"), exist_ok=True)
    os.makedirs(NARRATIVES_DIR, exist_ok=True)


def _get_store() -> Store:
    _ensure_dirs()
    init_db(DB_PATH)
    return Store(db_path=DB_PATH, events_path=EVENTS_PATH)


def _get_executor() -> tuple[Store, CommandExecutor]:
    store = _get_store()
    executor = CommandExecutor(store, narratives_dir=NARRATIVES_DIR)
    return store, executor


# ── Commands ──

def cmd_tool(args: list[str]):
    """Execute a Tool Call."""
    if len(args) < 2:
        print(json.dumps({"success": False, "error": "Usage: spine.py tool <name> <json_args> [--command-id <id>]"}))
        sys.exit(1)

    tool_name = args[0]
    try:
        tool_args = json.loads(args[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON args: {e}"}))
        sys.exit(1)

    # Parse optional --command-id
    command_id = None
    for i, a in enumerate(args[2:], 2):
        if a == "--command-id" and i + 1 < len(args):
            command_id = args[i + 1]
            break
    if command_id is None:
        command_id = f"cmd-{uuid.uuid4().hex[:8]}"

    store, executor = _get_executor()
    result = executor.execute(command_id, tool_name, tool_args)

    # Flush events after write (memory tools handle own commits)
    _NO_FLUSH = {"get_node", "search_nodes", "shift_focus", "expand_context",
                 "memory_add", "memory_search", "memory_update",
                 "memory_forget", "memory_promote", "memory_confirm"}
    if result.success and tool_name not in _NO_FLUSH:
        try:
            store.flush_events()
        except Exception:
            pass

    output = {
        "success": result.success,
        "command_id": result.command_id,
    }
    if result.data is not None:
        output["data"] = result.data
    if result.error is not None:
        output["error"] = result.error
    if result.suggestion is not None:
        output["suggestion"] = result.suggestion
    if result.affected_nodes:
        output["affected_nodes"] = result.affected_nodes
    if result.warnings:
        output["warnings"] = result.warnings

    print(json.dumps(output, ensure_ascii=False, default=str))


def cmd_bootstrap(args: list[str]):
    """Cold start — generate and print Context Bundle."""
    max_tokens = 10000
    for i, a in enumerate(args):
        if a == "--max-tokens" and i + 1 < len(args):
            max_tokens = int(args[i + 1])

    store = _get_store()

    from spine.recovery import bootstrap
    bundle = bootstrap(store, NARRATIVES_DIR, max_tokens=max_tokens)

    # Print as structured sections
    sections = []
    if bundle.l0_dashboard:
        sections.append(f"## 📊 全局看板\n\n{bundle.l0_dashboard}")
    if bundle.l_alert:
        sections.append(f"\n{bundle.l_alert}")
    if bundle.l1_neighborhood:
        sections.append(f"## 🔍 近景关联\n\n{bundle.l1_neighborhood}")
    if bundle.l2_focus:
        sections.append(f"## 🎯 焦点工作区\n\n{bundle.l2_focus}")

    if sections:
        print("\n".join(sections))
    else:
        print("(FPMS: 系统为空，暂无项目数据)")

    # Print metadata as JSON comment
    meta = {
        "focus_node_id": bundle.focus_node_id,
        "total_tokens": bundle.total_tokens,
    }
    print(f"\n<!-- fpms_meta: {json.dumps(meta)} -->")


def cmd_heartbeat(args: list[str]):
    """Heartbeat scan — print alerts if any."""
    store = _get_store()

    from spine.heartbeat import scan
    session_state = store.get_session("heartbeat") or {}
    result = scan(store, session_state)

    # Persist heartbeat state
    try:
        store.set_session("heartbeat", session_state)
    except Exception:
        pass

    if not result.alerts:
        print("FPMS_HEARTBEAT_OK")
        return

    lines = []
    severity_icons = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟡", 5: "🔵"}
    for alert in result.alerts:
        icon = severity_icons.get(alert.severity, "⚪")
        lines.append(f"{icon} [{alert.node_id}] {alert.alert_type}: {alert.message}")

    if result.suppressed_count > 0:
        lines.append(f"  (+{result.suppressed_count} 条已压制)")

    print("\n".join(lines))


def cmd_dashboard(args: list[str]):
    """Print L0 dashboard."""
    store = _get_store()

    from spine.dashboard import render_dashboard
    max_tokens = 1000
    for i, a in enumerate(args):
        if a == "--max-tokens" and i + 1 < len(args):
            max_tokens = int(args[i + 1])

    md = render_dashboard(store, max_tokens=max_tokens)
    print(md if md else "(空)")


def cmd_status(args: list[str]):
    """Print system status summary."""
    store = _get_store()

    nodes = store.list_nodes()
    by_status = {}
    for n in nodes:
        by_status.setdefault(n.status, 0)
        by_status[n.status] += 1

    archived = len([n for n in nodes if n.archived_at])
    active_total = len(nodes) - archived

    from spine.risk import batch_compute_risks
    risks = batch_compute_risks(store)
    blocked = sum(1 for r in risks.values() if r.blocked)
    at_risk = sum(1 for r in risks.values() if r.at_risk)
    stale = sum(1 for r in risks.values() if r.stale)

    print(f"FPMS Status")
    print(f"  Nodes: {len(nodes)} total ({active_total} active, {archived} archived)")
    for status, count in sorted(by_status.items()):
        print(f"    {status}: {count}")
    print(f"  Risks: {blocked} blocked, {at_risk} at-risk, {stale} stale")
    print(f"  DB: {DB_PATH}")


# ── Main ──

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "tool": cmd_tool,
        "bootstrap": cmd_bootstrap,
        "heartbeat": cmd_heartbeat,
        "dashboard": cmd_dashboard,
        "status": cmd_status,
    }

    if cmd in commands:
        commands[cmd](args)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
