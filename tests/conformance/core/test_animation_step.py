"""Conformance tests of the rule animation-step (docs/spec/core.md)."""

from ._shared import ANIMATION_STEP, accepted, rule


@rule("animation-step")
class TestAnimationStep:
    @ANIMATION_STEP
    def test_an_animation_as_a_step(self):
        accepted(
            "(real k 0) (animation a (move k (to 1) (duration 1))"
            " (animation (loop 2) (move k (to 2) (duration 1))))"
        )
