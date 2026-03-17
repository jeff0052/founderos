"""Tests for Ironclad Test Lock — Constitution Article 5.

Tests that invariant test files cannot be modified, deleted, or renamed
without detection. New files should be allowed.
"""
import json
import os
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'constitution_guard'))

from ironclad_test_lock import check_invariants, update_hashes


class TestMustDetect:
    """Modifications to existing invariant tests MUST be detected."""

    def setup_method(self):
        """Create a temp directory simulating tests/invariants/ with baseline."""
        self.tmpdir = tempfile.mkdtemp()
        self.invariants_dir = os.path.join(self.tmpdir, 'tests', 'invariants')
        os.makedirs(self.invariants_dir)

        # Create two invariant test files
        self.test_file_1 = os.path.join(self.invariants_dir, 'test_payment_invariant.py')
        self.test_file_2 = os.path.join(self.invariants_dir, 'test_settlement_invariant.py')

        with open(self.test_file_1, 'w') as f:
            f.write("def test_payment_never_negative():\n    assert payment >= 0\n")
        with open(self.test_file_2, 'w') as f:
            f.write("def test_settlement_balanced():\n    assert debits == credits\n")

        # Generate baseline hashes
        self.hash_file = os.path.join(self.tmpdir, '.invariant_hashes.json')
        update_hashes(self.invariants_dir, self.hash_file)

        # Verify baseline was created
        with open(self.hash_file) as f:
            baseline = json.load(f)
        assert len(baseline) == 2

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_detect_modification(self):
        """Modified file content must be detected."""
        with open(self.test_file_1, 'w') as f:
            f.write("def test_payment_never_negative():\n    assert True  # cheating!\n")

        violations = check_invariants(self.invariants_dir, self.hash_file)
        assert len(violations) > 0
        assert any(v['type'] == 'MODIFIED' for v in violations)

    def test_detect_deletion(self):
        """Deleted invariant test must be detected."""
        os.unlink(self.test_file_2)

        violations = check_invariants(self.invariants_dir, self.hash_file)
        assert len(violations) > 0
        assert any(v['type'] == 'DELETED' for v in violations)

    def test_detect_rename(self):
        """Renamed file (delete + new name) must be detected as deletion."""
        new_path = os.path.join(self.invariants_dir, 'test_renamed.py')
        os.rename(self.test_file_1, new_path)

        violations = check_invariants(self.invariants_dir, self.hash_file)
        assert len(violations) > 0
        # Renaming removes the original, so at minimum DELETED should fire
        assert any(v['type'] == 'DELETED' for v in violations)


class TestMustAllow:
    """New files should NOT be flagged as violations."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.invariants_dir = os.path.join(self.tmpdir, 'tests', 'invariants')
        os.makedirs(self.invariants_dir)

        # Create one file and generate baseline
        self.existing = os.path.join(self.invariants_dir, 'test_existing.py')
        with open(self.existing, 'w') as f:
            f.write("def test_existing():\n    pass\n")

        self.hash_file = os.path.join(self.tmpdir, '.invariant_hashes.json')
        update_hashes(self.invariants_dir, self.hash_file)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_new_file_allowed(self):
        """Adding a new invariant test should not be a violation."""
        new_file = os.path.join(self.invariants_dir, 'test_new_invariant.py')
        with open(new_file, 'w') as f:
            f.write("def test_new_rule():\n    assert True\n")

        violations = check_invariants(self.invariants_dir, self.hash_file)
        assert len(violations) == 0

    def test_no_changes(self):
        """No changes at all should pass clean."""
        violations = check_invariants(self.invariants_dir, self.hash_file)
        assert len(violations) == 0
