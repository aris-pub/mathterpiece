"""Conformance tests of the rule none-never-a-condition (docs/spec/evaluation.md)."""

from ._shared import INVERSE, compile_error, pytest, rule


@rule("none-never-a-condition")
class TestNoneNeverACondition:
    def test_the_condition_of_an_if(self):
        compile_error("(bool|none c none) (real v (if c 1 2))")

    def test_active(self):
        compile_error(
            "(bool|none c none) (real k 0)"
            " (button b (active c) (animation (move k (to 1) (duration 1))))"
        )

    @pytest.mark.parametrize("f", ["sum", "min", "max", "count"])
    def test_the_items_of_a_collection_function(self, f):
        compile_error(INVERSE + f"(real v ({f} {{1 (f 0)}}))")
