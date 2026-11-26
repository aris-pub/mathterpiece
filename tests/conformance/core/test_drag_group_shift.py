"""Conformance tests of the rule drag-group-shift (docs/spec/core.md)."""

from ._shared import DRAG_SHIFT, accepted, compile_error, rule


@rule("drag-group-shift")
class TestDragGroupShift:
    @DRAG_SHIFT
    def test_a_group_is_dragged_by_its_shift(self):
        accepted("(scene s (group g (circle c (r 1)))) (canvas v s (on-drag g g.shift))")

    @DRAG_SHIFT
    def test_a_drag_of_the_pos_of_a_group_is_an_error(self):
        accepted("(scene s (group g (circle c (r 1)))) (canvas v s (on-drag g g.shift))")
        compile_error("(scene s (group g (circle c (r 1)))) (canvas v s (on-drag g g.pos))")
