"""Conformance tests of the rule functions (docs/spec/data-model.md)."""

from ._shared import accepted, rule


@rule("functions")
class TestFunctions:
    def test_a_declared_function_is_called(self):
        m = accepted("(func twice ((real x)) (* 2 x)) (real v (twice 2) (const))")
        assert m.get("v").value.value == 4
