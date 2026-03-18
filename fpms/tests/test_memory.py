"""Tests for FPMS Memory Layer — PRD-memory-v2.2 verification."""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

# Ensure spine is importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spine.schema import init_db
from spine.store import Store
from spine.memory import MemoryStore, MemoryValidationError, MemoryStateError
from spine.models import AddMemoryInput, Memory


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    events_path = str(tmp_path / "events.jsonl")
    init_db(db_path)
    return Store(db_path=db_path, events_path=events_path)


@pytest.fixture
def ms(store):
    return MemoryStore(store)


def _add_fact(ms, content="公司在新加坡", **kwargs):
    defaults = dict(layer="fact", content=content, source="manual", priority="P0", confidence=0.9)
    defaults.update(kwargs)
    return ms.add_memory(AddMemoryInput(**defaults))


def _add_judgment(ms, content="Linear 比较好用", **kwargs):
    defaults = dict(layer="judgment", content=content, source="manual",
                    sub_type="preference", priority="P0", confidence=0.8)
    defaults.update(kwargs)
    return ms.add_memory(AddMemoryInput(**defaults))


def _add_scratch(ms, content="今天在讨论记忆架构", **kwargs):
    defaults = dict(layer="scratch", content=content, source="auto", priority="P2", confidence=0.6)
    defaults.update(kwargs)
    return ms.add_memory(AddMemoryInput(**defaults))


# ── §2.1 Three Layer Model ──────────────────────────────────────

class TestThreeLayerModel:
    def test_create_fact(self, ms):
        mem = _add_fact(ms)
        assert mem.layer == "fact"
        assert mem.id.startswith("mem-")
        assert len(mem.id) == 10  # mem- + 6 hex

    def test_create_judgment_with_sub_type(self, ms):
        mem = _add_judgment(ms, sub_type="decision")
        assert mem.layer == "judgment"
        assert mem.sub_type == "decision"

    def test_create_scratch(self, ms):
        mem = _add_scratch(ms)
        assert mem.layer == "scratch"
        assert mem.priority == "P2"

    def test_invalid_layer_rejected(self, ms):
        with pytest.raises(Exception):  # Pydantic validation
            ms.add_memory(AddMemoryInput(layer="constitution", content="test", source="manual"))

    def test_sub_type_only_for_judgment(self, ms):
        with pytest.raises(MemoryValidationError, match="sub_type is only valid for"):
            ms.add_memory(AddMemoryInput(
                layer="fact", content="some fact", source="manual",
                sub_type="preference", confidence=0.9
            ))

    def test_all_sub_types(self, ms):
        for st in ["preference", "decision", "lesson", "pattern"]:
            mem = ms.add_memory(AddMemoryInput(
                layer="judgment", content=f"test {st}", source="manual",
                sub_type=st, confidence=0.8
            ))
            assert mem.sub_type == st


# ── §2.2 Layer Admission Rules ──────────────────────────────────

class TestLayerAdmission:
    def test_fact_rejects_low_confidence(self, ms):
        with pytest.raises(MemoryValidationError, match="confidence ≥ 0.5"):
            ms.add_memory(AddMemoryInput(
                layer="fact", content="some fact", source="manual", confidence=0.3
            ))

    def test_fact_rejects_comparative_words_auto(self, ms):
        with pytest.raises(MemoryValidationError, match="comparative/tendency"):
            ms.add_memory(AddMemoryInput(
                layer="fact", content="这个工具更好用", source="auto", confidence=0.9
            ))

    def test_fact_allows_comparative_manual(self, ms):
        # Manual source doesn't have comparative word restriction
        mem = ms.add_memory(AddMemoryInput(
            layer="fact", content="这个工具更适合我们", source="manual", confidence=0.9
        ))
        assert mem.layer == "fact"

    def test_auto_rejects_forbidden_words(self, ms):
        forbidden = ["可能是这样", "也许需要", "大概如此", "推测结果", "应该是", "似乎如此", "看起来是"]
        for content in forbidden:
            with pytest.raises(MemoryValidationError, match="forbidden words"):
                ms.add_memory(AddMemoryInput(
                    layer="judgment", content=content, source="auto", confidence=0.8
                ))

    def test_manual_allows_forbidden_words(self, ms):
        # Manual source is not restricted by forbidden words
        mem = ms.add_memory(AddMemoryInput(
            layer="judgment", content="可能需要重新考虑", source="manual",
            sub_type="decision", confidence=0.8
        ))
        assert mem.content == "可能需要重新考虑"


