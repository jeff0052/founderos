"""Tests for Constitution Guard CLI entry point.

Tests the unified CLI interface: check, check --only, update-hashes, status.
Tests exit codes: 0 (pass), 1 (hard block), 2 (needs approval).
"""
import json
import os
import subprocess
import sys
import tempfile
import pytest

GUARD_SCRIPT = os.path.join(
    os.path.dirname(__file__), '..', '..', 'tools', 'constitution_guard', 'constitution_guard.py'
)


def run_guard(*args, config_path=None, cwd=None):
    """Run constitution_guard.py CLI and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, GUARD_SCRIPT] + list(args)
    env = os.environ.copy()
    if config_path:
        env['CONSTITUTION_GUARD_CONFIG'] = config_path
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


class TestStatusCommand:
    """Test the 'status' subcommand."""

    def test_status_shows_config(self):
        """status should display current configuration."""
        code, stdout, _ = run_guard('status')
        assert code == 0
        assert 'float_scanner' in stdout or 'Float Scanner' in stdout


class TestCheckCommand:
    """Test the 'check' subcommand and exit codes."""

    def test_check_clean_exits_zero(self):
        """With no violations, check should exit 0."""
        # Create a temp dir with no offending files
        tmpdir = tempfile.mkdtemp()
        config = {
            "float_scanner": {"enabled": True, "paths": [], "whitelist": []},
            "test_lock": {"enabled": True, "protected_dir": os.path.join(tmpdir, "invariants/"), "hash_file": os.path.join(tmpdir, "hashes.json")},
            "core_path_gate": {"enabled": True, "core_paths": [], "approvers": ["jeff"]}
        }
        config_path = os.path.join(tmpdir, 'config.json')
        hash_path = config['test_lock']['hash_file']
        inv_dir = config['test_lock']['protected_dir']
        os.makedirs(inv_dir, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config, f)
        with open(hash_path, 'w') as f:
            json.dump({}, f)

        code, stdout, _ = run_guard('check', config_path=config_path)
        assert code == 0

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_check_only_float(self):
        """check --only float should only run the float scanner."""
        code, stdout, _ = run_guard('check', '--only', 'float')
        # Should at least run without crashing
        assert code in (0, 1, 2)

    def test_check_only_testlock(self):
        """check --only testlock should only run test lock."""
        code, stdout, _ = run_guard('check', '--only', 'testlock')
        assert code in (0, 1, 2)

    def test_check_only_corepath(self):
        """check --only corepath should only run core path gate."""
        code, stdout, _ = run_guard('check', '--only', 'corepath')
        assert code in (0, 1, 2)


class TestUpdateHashes:
    """Test the 'update-hashes' subcommand."""

    def test_update_hashes_creates_baseline(self):
        """update-hashes should create/update the hash baseline file."""
        tmpdir = tempfile.mkdtemp()
        inv_dir = os.path.join(tmpdir, 'invariants')
        os.makedirs(inv_dir)
        hash_file = os.path.join(tmpdir, 'hashes.json')

        # Create a test file
        with open(os.path.join(inv_dir, 'test_example.py'), 'w') as f:
            f.write("def test_example():\n    assert True\n")

        config = {
            "float_scanner": {"enabled": True, "paths": [], "whitelist": []},
            "test_lock": {"enabled": True, "protected_dir": inv_dir, "hash_file": hash_file},
            "core_path_gate": {"enabled": True, "core_paths": [], "approvers": ["jeff"]}
        }
        config_path = os.path.join(tmpdir, 'config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f)

        code, _, _ = run_guard('update-hashes', config_path=config_path)
        assert code == 0
        assert os.path.exists(hash_file)

        with open(hash_file) as f:
            hashes = json.load(f)
        assert len(hashes) == 1

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestExitCodes:
    """Test that exit codes follow the contract: 0=pass, 1=hard block, 2=needs approval."""

    def test_float_violation_exits_one(self):
        """Float violations should cause exit code 1 (hard block)."""
        tmpdir = tempfile.mkdtemp()

        # Create a file with float violation in a scanned path
        scan_dir = os.path.join(tmpdir, 'src', 'payments')
        os.makedirs(scan_dir)
        with open(os.path.join(scan_dir, 'processor.py'), 'w') as f:
            f.write("amount = 0.1\n")

        config = {
            "float_scanner": {
                "enabled": True,
                "paths": [os.path.join(tmpdir, "src/payments/**/*.py")],
                "whitelist": []
            },
            "test_lock": {"enabled": False, "protected_dir": "/nonexistent", "hash_file": "/nonexistent"},
            "core_path_gate": {"enabled": False, "core_paths": [], "approvers": []}
        }
        config_path = os.path.join(tmpdir, 'config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f)

        code, _, _ = run_guard('check', config_path=config_path)
        assert code == 1

        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
