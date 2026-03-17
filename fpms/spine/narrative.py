"""Narrative file management: append-only markdown read/write/repair."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional


def append_narrative(narratives_dir: str, node_id: str,
                      timestamp: str, event_type: str,
                      content: str, mentions: Optional[list] = None) -> bool:
    """追加一条叙事到 narratives/{node_id}.md。
    格式: ## {timestamp} [{event_type}]\n{content}
    返回是否写入成功。失败时不抛异常，返回 False。"""
    try:
        os.makedirs(narratives_dir, exist_ok=True)
        path = os.path.join(narratives_dir, "{}.md".format(node_id))
        lines = "## {} [{}]\n{}\n".format(timestamp, event_type, content)
        if mentions:
            lines += "Mentions: {}\n".format(", ".join(mentions))
        lines += "\n"
        with open(path, "a") as f:
            f.write(lines)
        return True
    except Exception:
        return False


def read_narrative(narratives_dir: str, node_id: str,
                    last_n_entries: Optional[int] = None,
                    since_days: Optional[int] = None) -> str:
    """读取叙事内容。支持按条数或天数截取。"""
    path = os.path.join(narratives_dir, "{}.md".format(node_id))
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        text = f.read()
    if not text.strip():
        return ""

    # Split into entries by ## headers
    entries = re.split(r'(?=^## )', text, flags=re.MULTILINE)
    entries = [e for e in entries if e.strip()]

    if last_n_entries is not None:
        entries = entries[-last_n_entries:]

    if since_days is not None:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=since_days)
        filtered = []
        for entry in entries:
            # Extract timestamp from ## {timestamp} [{event_type}]
            m = re.match(r'^## (\S+)', entry)
            if m:
                ts_str = m.group(1)
                try:
                    ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        filtered.append(entry)
                except ValueError:
                    filtered.append(entry)
            else:
                filtered.append(entry)
        entries = filtered

    return "".join(entries)


def read_compressed(narratives_dir: str, node_id: str) -> Optional[str]:
    """读取压缩摘要 {node_id}.compressed.md。不存在返回 None。"""
    path = os.path.join(narratives_dir, "{}.compressed.md".format(node_id))
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read()


def write_compressed(narratives_dir: str, node_id: str, content: str) -> None:
    """写入压缩摘要。"""
    os.makedirs(narratives_dir, exist_ok=True)
    path = os.path.join(narratives_dir, "{}.compressed.md".format(node_id))
    with open(path, "w") as f:
        f.write(content)


def write_repair_event(narratives_dir: str, node_id: str,
                        original_event: dict, error: str) -> None:
    """写入修复事件记录。当 narrative 写入失败时调用。"""
    os.makedirs(narratives_dir, exist_ok=True)
    path = os.path.join(narratives_dir, "{}.md".format(node_id))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = "## {} [repair]\nOriginal event: {}\nError: {}\n\n".format(
        now, json.dumps(original_event), error
    )
    with open(path, "a") as f:
        f.write(entry)
