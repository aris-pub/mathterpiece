"""Conformance tests of the rule what-a-name-means (docs/spec/evaluation.md)."""

from ._shared import accepted, compile_error, rule, value


@rule("what-a-name-means")
class TestWhatANameMeans:
    def test_a_name_in_an_expression_gives_the_value_that_it_holds(self):
        assert value("(real a 3 (const)) (real v (* 2 a))", "v") == 6

    def test_a_name_as_a_target_means_the_container(self):
        target = "(slider s (animation (move a (from 0) (to 1) (duration 0))))"
        accepted("(real a 1) " + target)
        # A const container cannot be written to, so the name as a target is refused.
        compile_error("(real a 1 (const)) " + target)
