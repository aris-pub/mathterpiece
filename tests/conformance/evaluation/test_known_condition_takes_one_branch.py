"""Conformance tests of the rule known-condition-takes-one-branch (docs/spec/evaluation.md)."""

from ._shared import WHOLE_FORMS, compile_error, rule, value


@rule("known-condition-takes-one-branch")
class TestKnownConditionTakesOneBranch:
    X = "(real x 0 (const))\n"

    def test_if(self):
        assert value(self.X + "(real a (if (= x 0) 0 (/ 1 x)))", "a") == 0

    @WHOLE_FORMS
    def test_cond(self):
        assert value(self.X + "(real b (cond ((= x 0) 0) (else (/ 1 x))))", "b") == 0

    @WHOLE_FORMS
    def test_and(self):
        assert value(self.X + "(bool c (and (> x 0) (> (/ 1 x) 2)))", "c") is False

    def test_let_is_proved_whole(self):
        compile_error(self.X + "(real d (let ((u (/ 1 x))) 0))")

    def test_or_default_is_proved_whole(self):
        compile_error("(real v (or? 2 (/ 1 0)))")

    def test_the_branch_not_taken_is_not_proved(self):
        assert value(self.X + "(real e (if (= x 0) 0 'not a number'))", "e") == 0

    def test_in_a_foreach_both_branches_are_proved(self):
        compile_error("(scene s (foreach i 2 (circle_ (r (if (= i 0) 1 'a')))))")
