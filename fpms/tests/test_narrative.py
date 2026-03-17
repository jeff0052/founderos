"""Tests for narrative.py — append-only narrative storage."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from fpms.narrative import (
    append_narrative,
    read_compressed,
    read_narrative,
    write_compressed,
    write_repair_event,
)


@pytest.fixture
def narr_dir(tmp_path):
    """Provide a temporary narratives directory."""
    d = tmp_path / "narratives"
    d.mkdir()
    return str(d)


# ── append_narrative ─────────────────────────────────────────────


class TestAppendNarrative:
    def test_creates_file_and_returns_true(self, narr_dir):
        result = append_narrative(
            narr_dir, "task-abc1", "2026-03-17T10:00:00Z", "created", "Node created"
        )
        assert result is True
        path = os.path.join(narr_dir, "task-abc1.md")
        assert os.path.exists(path)

    def test_format_correct(self, narr_dir):
        append_narrative(
            narr_dir, "task-abc1", "2026-03-17T10:00:00Z", "created", "Node created"
        )
        path = os.path.join(narr_dir, "task-abc1.md")
        with open(path, "r") as f:
            text = f.read()
        assert "## 2026-03-17T10:00:00Z [created]" in text
        assert "Node created" in text

    def test_append_only_multiple_writes(self, narr_dir):
        """Multiple appends must not overwrite earlier content."""
        append_narrative(
            narr_dir, "task-abc1", "2026-03-17T10:00:00Z", "created", "First entry"
        )
        append_narrative(
            narr_dir, "task-abc1", "2026-03-17T11:00:00Z", "updated", "Second entry"
        )
        path = os.path.join(narr_dir, "task-abc1.md")
        with open(path, "r") as f:
            text = f.read()
        assert "First entry" in text
        assert "Second entry" in text
        # First entry must appear before second entry
        assert text.index("First entry") < text.index("Second entry")

    def test_with_mentions(self, narr_dir):
        append_narrative(
            narr_dir,
            "task-abc1",
            "2026-03-17T10:00:00Z",
            "linked",
            "Depends on goal-xyz",
            mentions=["goal-xyz9", "mile-1234"],
        )
        path = os.path.join(narr_dir, "task-abc1.md")
        with open(path, "r") as f:
            text = f.read()
        assert "goal-xyz9" in text
        assert "mile-1234" in text

    def test_auto_creates_directory_and_file(self, tmp_path):
        """When narratives_dir doesn't exist yet, it should be created."""
        deep_dir = str(tmp_path / "nested" / "narratives")
        result = append_narrative(
            deep_dir, "task-new1", "2026-03-17T10:00:00Z", "created", "Auto-created"
        )
        assert result is True
        assert os.path.exists(os.path.join(deep_dir, "task-new1.md"))

    def test_returns_false_on_failure(self, narr_dir):
        """Simulate a failure scenario — writing to an invalid path should return False."""
        # Use a path that cannot be created (file as directory component)
        blocker = os.path.join(narr_dir, "blocker")
        with open(blocker, "w") as f:
            f.write("I am a file")
        # Try to use the file as a directory
        bad_dir = os.path.join(blocker, "subdir")
        result = append_narrative(
            bad_dir, "task-fail", "2026-03-17T10:00:00Z", "created", "Should fail"
        )
        assert result is False

    def test_returns_true_on_success(self, narr_dir):
        result = append_narrative(
            narr_dir, "task-ok01", "2026-03-17T10:00:00Z", "created", "OK"
        )
        assert result is True


# ── read_narrative ───────────────────────────────────────────────


