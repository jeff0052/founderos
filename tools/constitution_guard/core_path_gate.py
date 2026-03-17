# Core Path Gate — Constitution Article 3
# What: Flags changes to payment core paths for Founder approval.
#   Uses fnmatch glob patterns to match file paths against configured core_paths.
#   Returns which files matched and whether approval is needed.
# What NOT: Not a blocker (flags only, doesn't prevent commits). Not a code reviewer.
#   Does not inspect file content — only path matching.
# Interacts with: constitution_guard.json (core path config), called by constitution_guard.py CLI.

"""
Core Path Gate — path-based flagging for Founder approval.

Why fnmatch instead of regex?
  Glob patterns are what developers already use (.gitignore, shell, etc.).
  Lower cognitive overhead, fewer bugs, same expressive power for path matching.
"""

import fnmatch
from typing import List, Dict, Any


def check_paths(changed_files: List[str], core_paths: List[str]) -> Dict[str, Any]:
    """Check if any changed files match core path patterns.

    Args:
        changed_files: List of file paths (relative to repo root).
        core_paths: List of glob patterns defining core paths.

    Returns dict with:
        - flagged: bool (True if any core path matched)
        - matched_files: list of files that matched core patterns
        - matched_patterns: dict mapping each matched file to its matching pattern
    """
    matched_files = []
    matched_patterns = {}

    for filepath in changed_files:
        for pattern in core_paths:
            if _matches(filepath, pattern):
                if filepath not in matched_files:
                    matched_files.append(filepath)
                matched_patterns[filepath] = pattern
                break  # One match is enough per file

    return {
        'flagged': len(matched_files) > 0,
        'matched_files': matched_files,
        'matched_patterns': matched_patterns,
    }


def _matches(filepath: str, pattern: str) -> bool:
    """Check if a filepath matches a glob pattern.

    Handles ** (recursive) by checking both fnmatch and path prefix patterns.
    Why manual ** handling: fnmatch doesn't natively support ** as "any depth".
    We split on ** and check prefix + suffix independently.
    """
    if '**' in pattern:
        # Split pattern on ** and handle recursive matching
        parts = pattern.split('**')
        if len(parts) == 2:
            prefix = parts[0].rstrip('/')
            suffix = parts[1].lstrip('/')

            # Check prefix matches
            if prefix and not filepath.startswith(prefix + '/') and filepath != prefix:
                return False

            # If there's a suffix pattern, check the remaining path
            if suffix:
                # Get the part after the prefix
                if prefix:
                    remaining = filepath[len(prefix):].lstrip('/')
                else:
                    remaining = filepath

                # Check if any tail of the remaining path matches the suffix
                path_parts = remaining.split('/')
                for i in range(len(path_parts)):
                    candidate = '/'.join(path_parts[i:])
                    if fnmatch.fnmatch(candidate, suffix):
                        return True
                return False
            else:
                # Pattern like "src/payments/core/**" — matches anything under prefix
                return True

    # Simple glob pattern (no **)
    return fnmatch.fnmatch(filepath, pattern)
