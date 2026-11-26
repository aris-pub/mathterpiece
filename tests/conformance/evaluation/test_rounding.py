"""Conformance tests of the rule rounding (docs/spec/evaluation.md)."""

from ._shared import ROUND, pytest, rule, value


@rule("rounding")
class TestRounding:
    @pytest.mark.parametrize(
        "x, r", [("2.5", 3), ("-2.5", -3), ("0.5", 1), ("1.4", 1), ("-0.5", -1)]
    )
    def test_round_halves_away_from_zero(self, x, r):
        assert value(f"(int v (round {x}))", "v") == r

    def test_round_to_decimal_places_on_the_shortest_decimal_form(self):
        assert value("(real v (round 0.125 2))", "v") == 0.13
        assert value("(real v (round 2.675 2))", "v") == 2.68

    def test_a_format_spec(self):
        assert value("(string v f'{0.125:.2f} {2.675:.2f} {2.5:.0f}')", "v") == "0.13 2.68 3"

    @ROUND
    def test_round_gives_none_at_no_input(self):
        assert value("(real v (round 1e28))", "v") == 1e28
