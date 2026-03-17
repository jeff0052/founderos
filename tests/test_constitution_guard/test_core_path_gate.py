"""Tests for Core Path Gate — Constitution Article 3.

Tests that changes to payment core paths are flagged for Founder approval,
while non-core changes pass through.
"""
import json
import os
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'constitution_guard'))

from core_path_gate import check_paths


# Load config for core_paths
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'tools', 'constitution_guard', 'constitution_guard.json'
)
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)
CORE_PATHS = CONFIG['core_path_gate']['core_paths']


class TestMustFlag:
    """Changes to core paths MUST be flagged (exit 2 = needs approval)."""

    def test_payment_core_change(self):
        """src/payments/core/engine.py must be flagged."""
        result = check_paths(['src/payments/core/engine.py'], CORE_PATHS)
        assert result['flagged'] is True
        assert 'src/payments/core/engine.py' in result['matched_files']

    def test_settlement_change(self):
        """src/settlement/reconciler.py must be flagged."""
        result = check_paths(['src/settlement/reconciler.py'], CORE_PATHS)
        assert result['flagged'] is True

    def test_fees_change(self):
        """src/fees/calculator.py must be flagged."""
        result = check_paths(['src/fees/calculator.py'], CORE_PATHS)
        assert result['flagged'] is True

    def test_wallet_core_change(self):
        """src/wallet/core/balance.py must be flagged."""
        result = check_paths(['src/wallet/core/balance.py'], CORE_PATHS)
        assert result['flagged'] is True

    def test_invariant_hashes_change(self):
        """.invariant_hashes.json must be flagged."""
        result = check_paths(['.invariant_hashes.json'], CORE_PATHS)
        assert result['flagged'] is True

    def test_constitution_guard_config_change(self):
        """constitution_guard.json must be flagged."""
        result = check_paths(['constitution_guard.json'], CORE_PATHS)
        assert result['flagged'] is True

    def test_guard_tool_change(self):
        """tools/constitution_guard/ast_float_scanner.py must be flagged."""
        result = check_paths(['tools/constitution_guard/ast_float_scanner.py'], CORE_PATHS)
        assert result['flagged'] is True

    def test_mixed_files(self):
        """Mix of core and non-core: should flag with only core files matched."""
        files = ['src/payments/core/engine.py', 'src/api/views.py', 'README.md']
        result = check_paths(files, CORE_PATHS)
        assert result['flagged'] is True
        assert 'src/payments/core/engine.py' in result['matched_files']
        assert 'README.md' not in result['matched_files']


class TestMustAllow:
    """Non-core path changes MUST pass through (exit 0)."""

    def test_api_change(self):
        """src/api/views.py is not a core path."""
        result = check_paths(['src/api/views.py'], CORE_PATHS)
        assert result['flagged'] is False
        assert len(result['matched_files']) == 0

    def test_readme_change(self):
        """README.md is not a core path."""
        result = check_paths(['README.md'], CORE_PATHS)
        assert result['flagged'] is False

    def test_non_core_wallet(self):
        """src/wallet/utils.py (not core/) should pass."""
        result = check_paths(['src/wallet/utils.py'], CORE_PATHS)
        assert result['flagged'] is False

    def test_empty_file_list(self):
        """No files changed should pass."""
        result = check_paths([], CORE_PATHS)
        assert result['flagged'] is False
