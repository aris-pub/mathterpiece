"""Conformance tests for docs/spec/types.md."""

import pytest

from .support import accepted, compile_error, same_meaning

rule = pytest.mark.rule


@rule("type-notation")
class TestTypeNotation:
    def test_a_declared_type(self):
        compile_error("(type pos real (>= 0)) (pos k -1)")
        a = accepted("(type pos real (>= 0)) (pos k 1)").get("k").value.type
        b = accepted("((real (>= 0)) k 1)").get("k").value.type
        assert (a.base, a.constraints) == (b.base, b.constraints)


@rule("the-types")
class TestTheTypes:
    def test_the_type_colormap(self):
        same_meaning(
            "(func f ((colormap m)) (m 0.5)) (colormap cm ['red' 'blue']) (color v (f cm))",
            "(func f ((func[real color] m)) (m 0.5)) (colormap cm ['red' 'blue']) (color v (f cm))",
        )
