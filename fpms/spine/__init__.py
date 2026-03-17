"""FPMS Spine Engine — Deterministic project management engine for AI Agents."""

from .models import Node, Edge, ToolResult, Alert, ContextBundle
from .schema import init_db, get_connection
from .store import Store
from .validator import (
    ValidationError,
    validate_status_transition,
    validate_dag_safety,
    validate_xor_constraint,
    validate_active_domain,
    validate_attach,
    validate_dependency,
)
from .narrative import append_narrative, read_narrative, read_compressed, write_compressed, write_repair_event
from .risk import RiskMarks, compute_risks, batch_compute_risks
from .rollup import compute_rollup, batch_compute_rollup
from .dashboard import render_dashboard
from .heartbeat import HeartbeatResult, scan
from .focus import FocusResult, arbitrate, shift_focus
from .bundle import assemble, estimate_tokens
from .archive import scan_archive_candidates, archive_nodes, unarchive_node
from .recovery import bootstrap
from .compression import compress_narrative, should_compress
from .tools import ToolHandler
from .command_executor import CommandExecutor

__version__ = "0.1.0"