# ── §2.5 Source × Verification Legal Combos ─────────────────────

class TestSourceVerification:
    def test_auto_gets_auto_extracted(self, ms):
        mem = _add_scratch(ms, source="auto")
        assert mem.verification == "auto_extracted"

    def test_manual_gets_user_confirmed(self, ms):
        mem = _add_fact(ms, source="manual")
        assert mem.verification == "user_confirmed"

    def test_system_gets_system_verified(self, ms):
        mem = ms.add_memory(AddMemoryInput(
            layer="fact", content="task-a489 完成", source="system", confidence=0.95
        ))
        assert mem.verification == "system_verified"

    def test_auto_cannot_be_user_confirmed(self, ms):
        with pytest.raises(MemoryValidationError, match="requires verification"):
            ms.add_memory(AddMemoryInput(
                layer="fact", content="test", source="auto",
                verification="user_confirmed", confidence=0.9
            ))

    def test_manual_cannot_be_auto_extracted(self, ms):
        with pytest.raises(MemoryValidationError, match="requires verification"):
            ms.add_memory(AddMemoryInput(
                layer="fact", content="test", source="manual",
                verification="auto_extracted", confidence=0.9
            ))


# ── §4 State Transitions ────────────────────────────────────────

class TestStateTransitions:
    def test_confirm_auto_extracted(self, ms):
        mem = _add_scratch(ms)
        assert mem.verification == "auto_extracted"
        confirmed = ms.confirm_memory(mem.id)
        assert confirmed.verification == "user_confirmed"

    def test_confirm_already_confirmed_fails(self, ms):
        mem = _add_fact(ms)  # manual → user_confirmed
        with pytest.raises(MemoryStateError, match="Only auto_extracted"):
            ms.confirm_memory(mem.id)

    def test_promote_scratch_to_fact(self, ms):
        mem = _add_scratch(ms, content="公司在新加坡", confidence=0.9)
        promoted = ms.promote_memory(mem.id, "fact")
        assert promoted.layer == "fact"

    def test_promote_scratch_to_judgment(self, ms):
        mem = _add_scratch(ms, content="这个教训很重要")
        promoted = ms.promote_memory(mem.id, "judgment", sub_type="lesson")
        assert promoted.layer == "judgment"
        assert promoted.sub_type == "lesson"

    def test_promote_non_scratch_fails(self, ms):
        mem = _add_fact(ms)
        with pytest.raises(MemoryStateError, match="Only scratch"):
            ms.promote_memory(mem.id, "judgment")

    def test_promote_revalidates_fact_confidence(self, ms):
        mem = _add_scratch(ms, confidence=0.3)
        with pytest.raises(MemoryValidationError, match="confidence ≥ 0.5"):
            ms.promote_memory(mem.id, "fact")

    def test_promote_revalidates_fact_content(self, ms):
        mem = _add_scratch(ms, content="通常是这样的")
        with pytest.raises(MemoryValidationError, match="comparative/tendency"):
            ms.promote_memory(mem.id, "fact")

    def test_promote_with_new_confidence(self, ms):
        mem = _add_scratch(ms, confidence=0.3)
        promoted = ms.promote_memory(mem.id, "fact", confidence=0.9)
        assert promoted.confidence == 0.9

    def test_update_requires_confirmed(self, ms):
        mem = _add_scratch(ms)  # auto_extracted
        with pytest.raises(MemoryStateError, match="confirm_memory first"):
            ms.update_memory(mem.id, {"content": "new content"})

    def test_update_confirmed_works(self, ms):
        mem = _add_fact(ms)  # manual → user_confirmed
        updated = ms.update_memory(mem.id, {"content": "updated fact"})
        assert updated.content == "updated fact"

    def test_update_immutable_fields(self, ms):
        mem = _add_fact(ms)
        for field in ["id", "layer", "verification", "source", "created_at"]:
            with pytest.raises(MemoryStateError, match="immutable"):
                ms.update_memory(mem.id, {field: "hack"})

    def test_forget_archives(self, ms):
        mem = _add_fact(ms)
        forgotten = ms.forget(mem.id)
        assert forgotten.archived_at is not None

    def test_forget_already_archived_fails(self, ms):
        mem = _add_fact(ms)
        ms.forget(mem.id)
        with pytest.raises(MemoryStateError, match="already archived"):
            ms.forget(mem.id)

    def test_cannot_confirm_archived(self, ms):
        mem = _add_scratch(ms)
        ms.forget(mem.id)
        with pytest.raises(MemoryStateError, match="archived"):
            ms.confirm_memory(mem.id)

    def test_cannot_promote_archived(self, ms):
        mem = _add_scratch(ms)
        ms.forget(mem.id)
        with pytest.raises(MemoryStateError, match="archived"):
            ms.promote_memory(mem.id, "fact")

    def test_cannot_update_archived(self, ms):
        mem = _add_fact(ms)
        ms.forget(mem.id)
        with pytest.raises(MemoryStateError, match="archived"):
            ms.update_memory(mem.id, {"content": "hack"})


