"""Tests for memory tool handlers in spine/tools.py."""

import json
import os
import subprocess
import sys

import pytest

from spine.schema import init_db
from spine.store import Store
from spine import validator as validator_module
from spine import narrative as narrative_module
from spine.tools import ToolHandler


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)


@pytest.fixture
def handler(store, tmp_path):
    narratives_dir = str(tmp_path / "narratives")
    os.makedirs(narratives_dir, exist_ok=True)
    return ToolHandler(
        store=store,
        validator_module=validator_module,
        narrative_module=narrative_module,
        narratives_dir=narratives_dir,
    )


def _add_fact(handler, content="公司在新加坡", **overrides):
    params = dict(layer="fact", content=content, source="manual", priority="P0", confidence=0.9)
    params.update(overrides)
    return handler.handle("memory_add", params)


def _add_scratch(handler, content="今天在讨论记忆架构", **overrides):
    params = dict(layer="scratch", content=content, source="auto", priority="P2", confidence=0.6)
    params.update(overrides)
    return handler.handle("memory_add", params)


# ── Happy Path ────────────────────────────────────────────────────

class TestMemoryAddTool:
    def test_add_fact(self, handler):
        result = _add_fact(handler)
        assert result.success is True
        assert result.data["layer"] == "fact"
        assert result.data["content"] == "公司在新加坡"
        assert result.data["id"].startswith("mem-")

    def test_add_scratch(self, handler):
        result = _add_scratch(handler)
        assert result.success is True
        assert result.data["layer"] == "scratch"

    def test_add_judgment(self, handler):
        result = handler.handle("memory_add", {
            "layer": "judgment", "content": "Linear好用",
            "source": "manual", "sub_type": "preference",
        })
        assert result.success is True
        assert result.data["sub_type"] == "preference"


class TestMemorySearchTool:
    def test_search_by_layer(self, handler):
        _add_fact(handler)
        _add_scratch(handler)
        result = handler.handle("memory_search", {"layer": "fact"})
        assert result.success is True
        assert len(result.data["memories"]) == 1
        assert result.data["memories"][0]["layer"] == "fact"

    def test_search_empty(self, handler):
        result = handler.handle("memory_search", {})
        assert result.success is True
        assert result.data["memories"] == []

    def test_search_by_keyword(self, handler):
        _add_fact(handler, content="团队在北京办公")
        result = handler.handle("memory_search", {"keyword": "北京"})
        assert result.success is True
        assert len(result.data["memories"]) == 1


class TestMemoryUpdateTool:
    def test_update_content(self, handler):
        add_result = _add_fact(handler)
        mem_id = add_result.data["id"]
        result = handler.handle("memory_update", {
            "memory_id": mem_id, "content": "公司在东京",
        })
        assert result.success is True
        assert result.data["content"] == "公司在东京"

    def test_update_tags(self, handler):
        add_result = _add_fact(handler)
        mem_id = add_result.data["id"]
        result = handler.handle("memory_update", {
            "memory_id": mem_id, "tags": ["location"],
        })
        assert result.success is True
        assert result.data["tags"] == ["location"]


class TestMemoryForgetTool:
    def test_forget(self, handler):
        add_result = _add_fact(handler)
        mem_id = add_result.data["id"]
        result = handler.handle("memory_forget", {"memory_id": mem_id})
        assert result.success is True
        assert result.data["archived_at"] is not None


class TestMemoryPromoteTool:
    def test_promote_scratch_to_fact(self, handler):
        add_result = _add_scratch(handler)
        mem_id = add_result.data["id"]
        # Confirm first (auto_extracted → user_confirmed) so promote can work
        handler.handle("memory_confirm", {"memory_id": mem_id})
        result = handler.handle("memory_promote", {
            "memory_id": mem_id, "target_layer": "fact", "confidence": 0.9,
        })
        assert result.success is True
        assert result.data["layer"] == "fact"

    def test_promote_scratch_to_judgment(self, handler):
        add_result = _add_scratch(handler)
        mem_id = add_result.data["id"]
        handler.handle("memory_confirm", {"memory_id": mem_id})
        result = handler.handle("memory_promote", {
            "memory_id": mem_id, "target_layer": "judgment",
            "sub_type": "lesson",
        })
        assert result.success is True
        assert result.data["layer"] == "judgment"


