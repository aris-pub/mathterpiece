"""Conformance tests of the rule equality-operands (docs/spec/evaluation.md)."""

from ._shared import EQUAL_FUNCTIONS, accepted, compile_error, pytest, rule, value


@rule("equality-operands")
class TestEqualityOperands:
    def test_a_point_and_a_list_of_ints(self):
        compile_error("(point p [1 2] (const)) (list[int] xs {1 2} (const)) (bool v (= p xs))")

    def test_a_literal_list_takes_the_type_of_the_other_side(self):
        assert value("(point p [1 2] (const)) (bool v (= p [1 2]))", "v") is True

    def test_two_types_that_do_not_fit(self):
        compile_error("(bool v (= 1 'a'))")

    def test_one_side_is_none(self):
        accepted("(real k 1) (bool v (= k none))")

    @EQUAL_FUNCTIONS
    @pytest.mark.parametrize(
        "src",
        [
            "(bool v (= sind sind))",
            "(real k 0) (transition t k (to 1) (duration 1)) (bool v (= t t))",
            "(bool v (!= {sind} {cosd}))",
        ],
    )
    def test_functions_transitions_and_animations(self, src):
        compile_error(src)
