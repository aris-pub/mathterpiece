"""Conformance tests of the rule the-types (docs/spec/types.md)."""

from ._shared import BEZIER, EASE, UNIT, accepted, compile_error, rule, same_meaning


@rule("the-types")
class TestTheTypes:
    def test_the_type_colormap(self):
        same_meaning(
            "(func f ((colormap m)) (m 0.5)) (colormap cm {#'red' #'blue'}) (color v (f cm))",
            "(func f ((func[real color] m)) (m 0.5)) (colormap cm {#'red' #'blue'})"
            " (color v (f cm))",
        )

    @UNIT
    def test_unit_is_a_built_in_type(self):
        compile_error("(unit k 2)")
        accepted("(unit k 0.5)")

    @EASE
    def test_ease_is_a_built_in_type(self):
        accepted("(ease e (fn ((unit t)) t))")

    @BEZIER
    def test_bezier_is_a_shape_type(self):
        accepted("(scene s (bezier b (from [0 0]) (to [1 1])))")

    @BEZIER
    def test_curve_is_a_built_in_type(self):
        accepted("(curve c (fn ((real t)) [t t]))")