class TestMemoryConfirmTool:
    def test_confirm_auto_extracted(self, handler):
        add_result = _add_scratch(handler)
        mem_id = add_result.data["id"]
        result = handler.handle("memory_confirm", {"memory_id": mem_id})
        assert result.success is True
        assert result.data["verification"] == "user_confirmed"


# ── Error Path ────────────────────────────────────────────────────

class TestMemoryToolErrors:
    def test_add_invalid_layer(self, handler):
        result = handler.handle("memory_add", {
            "layer": "bogus", "content": "test", "source": "manual",
        })
        assert result.success is False
        assert "layer" in result.error

    def test_add_empty_content(self, handler):
        result = handler.handle("memory_add", {
            "layer": "fact", "content": "", "source": "manual",
        })
        assert result.success is False
        assert "content" in result.error

    def test_update_not_found(self, handler):
        result = handler.handle("memory_update", {
            "memory_id": "mem-000000", "content": "nope",
        })
        assert result.success is False
        assert "not found" in result.error

    def test_forget_not_found(self, handler):
        result = handler.handle("memory_forget", {"memory_id": "mem-000000"})
        assert result.success is False
        assert "not found" in result.error

    def test_confirm_already_confirmed(self, handler):
        add_result = _add_fact(handler)  # manual → user_confirmed
        mem_id = add_result.data["id"]
        result = handler.handle("memory_confirm", {"memory_id": mem_id})
        assert result.success is False
        assert "auto_extracted" in result.error

    def test_promote_non_scratch(self, handler):
        add_result = _add_fact(handler)
        mem_id = add_result.data["id"]
        result = handler.handle("memory_promote", {
            "memory_id": mem_id, "target_layer": "judgment",
        })
        assert result.success is False
        assert "scratch" in result.error

    def test_forget_already_archived(self, handler):
        add_result = _add_fact(handler)
        mem_id = add_result.data["id"]
        handler.handle("memory_forget", {"memory_id": mem_id})
        result = handler.handle("memory_forget", {"memory_id": mem_id})
        assert result.success is False
        assert "archived" in result.error

    def test_update_auto_extracted_requires_confirm(self, handler):
        add_result = _add_scratch(handler)  # auto → auto_extracted
        mem_id = add_result.data["id"]
        result = handler.handle("memory_update", {
            "memory_id": mem_id, "content": "updated",
        })
        assert result.success is False
        assert "confirm" in result.error.lower()


# ── CLI E2E ───────────────────────────────────────────────────────

class TestMemoryToolCLI:
    def test_cli_memory_add(self):
        """spine.py tool memory_add roundtrip via subprocess."""
        spine_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spine.py")
        params = json.dumps({
            "layer": "fact", "content": "CLI测试记忆",
            "source": "manual", "priority": "P1", "confidence": 0.8,
        })
        result = subprocess.run(
            [sys.executable, spine_path, "tool", "memory_add", params],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": os.path.dirname(spine_path)},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["data"]["layer"] == "fact"
        assert output["data"]["id"].startswith("mem-")

    def test_cli_memory_search(self):
        """spine.py tool memory_search roundtrip via subprocess."""
        spine_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spine.py")
        # Add one first
        add_params = json.dumps({
            "layer": "scratch", "content": "CLI搜索测试",
            "source": "auto", "priority": "P2", "confidence": 0.6,
        })
        subprocess.run(
            [sys.executable, spine_path, "tool", "memory_add", add_params],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": os.path.dirname(spine_path)},
        )
        # Search
        search_params = json.dumps({"keyword": "CLI搜索"})
        result = subprocess.run(
            [sys.executable, spine_path, "tool", "memory_search", search_params],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": os.path.dirname(spine_path)},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert len(output["data"]["memories"]) >= 1
