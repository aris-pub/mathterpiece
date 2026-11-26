"""Conformance tests of the rule rounding (docs/spec/evaluation.md)."""

from decimal import ROUND_HALF_UP, Context, Decimal

from hypothesis import assume, example, given
from hypothesis import strategies as st

from ..support import examples
from ._shared import ROUND, pytest, rule, value

# Below 10^28, where today's compiler stops (mtp-6yga, tested below).
REALS = st.one_of(
    st.floats(-1e27, 1e27),
    st.integers(-(10**6), 10**6).map(lambda n: n + 0.5),
    st.decimals(-1000, 1000, places=3, allow_nan=False, allow_infinity=False).map(float),
)
PLACES = st.integers(0, 6)


def rounded(x: float, places: int) -> Decimal:
    """x rounded to a number of places, halves away from zero, on its shortest decimal form."""
    exact = Context(prec=400)
    return Decimal(repr(x)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP, exact)


def decimal_places(x: float) -> int:
    """The number of digits after the point in the shortest decimal form of x."""
    return max(-Decimal(repr(x)).as_tuple().exponent, 0)


@rule("rounding")
class TestRounding:
    @examples(300)
    @example(2.5)
    @example(-2.5)
    @example(0.5)
    @example(1.4)
    @example(-0.5)
    @given(REALS)
    def test_round_halves_away_from_zero(self, x):
        assert value(f"(int v (round {x!r}))", "v") == int(rounded(x, 0))

    @examples(300)
    @example(0.125, 2)
    @example(2.675, 2)
    @given(REALS.filter(lambda x: abs(x) < 1e15), PLACES)
    def test_round_to_decimal_places_on_the_shortest_decimal_form(self, x, places):
        assert value(f"(real v (round {x!r} {places}))", "v") == float(rounded(x, places))

    # Whether a zero keeps its sign is not part of this rule, so a result of zero is left out.
    @examples(300)
    @example(0.125, 2)
    @example(2.675, 2)
    @example(2.5, 0)
    @given(REALS.filter(lambda x: abs(x) < 1e15), PLACES)
    def test_a_format_spec(self, x, places):
        assume(places <= decimal_places(x) and rounded(x, places) != 0)
        got = value(f"(string v f'{{{x!r}:.{places}f}}')", "v")
        assert got == str(rounded(x, places))

    @pytest.mark.xfail(
        strict=True,
        reason="no bead: a format spec with more places than the shortest decimal form shows the "
        "digits of the binary value, so f'{549755813888.4688:.5f}' is 549755813888.46875",
    )
    @examples(100)
    @example(549755813888.4688, 5)
    @given(REALS.filter(lambda x: abs(x) < 1e15), PLACES)
    def test_a_format_spec_with_more_places_than_the_shortest_decimal_form(self, x, places):
        assume(places > decimal_places(x))
        got = value(f"(string v f'{{{x!r}:.{places}f}}')", "v")
        assert got == str(rounded(x, places))

    @ROUND
    def test_round_gives_none_at_no_input(self):
        assert value("(real v (round 1e28))", "v") == 1e28
