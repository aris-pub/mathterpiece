"""Conformance tests of the rule evaluation-is-pure (docs/spec/evaluation.md)."""

from ._shared import mtpc, obj, rule


@rule("evaluation-is-pure")
class TestEvaluationIsPure:
    def test_reading_a_value_changes_nothing(self):
        d = mtpc("(real a 1) (real b (+ a 1)) (real c (+ a 1))")
        assert obj(d, "a")["value"]["free"] == 1
        assert obj(d, "b")["value"]["bound"] == obj(d, "c")["value"]["bound"]

    def test_a_folded_call_changes_no_variable(self):
        d = mtpc("(real a 1) (func f ((real x)) (* 2 x)) (real v (f 3))")
        assert obj(d, "a")["value"]["free"] == 1
        assert obj(d, "v")["value"]["free"] == 6
