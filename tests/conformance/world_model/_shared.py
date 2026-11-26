"""What the conformance tests of docs/spec/world-model.md share: imports, sources and helpers."""

import pytest

from ..support import compile_error, same_meaning

rule = pytest.mark.rule

__all__ = ["pytest", "compile_error", "same_meaning", "rule"]
