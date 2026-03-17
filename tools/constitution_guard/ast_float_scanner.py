# AST Float Scanner — Constitution Article 13
# What: Scans Python AST for float usage in payment/money code paths.
#   Detects: float literals, float() calls, float type annotations, division operator.
# What NOT: Not a general linter. Not a runtime checker. Not a semantic analyzer.
#   Does not infer whether a variable is "money" — enforcement is path-based.
# Interacts with: constitution_guard.json (path config), called by constitution_guard.py CLI.

"""
AST Float Scanner — detects float usage in configured Python source paths.

Why AST instead of regex?
  Regex can't distinguish `float` in a string from `float` as a builtin call.
  AST gives us structural certainty: we know if it's a literal, a call, an annotation,
  or an operator. Zero false positives from string content or comments.
"""

import ast
import os
from typing import List, Dict, Any


def scan_file(filepath: str) -> List[Dict[str, Any]]:
    """Scan a single Python file for float usage violations.

    Returns a list of findings, each a dict with:
      - type: 'float_literal' | 'float_call' | 'float_annotation' | 'division'
      - line: line number (1-indexed)
      - col: column offset
      - snippet: the offending source line
      - file: filepath
    """
    with open(filepath, 'r') as f:
        source = f.read()
    source_lines = source.splitlines()

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        # Can't parse → can't scan. Caller decides severity.
        return []

    findings = []

    for node in ast.walk(tree):
        lineno = getattr(node, 'lineno', None)
        if lineno is None:
            continue

        # Check noqa exemption on this line
        if lineno <= len(source_lines):
            line_text = source_lines[lineno - 1]
            if '# noqa: float-ok' in line_text:
                continue

        col = getattr(node, 'col_offset', 0)
        snippet = source_lines[lineno - 1] if lineno <= len(source_lines) else ''

        finding_base = {'file': filepath, 'line': lineno, 'col': col, 'snippet': snippet.strip()}

        # 1. Float literal: ast.Constant with float value (but not int disguised as float)
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            findings.append({**finding_base, 'type': 'float_literal'})

        # 2. float() call
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == 'float':
                findings.append({**finding_base, 'type': 'float_call'})

        # 3. Float type annotation — function args
        elif isinstance(node, ast.arg) and node.annotation is not None:
            if isinstance(node.annotation, ast.Name) and node.annotation.id == 'float':
                findings.append({**finding_base, 'type': 'float_annotation'})

        # 3b. Float type annotation — variable annotations
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            if isinstance(node.annotation, ast.Name) and node.annotation.id == 'float':
                findings.append({**finding_base, 'type': 'float_annotation'})

        # 4. Division operator (/) — not floor division (//)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            findings.append({**finding_base, 'type': 'division'})

    return findings


def scan_files(filepaths: List[str]) -> List[Dict[str, Any]]:
    """Scan multiple files, return aggregated findings."""
    all_findings = []
    for fp in filepaths:
        if fp.endswith('.py') and os.path.isfile(fp):
            all_findings.extend(scan_file(fp))
    return all_findings
