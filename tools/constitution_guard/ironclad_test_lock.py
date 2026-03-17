# Ironclad Test Lock — Constitution Article 5
# What: Verifies invariant test files haven't been tampered with via SHA-256 hash check.
#   Detects: MODIFIED, DELETED, RENAMED (as deletion of original).
#   Allows: New files (adding new invariant tests is encouraged).
# What NOT: Not a test runner. Not a test quality checker. Not responsible for
#   deciding WHAT should be an invariant test — only that existing ones aren't changed.
# Interacts with: .invariant_hashes.json (baseline), tests/invariants/ directory,
#   called by constitution_guard.py CLI.

"""
Ironclad Test Lock — SHA-256 integrity check for invariant test files.

Why SHA-256 and not file modification time?
  Timestamps are unreliable (Git checkout resets them, CI environments don't preserve them).
  Content hash is the only reliable way to detect actual changes.
"""

import hashlib
import json
import os
from typing import List, Dict, Any


def _hash_file(filepath: str) -> str:
    """Compute SHA-256 hash of a file's content."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _collect_files(directory: str) -> Dict[str, str]:
    """Walk directory, return {relative_path: absolute_path} for all .py files."""
    files = {}
    if not os.path.isdir(directory):
        return files
    for root, _, filenames in os.walk(directory):
        for fname in filenames:
            if fname.endswith('.py'):
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, directory)
                files[rel_path] = abs_path
    return files


def update_hashes(invariants_dir: str, hash_file: str) -> Dict[str, str]:
    """Generate fresh hash baseline for all files in invariants_dir.

    This is the most dangerous operation in the system — it replaces the baseline.
    Should ONLY be run with Founder approval.
    """
    files = _collect_files(invariants_dir)
    hashes = {}
    for rel_path, abs_path in sorted(files.items()):
        hashes[rel_path] = _hash_file(abs_path)

    with open(hash_file, 'w') as f:
        json.dump(hashes, f, indent=2)

    return hashes


def check_invariants(invariants_dir: str, hash_file: str) -> List[Dict[str, Any]]:
    """Check invariant test files against baseline hashes.

    Returns list of violations, each a dict with:
      - type: 'MODIFIED' | 'DELETED'
      - file: relative path of the affected file
      - detail: human-readable description
    """
    # Load baseline
    if not os.path.isfile(hash_file):
        # No baseline = nothing to check (first run, need update-hashes first)
        return []

    with open(hash_file, 'r') as f:
        baseline = json.load(f)

    if not baseline:
        # Empty baseline = nothing protected yet
        return []

    # Collect current files
    current_files = _collect_files(invariants_dir)
    violations = []

    # Check each baseline entry
    for rel_path, expected_hash in baseline.items():
        if rel_path not in current_files:
            # File was deleted or renamed (rename = delete original + add new)
            violations.append({
                'type': 'DELETED',
                'file': rel_path,
                'detail': f'Invariant test file deleted: {rel_path}'
            })
        else:
            current_hash = _hash_file(current_files[rel_path])
            if current_hash != expected_hash:
                violations.append({
                    'type': 'MODIFIED',
                    'file': rel_path,
                    'detail': f'Invariant test file modified: {rel_path}'
                })

    # New files (in current but not in baseline) are NOT violations — allowed.

    return violations
