"""What the conformance tests of docs/spec/data-model.md share: imports, sources and helpers."""

import pytest

from ..support import accepted, compile_error

rule = pytest.mark.rule

UNNAMED = pytest.mark.xfail(strict=True, reason="mtp-1s8z: a variable with no name compiles")

NAME = pytest.mark.xfail(strict=True, reason="mtp-teu1: only shapes have the attribute name")

__all__ = ["pytest", "accepted", "compile_error", "rule", "UNNAMED", "NAME"]
