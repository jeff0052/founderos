"""Tests for AST Float Scanner — Constitution Article 13.

Tests that the scanner correctly detects float usage in payment code paths
and correctly allows safe patterns.
"""
import os
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'constitution_guard'))

from ast_float_scanner import scan_file


class TestMustBlock:
    """These patterns MUST be detected and blocked."""

    def _write_tmp(self, code: str) -> str:
        """Write code to a temp .py file, return path."""
        fd, path = tempfile.mkstemp(suffix='.py')
        with os.fdopen(fd, 'w') as f:
            f.write(code)
        return path

    def test_float_literal(self):
        """amount = 0.1 must be caught."""
        path = self._write_tmp("amount = 0.1\n")
        try:
            findings = scan_file(path)
            assert len(findings) > 0
            assert any(f['type'] == 'float_literal' for f in findings)
        finally:
            os.unlink(path)

    def test_float_call(self):
        """float(val) must be caught."""
        path = self._write_tmp("x = float(val)\n")
        try:
            findings = scan_file(path)
            assert len(findings) > 0
            assert any(f['type'] == 'float_call' for f in findings)
        finally:
            os.unlink(path)

    def test_float_annotation(self):
        """def f(a: float): must be caught."""
        path = self._write_tmp("def f(a: float):\n    pass\n")
        try:
            findings = scan_file(path)
            assert len(findings) > 0
            assert any(f['type'] == 'float_annotation' for f in findings)
        finally:
            os.unlink(path)

    def test_division_operator(self):
        """a / b must be caught (use // or Decimal division)."""
        path = self._write_tmp("result = a / b\n")
        try:
            findings = scan_file(path)
            assert len(findings) > 0
            assert any(f['type'] == 'division' for f in findings)
        finally:
            os.unlink(path)

    def test_multiple_violations_in_one_file(self):
        """Multiple violations should all be reported."""
        code = "x = 0.1\ny = float(z)\nresult = a / b\n"
        path = self._write_tmp(code)
        try:
            findings = scan_file(path)
            assert len(findings) >= 3
        finally:
            os.unlink(path)


class TestMustAllow:
    """These patterns MUST NOT be flagged."""

    def _write_tmp(self, code: str) -> str:
        fd, path = tempfile.mkstemp(suffix='.py')
        with os.fdopen(fd, 'w') as f:
            f.write(code)
        return path

    def test_integer_literal(self):
        """amount = 100 is fine."""
        path = self._write_tmp("amount = 100\n")
        try:
            findings = scan_file(path)
            assert len(findings) == 0
        finally:
            os.unlink(path)

    def test_decimal_usage(self):
        """Decimal('0.1') is the correct pattern."""
        path = self._write_tmp('from decimal import Decimal\namount = Decimal("0.1")\n')
        try:
            findings = scan_file(path)
            assert len(findings) == 0
        finally:
            os.unlink(path)

    def test_floor_division(self):
        """a // b is integer division, should be allowed."""
        path = self._write_tmp("result = a // b\n")
        try:
            findings = scan_file(path)
            assert len(findings) == 0
        finally:
            os.unlink(path)

    def test_noqa_comment(self):
        """Lines with # noqa: float-ok should be exempted."""
        path = self._write_tmp("ratio = 0.5  # noqa: float-ok\n")
        try:
            findings = scan_file(path)
            assert len(findings) == 0
        finally:
            os.unlink(path)

    def test_clean_code(self):
        """Normal code with no floats should pass."""
        code = "x = 42\ny = 'hello'\nz = [1, 2, 3]\n"
        path = self._write_tmp(code)
        try:
            findings = scan_file(path)
            assert len(findings) == 0
        finally:
            os.unlink(path)
