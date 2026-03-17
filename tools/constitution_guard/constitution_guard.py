#!/usr/bin/env python3
# Constitution Guard — Unified CLI entry point
# What: Coordinates three interceptors (float scanner, test lock, core path gate).
#   Provides CLI interface for pre-commit hooks, CI pipeline, and manual use.
# What NOT: Not an interceptor itself. Just orchestration, config loading, and reporting.
# Interacts with: ast_float_scanner, ironclad_test_lock, core_path_gate modules.
#   Reads constitution_guard.json for configuration.

"""
Constitution Guard CLI — the single entry point for all Constitution enforcement.

Exit codes:
  0 = All checks passed
  1 = Hard block (float violation or test lock violation)
  2 = Needs Founder approval (core path change detected)

Why a unified CLI instead of three separate tools?
  One config, one invocation, one report. Reduces CI complexity and maintenance.
"""

import argparse
import glob
import json
import os
import sys

# Import sibling modules
_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)

from ast_float_scanner import scan_file, scan_files
from ironclad_test_lock import check_invariants, update_hashes
from core_path_gate import check_paths


def load_config(config_path=None):
    """Load constitution_guard.json config.

    Config resolution order:
    1. CONSTITUTION_GUARD_CONFIG env var
    2. Explicit config_path argument
    3. Default: constitution_guard.json in the same directory as this script
    """
    if config_path is None:
        config_path = os.environ.get('CONSTITUTION_GUARD_CONFIG')
    if config_path is None:
        config_path = os.path.join(_dir, 'constitution_guard.json')

    with open(config_path, 'r') as f:
        return json.load(f)


def _collect_files_by_glob(patterns):
    """Expand glob patterns to actual file paths."""
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))
    return files


def run_float_scanner(config):
    """Run AST Float Scanner. Returns (findings_list, exit_code)."""
    cfg = config.get('float_scanner', {})
    if not cfg.get('enabled', True):
        return [], 0

    paths = cfg.get('paths', [])
    whitelist = cfg.get('whitelist', [])

    # Collect files matching scan paths
    target_files = _collect_files_by_glob(paths)

    # Remove whitelisted files
    whitelist_files = set()
    for wp in whitelist:
        whitelist_files.update(glob.glob(wp, recursive=True))

    target_files = [f for f in target_files if f not in whitelist_files]

    if not target_files:
        return [], 0

    findings = scan_files(target_files)
    exit_code = 1 if findings else 0
    return findings, exit_code


def run_test_lock(config):
    """Run Ironclad Test Lock. Returns (violations_list, exit_code)."""
    cfg = config.get('test_lock', {})
    if not cfg.get('enabled', True):
        return [], 0

    protected_dir = cfg.get('protected_dir', 'tests/invariants/')
    hash_file = cfg.get('hash_file', '.invariant_hashes.json')

    violations = check_invariants(protected_dir, hash_file)
    exit_code = 1 if violations else 0
    return violations, exit_code


def run_core_path_gate(config, changed_files=None):
    """Run Core Path Gate. Returns (result_dict, exit_code)."""
    cfg = config.get('core_path_gate', {})
    if not cfg.get('enabled', True):
        return {'flagged': False, 'matched_files': []}, 0

    core_paths = cfg.get('core_paths', [])

    if changed_files is None:
        changed_files = []

    result = check_paths(changed_files, core_paths)
    exit_code = 2 if result['flagged'] else 0
    return result, exit_code


def cmd_check(args, config):
    """Run checks. --only limits to a single interceptor."""
    only = getattr(args, 'only', None)
    max_exit = 0

    if only is None or only == 'float':
        findings, code = run_float_scanner(config)
        if findings:
            print(f"🚫 Float Scanner: {len(findings)} violation(s) found")
            for f in findings:
                print(f"  {f['file']}:{f['line']} [{f['type']}] {f['snippet']}")
        else:
            print("✅ Float Scanner: clean")
        max_exit = max(max_exit, code)

    if only is None or only == 'testlock':
        violations, code = run_test_lock(config)
        if violations:
            print(f"🚫 Test Lock: {len(violations)} violation(s) found")
            for v in violations:
                print(f"  [{v['type']}] {v['file']}: {v['detail']}")
        else:
            print("✅ Test Lock: clean")
        max_exit = max(max_exit, code)

    if only is None or only == 'corepath':
        # For corepath, we'd normally get changed files from git diff.
        # In check mode without git context, we scan nothing (pass).
        changed = getattr(args, 'files', []) or []
        result, code = run_core_path_gate(config, changed)
        if result['flagged']:
            print(f"⚠️  Core Path Gate: {len(result['matched_files'])} file(s) need Founder approval")
            for mf in result['matched_files']:
                print(f"  {mf} → needs-founder-approval")
        else:
            print("✅ Core Path Gate: clean")
        max_exit = max(max_exit, code)

    return max_exit


def cmd_update_hashes(args, config):
    """Update invariant test hash baseline."""
    cfg = config.get('test_lock', {})
    protected_dir = cfg.get('protected_dir', 'tests/invariants/')
    hash_file = cfg.get('hash_file', '.invariant_hashes.json')

    hashes = update_hashes(protected_dir, hash_file)
    print(f"✅ Updated hash baseline: {len(hashes)} file(s) in {hash_file}")
    return 0


def cmd_status(args, config):
    """Display current configuration and module status."""
    print("Constitution Guard — Status")
    print("=" * 40)

    fs = config.get('float_scanner', {})
    print(f"\nFloat Scanner: {'enabled' if fs.get('enabled') else 'disabled'}")
    print(f"  Scan paths: {fs.get('paths', [])}")
    print(f"  Whitelist: {fs.get('whitelist', [])}")

    tl = config.get('test_lock', {})
    print(f"\nTest Lock: {'enabled' if tl.get('enabled') else 'disabled'}")
    print(f"  Protected dir: {tl.get('protected_dir', 'N/A')}")
    print(f"  Hash file: {tl.get('hash_file', 'N/A')}")

    cp = config.get('core_path_gate', {})
    print(f"\nCore Path Gate: {'enabled' if cp.get('enabled') else 'disabled'}")
    print(f"  Core paths: {cp.get('core_paths', [])}")
    print(f"  Approvers: {cp.get('approvers', [])}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Constitution Guard — Physical interceptors for Constitution enforcement'
    )
    subparsers = parser.add_subparsers(dest='command')

    # check
    check_parser = subparsers.add_parser('check', help='Run constitution checks')
    check_parser.add_argument('--only', choices=['float', 'testlock', 'corepath'],
                              help='Run only a specific interceptor')
    check_parser.add_argument('--files', nargs='*', help='Files to check (for corepath)')

    # update-hashes
    subparsers.add_parser('update-hashes', help='Update invariant test hash baseline')

    # status
    subparsers.add_parser('status', help='Show current configuration')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    try:
        config = load_config()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Config error: {e}", file=sys.stderr)
        return 1

    commands = {
        'check': cmd_check,
        'update-hashes': cmd_update_hashes,
        'status': cmd_status,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args, config)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
