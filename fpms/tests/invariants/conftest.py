"""Shared fixtures for FPMS invariant tests."""

import os
import tempfile
import pytest


@pytest.fixture
def tmp_db_path():
    """Create a temporary SQLite database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def tmp_events_path():
    """Create a temporary events.jsonl path."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def tmp_narratives_dir():
    """Create a temporary narratives directory."""
    d = tempfile.mkdtemp()
    yield d


@pytest.fixture
def store(tmp_db_path, tmp_events_path):
    """Create a Store instance with temporary paths."""
    from spine.schema import init_db
    from spine.store import Store
    init_db(tmp_db_path)
    return Store(db_path=tmp_db_path, events_path=tmp_events_path)
