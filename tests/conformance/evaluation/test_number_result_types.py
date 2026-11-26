"""Conformance tests of the rule number-result-types (docs/spec/evaluation.md)."""

from ._shared import pytest, rule, value


@rule("number-result-types")
class TestNumberResultTypes:
    @pytest.mark.parametrize(
        "expr, kind",
        [
            ("(+ 1 2)", "int"),
            ("(+ 1 1/2)", "ratio"),
            ("(+ 1 0.5)", "real"),
            ("(+ 1/2 0.5)", "real"),
            ("(+ 1 1i)", "complex"),
            ("(/ 1 2)", "ratio"),
            ("(^ 2 3)", "int"),
            ("(^ 2 -1)", "ratio"),
            ("(^ 2 0.5)", "real"),
            ("(^ 2 1i)", "complex"),
            ("(abs 3+4i)", "real"),
        ],
    )
    def test_the_type_of_a_result(self, expr, kind):
        assert value(f"(string v (type-of {expr}))", "v") == kind

    def test_a_power_whose_range_holds_a_negative_int(self):
        assert value("(int n 2 (>= 0) (<= 4)) (string v (type-of (^ 2 n)))", "v") == "int"
        assert value("(int n 2 (>= -1) (<= 4)) (string v (type-of (^ 2 n)))", "v") == "ratio"

    def test_an_int_is_converted_to_the_nearest_real_ties_to_even(self):
        assert value("(real v (+ 9007199254740993 0.0))", "v") == 9007199254740992.0
        assert value("(real v (+ 9007199254740995 0.0))", "v") == 9007199254740996.0
