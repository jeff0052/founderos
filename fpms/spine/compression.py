"""Narrative compression: rule-based, v1 no LLM."""

from __future__ import annotations

import os
import re
from typing import List, Tuple

from spine.narrative import read_compressed, write_compressed


# ── Event type classification ───────────────────────────────────

_STATUS_KEYWORDS = re.compile(
    r"→|status|active|done|dropped|waiting|inbox", re.IGNORECASE
)
_DECISION_KEYWORDS = re.compile(
    r"决定|决策|decision|decided", re.IGNORECASE
)
_BLOCKER_KEYWORDS = re.compile(
    r"blocked|阻塞|卡在", re.IGNORECASE
)
_CORRECTION_KEYWORDS = re.compile(
    r"纠正|修正|correction|误", re.IGNORECASE
)

# Ordered: first match wins (more specific before less specific)
_CLASSIFIERS = [
    ("blocker", _BLOCKER_KEYWORDS),
    ("correction", _CORRECTION_KEYWORDS),
    ("decision", _DECISION_KEYWORDS),
    ("status_change", _STATUS_KEYWORDS),
]


def _classify_entry(header: str, body: str) -> str:
    """Classify a narrative entry by event type.

    Checks the explicit [event_type] tag first, then falls back to
    keyword matching on the full text (header + body).
    """
    # Check explicit tag in header: ## timestamp [event_type]
    tag_match = re.search(r'\[(\w+)\]', header)
    if tag_match:
        tag = tag_match.group(1).lower()
        if tag in ("status_change",):
            return "status_change"
        if tag in ("decision",):
            return "decision"
        if tag in ("blocker",):
            return "blocker"
        if tag in ("correction",):
            return "correction"

    # Keyword matching on full text
    full_text = header + "\n" + body
    for event_type, pattern in _CLASSIFIERS:
        if pattern.search(full_text):
            return event_type

    return "info"


# ── Parsing ─────────────────────────────────────────────────────

def _parse_entries(text: str) -> List[Tuple[str, str]]:
    """Parse narrative text into list of (header, body) tuples.

    Each entry starts with '## YYYY-...' header line.
    """
    parts = re.split(r'(?=^## )', text, flags=re.MULTILINE)
    entries = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        header = lines[0]
        body = lines[1].strip() if len(lines) > 1 else ""
        entries.append((header, body))
    return entries


def _estimate_tokens(text: str) -> int:
    """Estimate token count: len(text) // 2."""
    return len(text) // 2


# ── Info merging ────────────────────────────────────────────────

_INFO_MERGE_GROUP_SIZE = 3


def _merge_info_group(entries: List[Tuple[str, str]]) -> str:
    """Merge a group of consecutive info entries into a single summary line."""
    if len(entries) == 1:
        header, body = entries[0]
        return "{}\n{}\n".format(header, body)
    # Summarize: keep first timestamp, combine bodies
    first_header = entries[0][0]
    last_header = entries[-1][0]
    # Extract timestamps for range
    first_ts = re.match(r'^## (\S+)', first_header)
    last_ts = re.match(r'^## (\S+)', last_header)
    ts_range = ""
    if first_ts and last_ts:
        ts_range = "{}..{}".format(first_ts.group(1), last_ts.group(1))
    else:
        ts_range = first_header.replace("## ", "")

    bodies = [e[1] for e in entries if e[1]]
    # Take first line of each body for brevity
    summaries = []
    for b in bodies:
        first_line = b.split("\n")[0].strip()
        if first_line:
            summaries.append(first_line)

    return "## {} [info-merged]\n{} info entries: {}\n".format(
        ts_range, len(entries), "; ".join(summaries)
    )


# ── Core functions ──────────────────────────────────────────────


def should_compress(narratives_dir: str, node_id: str,
                     threshold_tokens: int = 2000) -> bool:
    """判断是否需要压缩。条件: token 数 > threshold_tokens。"""
    path = os.path.join(narratives_dir, "{}.md".format(node_id))
    if not os.path.exists(path):
        return False
    with open(path, "r") as f:
        text = f.read()
    if not text.strip():
        return False
    return _estimate_tokens(text) > threshold_tokens


def compress_narrative(narratives_dir: str, node_id: str,
                        max_output_tokens: int = 500) -> str:
    """规则压缩叙事。v1 不用 LLM。

    1. 读取 {node_id}.md
    2. 解析条目，分类事件类型
    3. 保留所有非 info 条目
    4. 连续 info 条目合并
    5. 超 max_output_tokens 则截断最旧 info
    6. 写入 .compressed.md
    """
    path = os.path.join(narratives_dir, "{}.md".format(node_id))
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        text = f.read()
    if not text.strip():
        return ""

    entries = _parse_entries(text)
    if not entries:
        return ""

    # Classify each entry
    classified: List[Tuple[str, Tuple[str, str]]] = []
    for header, body in entries:
        event_type = _classify_entry(header, body)
        classified.append((event_type, (header, body)))

    # Build output: preserve non-info, merge consecutive info groups
    output_parts: List[Tuple[str, str]] = []  # (type, text)
    info_group: List[Tuple[str, str]] = []

    def flush_info():
        nonlocal info_group
        if not info_group:
            return
        for i in range(0, len(info_group), _INFO_MERGE_GROUP_SIZE):
            chunk = info_group[i:i + _INFO_MERGE_GROUP_SIZE]
            output_parts.append(("info", _merge_info_group(chunk)))
        info_group = []

    for event_type, (header, body) in classified:
        if event_type == "info":
            info_group.append((header, body))
        else:
            flush_info()
            output_parts.append((event_type, "{}\n{}\n".format(header, body)))
    flush_info()

    # Join all parts
    result = "\n".join(text for _, text in output_parts)

    # Truncate if over budget: remove oldest info entries first
    while _estimate_tokens(result) > max_output_tokens and output_parts:
        # Find oldest info entry
        removed = False
        for i, (etype, _) in enumerate(output_parts):
            if etype == "info":
                output_parts.pop(i)
                result = "\n".join(text for _, text in output_parts)
                removed = True
                break
        if not removed:
            # All non-info — truncate from the beginning
            output_parts.pop(0)
            result = "\n".join(text for _, text in output_parts)

    # Write compressed output
    if result.strip():
        write_compressed(narratives_dir, node_id, result)

    return result
