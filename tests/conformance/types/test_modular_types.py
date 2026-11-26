"""Conformance tests of the rule modular-types (docs/spec/types.md)."""

from ._shared import TYPES_REDESIGN, accepted, compile_error, rule


@rule("modular-types")
class TestModularTypes:
    @TYPES_REDESIGN
    def test_a_modular_type_brings_a_value_in(self):
        m = accepted("((mod real 0 360) theta 400 (const))")
        assert m.get("theta").value.value == 40

    @TYPES_REDESIGN
    def test_a_modular_type_takes_no_comparison(self):
        accepted("((mod real 0 360) theta 10)")
        compile_error("((mod real 0 360) theta 10) (bool v (< theta 90))")
