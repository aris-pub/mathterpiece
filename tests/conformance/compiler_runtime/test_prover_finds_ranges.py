"""Conformance tests of the rule prover-finds-ranges (docs/spec/compiler-runtime.md)."""

from ._shared import accepted, compile_error, mtpc, obj, pytest, rule


@rule("prover-finds-ranges")
class TestProverFindsRanges:
    @pytest.mark.parametrize("src", ["(scene s (circle c (r (- 1 2))))", "(real v (/ 1 0))"])
    def test_a_range_outside_the_constraint(self, src):
        compile_error(src)

    def test_a_range_inside_the_constraint(self):
        accepted("(real k 1 (>= 0) (<= 2)) (scene s (circle c (r (* 2 k))))")

    def test_a_bound_value_whose_range_may_break_its_constraint_gets_a_check(self):
        d = mtpc("(real k 1 (>= 0) (<= 2)) (real|none v (* 2 k) (<= 3))")
        assert obj(d, "v")["value"]["bound"][0] == "check"

    def test_a_bound_value_whose_range_lies_inside_gets_no_check(self):
        d = mtpc("(real k 1 (>= 0) (<= 1)) (real|none v (* 2 k) (<= 3))")
        assert obj(d, "v")["value"]["bound"][0] != "check"