# ── §FR-3 Search & Sort ─────────────────────────────────────────

class TestSearchAndSort:
    def test_search_by_layer(self, ms):
        _add_fact(ms)
        _add_judgment(ms)
        _add_scratch(ms)

        facts = ms.search_memories(layer="fact")
        assert all(m.layer == "fact" for m in facts)

    def test_search_by_tags(self, ms):
        _add_fact(ms, tags=["singapore", "company"])
        _add_fact(ms, content="node ID 用 6 位 hex", tags=["engineering"])

        results = ms.search_memories(tags=["singapore"])
        assert len(results) == 1
        assert "singapore" in results[0].tags

    def test_search_by_keyword(self, ms):
        _add_fact(ms, content="公司在新加坡")
        _add_fact(ms, content="node ID 用 6 位 hex")

        results = ms.search_memories(keyword="新加坡")
        assert len(results) == 1

    def test_search_by_node_id(self, ms):
        _add_fact(ms, node_id="project-7842")
        _add_fact(ms, content="other fact")

        results = ms.search_memories(node_id="project-7842")
        assert len(results) == 1

    def test_search_excludes_archived_by_default(self, ms):
        mem = _add_fact(ms)
        ms.forget(mem.id)

        results = ms.search_memories(layer="fact")
        assert len(results) == 0

    def test_search_includes_archived_when_asked(self, ms):
        mem = _add_fact(ms)
        ms.forget(mem.id)

        results = ms.search_memories(layer="fact", include_archived=True)
        assert len(results) == 1

    def test_search_pagination(self, ms):
        for i in range(5):
            _add_fact(ms, content=f"fact {i}")

        page1 = ms.search_memories(limit=2, offset=0)
        page2 = ms.search_memories(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    def test_sort_fact_before_judgment(self, ms):
        _add_judgment(ms)
        _add_fact(ms)

        results = ms.search_memories()
        assert results[0].layer == "fact"

    def test_sort_confirmed_before_auto(self, ms):
        _add_scratch(ms, content="auto content 1")
        _add_fact(ms, content="confirmed content")

        results = ms.search_memories()
        assert results[0].verification == "user_confirmed"

    def test_search_increments_access_count(self, ms):
        mem = _add_fact(ms)
        assert mem.access_count == 0

        results = ms.search_memories(layer="fact")
        assert len(results) == 1

        # Re-fetch to check updated count
        updated = ms.get_memory(mem.id)
        assert updated.access_count == 1

    def test_search_by_needs_review(self, ms):
        mem = _add_fact(ms)
        # Manually set needs_review for testing
        ms._conn.execute("UPDATE memories SET needs_review=1 WHERE id=?", (mem.id,))
        ms._conn.commit()

        results = ms.search_memories(needs_review=True)
        assert len(results) == 1

        results = ms.search_memories(needs_review=False)
        assert len(results) == 0


# ── §FR-4 Bundle Integration ────────────────────────────────────

class TestBundleIntegration:
    def test_get_resident_memories_empty(self, ms):
        results = ms.get_resident_memories()
        assert results == []

    def test_get_resident_facts(self, ms):
        _add_fact(ms, content="fact 1", priority="P0")
        _add_fact(ms, content="fact 2", priority="P1")  # not P0, excluded

        results = ms.get_resident_memories()
        assert len(results) == 1
        assert results[0].content == "fact 1"

    def test_get_resident_preferences(self, ms):
        _add_judgment(ms, content="pref 1", sub_type="preference", priority="P0")
        _add_judgment(ms, content="lesson 1", sub_type="lesson", priority="P0")  # not preference

        results = ms.get_resident_memories()
        # Only preference, not lesson
        prefs = [m for m in results if m.sub_type == "preference"]
        assert len(prefs) == 1

    def test_resident_excludes_auto_extracted(self, ms):
        ms.add_memory(AddMemoryInput(
            layer="fact", content="auto fact", source="auto",
            priority="P0", confidence=0.9
        ))
        results = ms.get_resident_memories()
        assert len(results) == 0  # auto_extracted excluded

    def test_resident_max_count(self, ms):
        for i in range(10):
            _add_fact(ms, content=f"fact {i}", priority="P0")

        results = ms.get_resident_memories(max_count=5)
        assert len(results) <= 5

    def test_bundle_renders_l_memory(self, ms, store):
        from spine.bundle import assemble, _render_l_memory
        from spine.focus import FocusResult

        _add_fact(ms, content="公司在新加坡", priority="P0")

        memories = ms.get_resident_memories()
        text = _render_l_memory(memories)
        assert "🧠 Memory" in text
        assert "公司在新加坡" in text
        assert "[fact]" in text


# ── §FR-5 Decay ──────────────────────────────────────────────────

class TestDecay:
    def _age_memory(self, ms, memory_id, days):
        """Helper: backdate created_at for decay testing."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        ms._conn.execute(
            "UPDATE memories SET created_at=? WHERE id=?",
            (old_date, memory_id),
        )
        ms._conn.commit()

    def test_scratch_expires_after_7_days(self, ms):
        mem = _add_scratch(ms)
        self._age_memory(ms, mem.id, 8)

        result = ms.run_decay()
        assert result["archived"] == 1

        updated = ms.get_memory(mem.id)
        assert updated.archived_at is not None

    def test_p2_expires_after_30_days(self, ms):
        mem = _add_fact(ms, priority="P2")
        self._age_memory(ms, mem.id, 31)

        result = ms.run_decay()
        assert result["archived"] == 1

    def test_p1_expires_after_90_days(self, ms):
        mem = _add_fact(ms, priority="P1")
        self._age_memory(ms, mem.id, 91)

        result = ms.run_decay()
        assert result["archived"] == 1

    def test_p0_never_expires(self, ms):
        mem = _add_fact(ms, priority="P0")
        self._age_memory(ms, mem.id, 365)

        result = ms.run_decay()
        assert result["archived"] == 0

    def test_high_access_prevents_decay(self, ms):
        mem = _add_fact(ms, priority="P2")
        # Set high access count
        ms._conn.execute("UPDATE memories SET access_count=10 WHERE id=?", (mem.id,))
        ms._conn.commit()
        self._age_memory(ms, mem.id, 31)

        result = ms.run_decay()
        assert result["archived"] == 0

    def test_conflict_triggers_needs_review(self, ms):
        mem = _add_fact(ms)
        ms._conn.execute("UPDATE memories SET conflict_count=4 WHERE id=?", (mem.id,))
        ms._conn.commit()

        result = ms.run_decay()
        assert result["flagged_review"] == 1

        updated = ms.get_memory(mem.id)
        assert updated.needs_review is True
        assert updated.archived_at is None  # NOT archived, just flagged


# ── §3 Event Sourcing ───────────────────────────────────────────

class TestEventSourcing:
    def test_create_produces_event(self, ms):
        mem = _add_fact(ms)
        cur = ms._conn.execute(
            "SELECT * FROM memory_events WHERE memory_id=?", (mem.id,)
        )
        events = cur.fetchall()
        assert len(events) == 1
        assert events[0]["event_type"] == "memory_created"

    def test_forget_produces_event(self, ms):
        mem = _add_fact(ms)
        ms.forget(mem.id)
        cur = ms._conn.execute(
            "SELECT * FROM memory_events WHERE memory_id=? AND event_type='memory_archived'",
            (mem.id,),
        )
        assert cur.fetchone() is not None

    def test_confirm_produces_event(self, ms):
        mem = _add_scratch(ms)
        ms.confirm_memory(mem.id)
        cur = ms._conn.execute(
            "SELECT * FROM memory_events WHERE memory_id=? AND event_type='memory_confirmed'",
            (mem.id,),
        )
        assert cur.fetchone() is not None

    def test_promote_produces_event(self, ms):
        mem = _add_scratch(ms, content="important scratch", confidence=0.9)
        ms.promote_memory(mem.id, "fact")
        cur = ms._conn.execute(
            "SELECT * FROM memory_events WHERE memory_id=? AND event_type='memory_promoted'",
            (mem.id,),
        )
        event = cur.fetchone()
        assert event is not None
        payload = json.loads(event["payload"])
        assert payload["from_layer"] == "scratch"
        assert payload["to_layer"] == "fact"

    def test_update_records_old_new(self, ms):
        mem = _add_fact(ms)
        ms.update_memory(mem.id, {"content": "updated"})
        cur = ms._conn.execute(
            "SELECT * FROM memory_events WHERE memory_id=? AND event_type='memory_updated'",
            (mem.id,),
        )
        event = cur.fetchone()
        payload = json.loads(event["payload"])
        assert "old" in payload
        assert "new" in payload

    def test_search_produces_access_events(self, ms):
        mem = _add_fact(ms)
        ms.search_memories(layer="fact")
        cur = ms._conn.execute(
            "SELECT * FROM memory_events WHERE memory_id=? AND event_type='memory_accessed'",
            (mem.id,),
        )
        assert cur.fetchone() is not None


# ── Negative Feedback ────────────────────────────────────────────

class TestNegativeFeedback:
    def test_forget_bumps_similar_conflict(self, ms):
        mem1 = _add_fact(ms, content="公司在新加坡")
        mem2 = _add_fact(ms, content="公司总部在新加坡")
        # Manually set similar_to
        ms._conn.execute("UPDATE memories SET similar_to=? WHERE id=?", (mem1.id, mem2.id))
        ms._conn.commit()

        ms.forget(mem2.id)
        updated = ms.get_memory(mem1.id)
        assert updated.conflict_count == 1


# ── Content Validation ───────────────────────────────────────────

class TestContentValidation:
    def test_empty_content_rejected(self, ms):
        with pytest.raises(Exception):  # Pydantic
            ms.add_memory(AddMemoryInput(layer="fact", content="", source="manual"))

    def test_long_content_rejected(self, ms):
        with pytest.raises(Exception):  # Pydantic
            ms.add_memory(AddMemoryInput(
                layer="fact", content="x" * 601, source="manual"
            ))

    def test_tags_stored_as_json(self, ms):
        mem = _add_fact(ms, tags=["sg", "company"])
        assert mem.tags == ["sg", "company"]

    def test_based_on_stored_as_json(self, ms):
        fact = _add_fact(ms)
        mem = _add_judgment(ms, based_on=[fact.id, "some text reference"])
        assert fact.id in mem.based_on


# ── Similarity Detection ────────────────────────────────────────

class TestSimilarity:
    def test_similar_detected(self, ms):
        mem1 = _add_fact(ms, content="公司在新加坡注册")
        mem2 = _add_fact(ms, content="公司在新加坡注册成立")
        # similar_to should be set on the second one
        assert mem2.similar_to == mem1.id

    def test_dissimilar_not_flagged(self, ms):
        _add_fact(ms, content="公司在新加坡")
        mem2 = _add_fact(ms, content="node ID 用 6 位 hex")
        assert mem2.similar_to is None
