"""Conformance tests of the rule forms-with-no-name (docs/spec/grammar.md)."""

from ._shared import accepted, compile_error, rule


@rule("forms-with-no-name")
class TestFormsWithNoName:
    def test_the_second_item_of_a_move_is_its_target(self):
        accepted("(real k 0) (button b (animation (move k (to 1) (duration 1))))")

    def test_a_listener_has_no_name(self):
        accepted("(scene s (circle c (r 1))) (canvas v s (on-click c))")

    def test_a_view_always_has_a_name(self):
        compile_error("(scene s (circle c (r 1))) (canvas_ s)")

    def test_a_control_always_has_a_name(self):
        compile_error("(real k 0 (>= 0) (<= 1)) (slider_ (move k (from 0) (to 1)))")
