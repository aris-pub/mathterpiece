"""What the conformance tests of docs/spec/overview.md share: imports, sources and helpers."""

import pytest

from ..support import accepted, compile_error

rule = pytest.mark.rule

__all__ = ["pytest", "accepted", "compile_error", "rule"]
