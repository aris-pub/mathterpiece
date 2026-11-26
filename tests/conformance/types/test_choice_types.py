"""Conformance tests of the rule choice-types (docs/spec/types.md)."""

from ._shared import CHOICES, accepted, compile_error, rule


@rule("choice-types")
class TestChoiceTypes:
    SIDE = "(type side string (one-of 'left' 'right')) "

    def test_a_choice(self):
        accepted(self.SIDE + "(side v 'left')")

    def test_a_value_that_is_not_a_choice(self):
        compile_error(self.SIDE + "(side v 'up')")

    @CHOICES
    def test_a_free_string_is_not_proved_to_be_a_choice(self):
        compile_error(self.SIDE + "(string q 'left') (side v q)")
