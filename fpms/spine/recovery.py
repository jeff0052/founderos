"""Cold start / bootstrap flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import bundle
from . import dashboard
from . import focus as focus_mod
from . import heartbeat
from .focus import FocusResult
from .models import Alert, ContextBundle

if TYPE_CHECKING:
    from .store import Store


def _render_alerts_md(alerts: list[Alert]) -> str:
    """将告警列表渲染为 markdown。"""
    if not alerts:
        return ""
    lines = ["## ⚠️ 系统告警"]
    for a in alerts:
        lines.append(f"🔴 [{a.node_id}]: {a.alert_type} - {a.message}")
    return "\n".join(lines)


def bootstrap(store: "Store", narratives_dir: str,
              max_tokens: int = 10000) -> ContextBundle:
    """冷启动全流程。局部降级不阻断。"""

    # Step 1: store 已传入

    # Step 2: L0 全局看板 (降级: 看板损坏 → 空字符串)
    try:
        dashboard_md = dashboard.render_dashboard(store)
    except Exception:
        dashboard_md = ""

    # Step 3: Heartbeat 扫描 (降级: 失败 → 空告警)
    session_state: dict = {}
    raw = store.get_session("heartbeat")
    if raw is not None:
        session_state = raw
    try:
        hb_result = heartbeat.scan(store, session_state)
        alerts_md = _render_alerts_md(hb_result.alerts)
        focus_candidates = hb_result.focus_candidates
    except Exception:
        hb_result = None
        alerts_md = ""
        focus_candidates = []

    # 持久化 heartbeat session_state
    try:
        store.set_session("heartbeat", session_state)
    except Exception:
        pass

    # Step 4: 焦点仲裁 (降级: 失败 → 无焦点模式)
    focus_session: dict = {}
    for key in ("focus_primary", "focus_secondaries", "focus_touched_at"):
        raw = store.get_session(key)
        if raw is not None:
            focus_session[key] = raw.get("v") if isinstance(raw, dict) else raw
    try:
        focus_result = focus_mod.arbitrate(
            store, focus_session, alert_candidates=focus_candidates,
        )
    except Exception:
        focus_result = FocusResult()

    # Step 5: 组装认知包 (降级: 失败 → 最小 bundle)
    try:
        ctx = bundle.assemble(
            store, focus_result, dashboard_md, alerts_md, max_tokens,
        )
    except Exception:
        ctx = ContextBundle(
            l0_dashboard=dashboard_md,
            l_alert=alerts_md,
            l1_neighborhood="",
            l2_focus="",
            total_tokens=0,
            focus_node_id=focus_result.primary,
        )

    return ctx
