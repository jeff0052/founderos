"""Regression tests for S1, S2, S3 bug fixes."""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from spine.models import Node, ContextBundle
from spine.focus import FocusResult
from spine.schema import init_db
from spine.store import Store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# S1: recovery.py passes max_tokens positionally into narratives_dir slot
# ---------------------------------------------------------------------------

class TestS1RecoveryAssembleKwargs:
    """bundle.assemble() expects narratives_dir=str, max_tokens=int.
    recovery.py was calling assemble(store, focus, dash, alerts, max_tokens)
    which puts the int max_tokens into the narratives_dir position."""

    @pytest.fixture
    def store(self, tmp_path):
        db = str(tmp_path / "test.db")
        ev = str(tmp_path / "events.jsonl")
        init_db(db)
        return Store(db_path=db, events_path=ev)

    def test_bootstrap_does_not_pass_int_as_narratives_dir(self, store):
        """After fix, bundle.assemble should receive narratives_dir as str,
        not max_tokens (int). We patch assemble to inspect actual args."""
        now = _now()
        store.create_node(Node(
            id="task-0001", title="T1", status="active", node_type="task",
            is_root=True, parent_id=None, summary="s", why=None,
            next_step=None, owner=None, deadline=None,
            is_persistent=False, created_at=now, updated_at=now,
            status_changed_at=now, archived_at=None,
        ))
        # Force focus to point at task-0001 so assemble builds L2
        fake_focus = FocusResult(primary="task-0001", secondaries=[])
        captured = {}

        import spine.bundle as bundle_mod
        _orig_assemble = bundle_mod.assemble

        def spy_assemble(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return _orig_assemble(*args, **kwargs)

        with patch("spine.recovery.focus_mod.arbitrate", return_value=fake_focus), \
             patch("spine.recovery.bundle.assemble", side_effect=spy_assemble):
            from spine import recovery
            recovery.bootstrap(store, narratives_dir="", max_tokens=5000)

        # The 5th positional arg (index 4) should be narratives_dir (str),
        # NOT max_tokens (int). Or better, it should be passed as kwarg.
        if captured.get("args") and len(captured["args"]) > 4:
            fifth_arg = captured["args"][4]
            assert isinstance(fifth_arg, str), \
                f"5th positional arg to assemble is {type(fifth_arg).__name__}={fifth_arg!r}, expected str (narratives_dir)"
        # If passed as kwargs, that's also fine
        if "narratives_dir" in captured.get("kwargs", {}):
            assert isinstance(captured["kwargs"]["narratives_dir"], str)


# ---------------------------------------------------------------------------
# S2: validator.py opens new DB connections instead of reusing store._conn
# ---------------------------------------------------------------------------

class TestS2ValidatorUsesStoreConn:
    """Validator functions should see uncommitted data inside a transaction
    because they use store._conn, not a fresh sqlite3.connect()."""

    @pytest.fixture
    def store(self, tmp_path):
        db = str(tmp_path / "test.db")
        ev = str(tmp_path / "events.jsonl")
        init_db(db)
        return Store(db_path=db, events_path=ev)

    def test_validate_attach_sees_uncommitted_parent(self, store):
        """Create a parent inside a transaction (uncommitted).
        validate_attach should still find it via store._conn."""
        from spine.validator import validate_attach

        now = _now()
        with store.transaction():
            store.create_node(Node(
                id="task-parent", title="Parent", status="active",
                node_type="task", is_root=True, parent_id=None,
                summary="p", why=None, next_step=None, owner=None,
                deadline=None, is_persistent=False,
                created_at=now, updated_at=now, status_changed_at=now,
                archived_at=None,
            ))
            store.create_node(Node(
                id="task-child", title="Child", status="inbox",
                node_type="task", is_root=False, parent_id=None,
                summary="c", why=None, next_step=None, owner=None,
                deadline=None, is_persistent=False,
                created_at=now, updated_at=now, status_changed_at=now,
                archived_at=None,
            ))
            # This should NOT raise NODE_NOT_FOUND because parent exists
            # in the same transaction
            validate_attach(store, "task-child", "task-parent")

    def test_validate_dependency_sees_uncommitted_target(self, store):
        """Create a target inside a transaction (uncommitted).
        validate_dependency should still find it via store._conn."""
        from spine.validator import validate_dependency

        now = _now()
        with store.transaction():
            store.create_node(Node(
                id="task-a", title="A", status="active",
                node_type="task", is_root=True, parent_id=None,
                summary="a", why=None, next_step=None, owner=None,
                deadline=None, is_persistent=False,
                created_at=now, updated_at=now, status_changed_at=now,
                archived_at=None,
            ))
            store.create_node(Node(
                id="task-b", title="B", status="active",
                node_type="task", is_root=True, parent_id=None,
                summary="b", why=None, next_step=None, owner=None,
                deadline=None, is_persistent=False,
                created_at=now, updated_at=now, status_changed_at=now,
                archived_at=None,
            ))
            # Should NOT raise NODE_NOT_FOUND
            validate_dependency(store, "task-a", "task-b")


# ---------------------------------------------------------------------------
# S3: Store.__init__ calls get_connection() which doesn't init_db/WAL
# ---------------------------------------------------------------------------

class TestS3StoreInitCreatesSchema:
    """Store.__init__ should ensure tables exist (call init_db),
    not just get_connection which only sets foreign_keys."""

    def test_store_on_fresh_db_can_create_node(self, tmp_path):
        """Create a Store pointing at a non-existent DB file.
        It should auto-initialize schema so create_node works."""
        db = str(tmp_path / "brand_new.db")
        ev = str(tmp_path / "events.jsonl")
        # Do NOT call init_db() manually — Store should handle it
        s = Store(db_path=db, events_path=ev)
        now = _now()
        node = s.create_node(Node(
            id="task-0001", title="Fresh", status="inbox",
            node_type="task", is_root=True, parent_id=None,
            summary=None, why=None, next_step=None, owner=None,
            deadline=None, is_persistent=False,
            created_at=now, updated_at=now, status_changed_at=now,
            archived_at=None,
        ))
        assert node.id == "task-0001"

    def test_store_uses_wal_mode(self, tmp_path):
        """Store should open DB in WAL mode for concurrent reads."""
        db = str(tmp_path / "wal_test.db")
        ev = str(tmp_path / "events.jsonl")
        s = Store(db_path=db, events_path=ev)
        mode = s._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
