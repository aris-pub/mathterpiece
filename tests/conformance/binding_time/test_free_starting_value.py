"""Conformance tests of the rule free-starting-value (docs/spec/binding-time.md)."""

from ._shared import accepted, free, is_bound, mtpc, rule, same_meaning


@rule("free-starting-value")
class TestFreeStartingValue:
    def test_a_start_known_when_compiling_is_folded(self):
        d = mtpc("(real c 3 (const)) (real r free@(* 2 c))")
        assert free(d, "r") == 6

    def test_the_container_is_free_and_a_writer_may_write_to_it(self):
        accepted(
            "(real c 3 (const)) (real r free@(* 2 c))"
            " (slider sl (animation (move r (from 0) (to 1) (duration 0))))"
        )
        accepted(
            "(real a 1) (real r free@(* 2 a))"
            " (slider sl (animation (move r (from 0) (to 1) (duration 0))))"
        )

    def test_a_start_known_only_while_drawing_is_not_bound(self):
        assert not is_bound("(real a 1) (real v free@(* 2 a))", "v")
        assert not is_bound("(import rand rand) (rand-seed sd 1) (real v free@(rand 0 1))", "v")

    def test_free_at_is_the_form_free(self):
        same_meaning("(real a 1) (real v free@(* 2 a))", "(real a 1) (real v (free (* 2 a)))")
