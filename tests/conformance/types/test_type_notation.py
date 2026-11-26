"""Conformance tests of the rule type-notation (docs/spec/types.md)."""

from ._shared import accepted, compile_error, rule


@rule("type-notation")
class TestTypeNotation:
    def test_a_declared_type(self):
        compile_error("(type pos real (>= 0)) (pos k -1)")
        a = accepted("(type pos real (>= 0)) (pos k 1)").get("k").value.type
        b = accepted("((real (>= 0)) k 1)").get("k").value.type
        assert (a.base, a.constraints) == (b.base, b.constraints)
