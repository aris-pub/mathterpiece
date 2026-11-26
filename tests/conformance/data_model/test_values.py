"""Conformance tests of the rule values (docs/spec/data-model.md)."""

from ._shared import accepted, rule


@rule("values")
class TestValues:
    def test_equal_values_are_the_same_value(self):
        m = accepted("(real v (+ 1 2) (const)) (real w 3 (const))")
        assert m.get("v").value.value == m.get("w").value.value == 3
