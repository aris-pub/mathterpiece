"""Conformance tests of the rule what-reads-what (docs/spec/binding-time.md)."""

from ._shared import PAGE_READ, SLIDER, accepted, compile_error, rule


@rule("what-reads-what")
class TestWhatReadsWhat:
    def test_every_expression_may_read_the_scene(self):
        accepted("(scene s (circle c (r 1))) (real v c.r) (readout ro f'{c.r}')")

    def test_every_expression_may_read_a_formula(self):
        accepted("(formula f $'\\term{a}{x}' (term a (fill #'red'))) (color|none v f.a.fill)")

    def test_a_view_or_a_control_may_read_a_control(self):
        accepted("(real size 1) " + SLIDER + " (readout ro f'{sz.position}')")
        accepted(
            "(real size 1) " + SLIDER + " (real k 0)"
            " (button b (animation (move k (to 1) (duration 1))) (active (> sz.position 1)))"
        )

    def test_the_scene_may_not_read_a_control(self):
        compile_error("(real size 1) " + SLIDER + " (scene s (circle c (r sz.position)))")

    @PAGE_READ
    def test_a_variable_at_the_top_level_may_not_read_a_control(self):
        compile_error("(real size 1) " + SLIDER + " (real r (if (> sz.position 2) 2 1))")
