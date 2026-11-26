"""Conformance tests of the rule correctly-rounded-reals (docs/spec/evaluation.md)."""

import math
from decimal import Context, Decimal

from hypothesis import example, given
from hypothesis import strategies as st

from ..support import examples
from ._shared import ROUNDED, Fraction, clamped, pytest, rule, value, xfail

REALS = st.floats(-1e50, 1e50)

# Decimal works to 60 digits, so that turning its result into a float rounds only once in effect.
PRECISE = Context(prec=60)

# Python's sum makes up for rounding errors, but does not always give the nearest binary64 number.
COMPENSATED = "the compiler adds with Python's sum, which does not round once"


def literals(xs) -> str:
    return " ".join(map(repr, xs))


@rule("correctly-rounded-reals")
class TestCorrectlyRoundedReals:
    @examples(300)
    @example("+", 0.1, 0.2)
    @given(st.sampled_from("+-*"), REALS, REALS)
    def test_the_basic_operations(self, op, a, b):
        x, y = Fraction(a), Fraction(b)
        exact = {"+": x + y, "-": x - y, "*": x * y}[op]
        assert value(f"(real v ({op} {a!r} {b!r}))", "v") == clamped(exact)

    @examples(300)
    @example(1.0, 3.0)
    @given(REALS, REALS.filter(lambda b: b != 0))
    def test_division(self, a, b):
        assert value(f"(real|none v (/ {a!r} {b!r}))", "v") == clamped(Fraction(a) / Fraction(b))

    @examples(300)
    @example(2.0)
    @given(st.floats(0, 1e50))
    def test_sqrt(self, x):
        assert value(f"(real v (sqrt {x!r}))", "v") == float(Decimal(x).sqrt(PRECISE))

    @xfail("mtp-ydd4.7.38", f"{COMPENSATED}: (+ 1.0 9007199254740992.0 1e-300) is 2^53")
    @examples(300)
    @example([1.0, 9007199254740992.0, 1e-300])
    @given(st.lists(REALS, min_size=3, max_size=4))
    def test_a_sum_of_several_reals_is_rounded_once(self, xs):
        assert value(f"(real v (+ {literals(xs)}))", "v") == clamped(sum(map(Fraction, xs)))

    @xfail(
        "mtp-ydd4.7.38",
        "a product of several reals rounds after each step: (* 147.0 61273464317967.0 3.0) is "
        "27021597764223444",
    )
    @examples(300)
    @example([147.0, 61273464317967.0, 3.0])
    @given(st.lists(REALS, min_size=3, max_size=4))
    def test_a_product_of_several_reals_is_rounded_once(self, xs):
        assert value(f"(real v (* {literals(xs)}))", "v") == clamped(math.prod(map(Fraction, xs)))

    def test_sum_rounds_once(self):
        # The exact sum of the three doubles rounds to 0.6, while adding them one at a time gives
        # 0.6000000000000001.
        assert value("(real v (sum {0.1 0.2 0.3}))", "v") == 0.6

    # math.fsum gives the exact sum of floats, rounded once.
    @xfail(
        "mtp-ydd4.7.38",
        f"{COMPENSATED}: (sum {{1.0 9007199254740992.0 1e-300}}) is 2^53",
    )
    @examples(300)
    @example([1.0, 9007199254740992.0, 1e-300])
    @given(st.lists(REALS, min_size=1, max_size=6))
    def test_sum_of_any_reals_rounds_once(self, xs):
        assert value(f"(real v (sum {{{literals(xs)}}}))", "v") == math.fsum(xs)

    @ROUNDED
    @pytest.mark.parametrize("expr, exact", [("(sind 30)", 0.5), ("(cosd 60)", 0.5)])
    def test_the_functions_in_degrees(self, expr, exact):
        assert value(f"(real v {expr})", "v") == exact

    @examples(100)
    @given(st.sampled_from(["sind", "cosd"]), st.integers(-(10**6), 10**6))
    def test_the_functions_in_degrees_are_exact_at_multiples_of_90(self, f, k):
        exact = {"sind": [0.0, 1.0, 0.0, -1.0], "cosd": [1.0, 0.0, -1.0, 0.0]}[f][k % 4]
        assert value(f"(real v ({f} {90 * k}))", "v") == exact

    @xfail(
        "mtp-ydd4.7.38",
        "exp is not correctly rounded: (exp 4.061178123878948) is 58.042652248484174, and the "
        "exact value rounds to 58.04265224848418",
    )
    @examples(300)
    @example(4.061178123878948)
    @given(st.floats(-300, 300))
    def test_exp(self, x):
        assert value(f"(real v (exp {x!r}))", "v") == float(Decimal(x).exp(PRECISE))

    @xfail(
        "mtp-ydd4.7.38",
        "log is not correctly rounded: (log 1.542718478221884) is 0.43354610580928377, and the "
        "exact value rounds to 0.4335461058092838",
    )
    @examples(300)
    @example(1.542718478221884)
    @given(st.floats(0, 1e50, exclude_min=True))
    def test_log(self, x):
        assert value(f"(real|none v (log {x!r}))", "v") == float(Decimal(x).ln(PRECISE))
