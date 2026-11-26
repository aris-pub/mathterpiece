"""Conformance tests of the rule correctly-rounded-reals (docs/spec/evaluation.md)."""

from ._shared import ROUNDED, pytest, rule, value


@rule("correctly-rounded-reals")
class TestCorrectlyRoundedReals:
    @pytest.mark.parametrize(
        "expr, exact",
        [("(+ 0.1 0.2)", 0.30000000000000004), ("(sqrt 2)", 2**0.5), ("(/ 1 3.0)", 1 / 3)],
    )
    def test_the_basic_operations(self, expr, exact):
        assert value(f"(real v {expr})", "v") == exact

    @ROUNDED
    @pytest.mark.parametrize("expr, exact", [("(sind 30)", 0.5), ("(cosd 60)", 0.5)])
    def test_the_functions_in_degrees(self, expr, exact):
        assert value(f"(real v {expr})", "v") == exact

    def test_sum_rounds_once(self):
        # The exact sum of the three doubles rounds to 0.6, while adding them one at a time gives
        # 0.6000000000000001.
        assert value("(real v (sum {0.1 0.2 0.3}))", "v") == 0.6
