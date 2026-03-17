"""Invariant: Write path never reads derived/cache tables.

This is a code-level invariant verified by static analysis of the source.

Source: PRD Invariant #7, Architecture: Derived Layer Isolation
"""

import ast
import os
import pytest


# Derived/cache table names that must never appear in write-path code
DERIVED_TABLES = {
    "global_view_cache",
    "risk_cache",
    "narrative_index",
    "archive_index",
    "derived_",
}

# Write-path modules (these must never read from derived tables)
WRITE_PATH_MODULES = [
    "spine/store.py",
    "spine/validator.py",
    "spine/tools.py",
    "spine/command_executor.py",
]


def _get_project_root() -> str:
    """Get the fpms project root."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _find_string_literals(filepath: str) -> list:
    """Extract all string literals from a Python source file."""
    with open(filepath) as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
    return strings


class TestDerivedIsolation:
    """Write-path code must not reference derived/cache tables."""

    @pytest.mark.parametrize("module_path", WRITE_PATH_MODULES)
    def test_write_path_no_derived_references(self, module_path):
        """Check that write-path modules don't contain derived table names in SQL strings."""
        root = _get_project_root()
        filepath = os.path.join(root, module_path)

        if not os.path.exists(filepath):
            pytest.skip(f"{filepath} not found (skeleton only)")

        strings = _find_string_literals(filepath)

        for s in strings:
            s_lower = s.lower()
            for table in DERIVED_TABLES:
                if table in s_lower:
                    # Allow if it's in a comment or docstring context
                    # But in SQL strings, this is a violation
                    if "select" in s_lower or "from" in s_lower or "join" in s_lower:
                        pytest.fail(
                            f"Write-path module {module_path} references derived table '{table}' "
                            f"in what appears to be a SQL query: ...{s[:100]}..."
                        )

    def test_write_path_modules_exist(self):
        """All write-path modules should exist (even if skeleton)."""
        root = _get_project_root()
        for module_path in WRITE_PATH_MODULES:
            filepath = os.path.join(root, module_path)
            assert os.path.exists(filepath), f"Write-path module {module_path} should exist"