class TestReadNarrative:
    def _append_entries(self, narr_dir, node_id, entries):
        """Helper to append multiple entries."""
        for ts, etype, content in entries:
            append_narrative(narr_dir, node_id, ts, etype, content)

    def test_full_read(self, narr_dir):
        self._append_entries(
            narr_dir,
            "task-read",
            [
                ("2026-03-17T10:00:00Z", "created", "Entry one"),
                ("2026-03-17T11:00:00Z", "updated", "Entry two"),
                ("2026-03-17T12:00:00Z", "status", "Entry three"),
            ],
        )
        text = read_narrative(narr_dir, "task-read")
        assert "Entry one" in text
        assert "Entry two" in text
        assert "Entry three" in text

    def test_last_n_entries(self, narr_dir):
        self._append_entries(
            narr_dir,
            "task-lasn",
            [
                ("2026-03-17T10:00:00Z", "created", "Entry one"),
                ("2026-03-17T11:00:00Z", "updated", "Entry two"),
                ("2026-03-17T12:00:00Z", "status", "Entry three"),
            ],
        )
        text = read_narrative(narr_dir, "task-lasn", last_n_entries=2)
        assert "Entry one" not in text
        assert "Entry two" in text
        assert "Entry three" in text

    def test_since_days(self, narr_dir):
        now = datetime.now(timezone.utc)
        old_ts = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent_ts = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._append_entries(
            narr_dir,
            "task-sinc",
            [
                (old_ts, "created", "Old entry"),
                (recent_ts, "updated", "Recent entry"),
            ],
        )
        text = read_narrative(narr_dir, "task-sinc", since_days=3)
        assert "Old entry" not in text
        assert "Recent entry" in text

    def test_empty_file_returns_empty_string(self, narr_dir):
        """Reading a non-existent narrative should return empty string."""
        text = read_narrative(narr_dir, "task-none")
        assert text == ""

    def test_file_exists_but_empty(self, narr_dir):
        path = os.path.join(narr_dir, "task-empt.md")
        with open(path, "w") as f:
            f.write("")
        text = read_narrative(narr_dir, "task-empt")
        assert text == ""


# ── read_compressed ──────────────────────────────────────────────


class TestReadCompressed:
    def test_returns_content_when_exists(self, narr_dir):
        path = os.path.join(narr_dir, "task-comp.compressed.md")
        with open(path, "w") as f:
            f.write("Compressed summary content")
        result = read_compressed(narr_dir, "task-comp")
        assert result == "Compressed summary content"

    def test_returns_none_when_missing(self, narr_dir):
        result = read_compressed(narr_dir, "task-nope")
        assert result is None


# ── write_compressed ─────────────────────────────────────────────


class TestWriteCompressed:
    def test_writes_content(self, narr_dir):
        write_compressed(narr_dir, "task-wc01", "Summary v1")
        path = os.path.join(narr_dir, "task-wc01.compressed.md")
        with open(path, "r") as f:
            assert f.read() == "Summary v1"

    def test_overwrites_existing(self, narr_dir):
        """Compressed files CAN be overwritten (unlike narratives)."""
        write_compressed(narr_dir, "task-wc02", "Summary v1")
        write_compressed(narr_dir, "task-wc02", "Summary v2")
        path = os.path.join(narr_dir, "task-wc02.compressed.md")
        with open(path, "r") as f:
            content = f.read()
        assert "Summary v2" in content
        # v1 should NOT be present — overwrite, not append
        assert "Summary v1" not in content


# ── write_repair_event ───────────────────────────────────────────


class TestWriteRepairEvent:
    def test_contains_original_event_and_error(self, narr_dir):
        original = {"event_type": "status_change", "node_id": "task-rep1", "new_status": "done"}
        write_repair_event(narr_dir, "task-rep1", original, "MD write failed: disk full")
        path = os.path.join(narr_dir, "task-rep1.md")
        with open(path, "r") as f:
            text = f.read()
        assert "status_change" in text
        assert "disk full" in text

    def test_creates_directory_if_missing(self, tmp_path):
        deep_dir = str(tmp_path / "deep" / "narratives")
        original = {"event_type": "created", "node_id": "task-rep2"}
        write_repair_event(deep_dir, "task-rep2", original, "IO error")
        assert os.path.exists(os.path.join(deep_dir, "task-rep2.md"))
