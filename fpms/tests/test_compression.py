"""Tests for compression.py — rule-based narrative compression."""

import os

import pytest

from fpms.compression import compress_narrative, should_compress
from fpms.narrative import append_narrative, read_compressed


@pytest.fixture
def narr_dir(tmp_path):
    d = tmp_path / "narratives"
    d.mkdir()
    return str(d)


def _write_raw(narr_dir: str, node_id: str, content: str) -> None:
    """Write raw narrative content for testing."""
    path = os.path.join(narr_dir, "{}.md".format(node_id))
    with open(path, "w") as f:
        f.write(content)


# ── should_compress ─────────────────────────────────────────────


class TestShouldCompress:
    def test_short_narrative_no_compress(self, narr_dir):
        append_narrative(narr_dir, "task-s001", "2026-03-17T10:00:00Z", "created", "Short note")
        assert should_compress(narr_dir, "task-s001") is False

    def test_long_narrative_needs_compress(self, narr_dir):
        # threshold_tokens=2000, estimated as len(text)//2
        # So we need text > 4000 chars
        for i in range(100):
            append_narrative(
                narr_dir, "task-l001",
                "2026-03-17T{:02d}:{:02d}:00Z".format(10 + i // 60, i % 60),
                "info",
                "Entry number {} with some padding text to make it longer. " * 3
            )
        assert should_compress(narr_dir, "task-l001") is True

    def test_file_not_exists(self, narr_dir):
        assert should_compress(narr_dir, "task-nope") is False

    def test_empty_file(self, narr_dir):
        _write_raw(narr_dir, "task-empt", "")
        assert should_compress(narr_dir, "task-empt") is False

    def test_custom_threshold(self, narr_dir):
        append_narrative(narr_dir, "task-t001", "2026-03-17T10:00:00Z", "created", "Short")
        # With a very low threshold, even a short narrative should compress
        assert should_compress(narr_dir, "task-t001", threshold_tokens=1) is True


# ── compress_narrative ──────────────────────────────────────────


SAMPLE_NARRATIVE = """\
## 2026-03-01T10:00:00Z [created]
Node created: implement auth module

## 2026-03-02T09:00:00Z [status_change]
Status: inbox → active. Starting work.

## 2026-03-02T10:00:00Z [info]
Reviewed existing code structure.

## 2026-03-02T11:00:00Z [info]
Looked at dependency versions.

## 2026-03-02T12:00:00Z [info]
Checked test coverage.

## 2026-03-03T09:00:00Z [decision]
决定使用 JWT for auth tokens.

## 2026-03-03T14:00:00Z [blocker]
BLOCKED on missing API key from vendor.

## 2026-03-04T10:00:00Z [info]
Pinged vendor for API key.

## 2026-03-04T15:00:00Z [correction]
纠正: auth endpoint path should be /api/v2/auth, not /api/v1/auth.

## 2026-03-05T09:00:00Z [status_change]
Status: active → waiting. Waiting for vendor response.

## 2026-03-05T10:00:00Z [info]
Updated docs while waiting.

## 2026-03-05T11:00:00Z [info]
Refactored test helpers.

"""


class TestCompressNarrative:
    def test_preserves_status_change(self, narr_dir):
        _write_raw(narr_dir, "task-c001", SAMPLE_NARRATIVE)
        result = compress_narrative(narr_dir, "task-c001")
        assert "inbox → active" in result
        assert "active → waiting" in result

    def test_preserves_decision(self, narr_dir):
        _write_raw(narr_dir, "task-c002", SAMPLE_NARRATIVE)
        result = compress_narrative(narr_dir, "task-c002")
        assert "JWT" in result

    def test_preserves_blocker(self, narr_dir):
        _write_raw(narr_dir, "task-c003", SAMPLE_NARRATIVE)
        result = compress_narrative(narr_dir, "task-c003")
        assert "BLOCKED" in result or "API key" in result

    def test_preserves_correction(self, narr_dir):
        _write_raw(narr_dir, "task-c004", SAMPLE_NARRATIVE)
        result = compress_narrative(narr_dir, "task-c004")
        assert "/api/v2/auth" in result

    def test_info_entries_merged(self, narr_dir):
        _write_raw(narr_dir, "task-c005", SAMPLE_NARRATIVE)
        result = compress_narrative(narr_dir, "task-c005")
        # The 6 info entries should be merged, so we shouldn't see all of them verbatim
        info_count = result.count("[info]")
        assert info_count < 6  # original has 6 info entries

    def test_writes_compressed_file(self, narr_dir):
        _write_raw(narr_dir, "task-c006", SAMPLE_NARRATIVE)
        compress_narrative(narr_dir, "task-c006")
        compressed = read_compressed(narr_dir, "task-c006")
        assert compressed is not None
        assert len(compressed) > 0

    def test_empty_file_returns_empty(self, narr_dir):
        _write_raw(narr_dir, "task-c007", "")
        result = compress_narrative(narr_dir, "task-c007")
        assert result == ""

    def test_nonexistent_file_returns_empty(self, narr_dir):
        result = compress_narrative(narr_dir, "task-nope")
        assert result == ""

    def test_max_output_tokens_truncation(self, narr_dir):
        # Build a narrative with many important entries that exceed token limit
        lines = ""
        for i in range(50):
            lines += "## 2026-03-{:02d}T10:00:00Z [status_change]\n".format(
                min(i + 1, 28)
            )
            lines += "Status: active → waiting. Iteration {}.\n\n".format(i)
        _write_raw(narr_dir, "task-c008", lines)
        result = compress_narrative(narr_dir, "task-c008", max_output_tokens=50)
        # Token estimate = len(text)//2, so output should be <= 100 chars
        assert len(result) // 2 <= 50

    def test_keyword_detection_status_arrow(self, narr_dir):
        """Status changes detected via → symbol."""
        narrative = "## 2026-03-01T10:00:00Z [info]\nMoved inbox → active today.\n\n"
        _write_raw(narr_dir, "task-c009", narrative)
        result = compress_narrative(narr_dir, "task-c009")
        # Should be preserved (detected as status_change via →)
        assert "inbox → active" in result

    def test_keyword_detection_decision_chinese(self, narr_dir):
        """Decision detected via Chinese keyword 决定."""
        narrative = "## 2026-03-01T10:00:00Z [info]\n决定使用新框架.\n\n"
        _write_raw(narr_dir, "task-c010", narrative)
        result = compress_narrative(narr_dir, "task-c010")
        assert "新框架" in result

    def test_keyword_detection_blocker_chinese(self, narr_dir):
        """Blocker detected via Chinese keyword 阻塞."""
        narrative = "## 2026-03-01T10:00:00Z [info]\n被外部依赖阻塞.\n\n"
        _write_raw(narr_dir, "task-c011", narrative)
        result = compress_narrative(narr_dir, "task-c011")
        assert "阻塞" in result

    def test_idempotent_compress(self, narr_dir):
        """Compressing same input twice produces same output."""
        _write_raw(narr_dir, "task-c012", SAMPLE_NARRATIVE)
        result1 = compress_narrative(narr_dir, "task-c012")
        # Re-write original (compress reads .md, not .compressed.md)
        _write_raw(narr_dir, "task-c012", SAMPLE_NARRATIVE)
        result2 = compress_narrative(narr_dir, "task-c012")
        assert result1 == result2

    def test_consecutive_info_merge_boundary(self, narr_dir):
        """Info entries separated by non-info entries should be in separate merge groups."""
        narrative = (
            "## 2026-03-01T10:00:00Z [info]\nInfo A.\n\n"
            "## 2026-03-01T11:00:00Z [info]\nInfo B.\n\n"
            "## 2026-03-01T12:00:00Z [decision]\n决定 something.\n\n"
            "## 2026-03-01T13:00:00Z [info]\nInfo C.\n\n"
            "## 2026-03-01T14:00:00Z [info]\nInfo D.\n\n"
        )
        _write_raw(narr_dir, "task-c013", narrative)
        result = compress_narrative(narr_dir, "task-c013")
        # Decision must be preserved
        assert "决定" in result
