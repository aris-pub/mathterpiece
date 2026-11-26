"""Conformance tests of the rule forms-evaluate-some-parts (docs/spec/evaluation.md)."""

from ._shared import INVERSE, Fraction, rule, value


@rule("forms-evaluate-some-parts")
class TestFormsEvaluateSomeParts:
    def test_if_evaluates_only_the_branch_taken(self):
        assert value(INVERSE + "(real v (if (= 1 1) 3 (f 0)))", "v") == 3

    def test_or_default_evaluates_the_default_only_for_none(self):
        assert value(INVERSE + "(real v (or? (f 0) 5))", "v") == 5
        assert value(INVERSE + "(real v (or? (f 2) 5))", "v") == Fraction(1, 2)

    def test_a_let_value_that_nothing_reads_is_not_evaluated(self):
        # u would be none at x = 0, but nothing reads it, so v is 0 and not none.
        assert value("(real x 0 (>= -1) (<= 1)) (real v (let ((u (/ 1 x))) 0))", "v") == 0

    def test_fn_evaluates_nothing_until_it_is_called(self):
        src = "(func[real] g ((func[real real] h)) (h 2))"
        assert value(src + " (real v (g (fn ((real x)) (* x 3))))", "v") == 6
