"""Conformance tests of the rule prover-finds-ranges (docs/spec/compiler-runtime.md)."""

import math

from hypothesis import given
from hypothesis import strategies as st

from ..support import examples, value
from ._shared import REJECTION, accepted, compile_error, mtpc, obj, pytest, rule

# An expression of K, which stands for the variable k or for one value of it.
EXPRESSIONS = st.recursive(
    st.one_of(st.just("K"), st.floats(-10, 10).map(repr)),
    lambda inner: st.one_of(
        st.builds(lambda op, a, b: f"({op} {a} {b})", st.sampled_from("+-*"), inner, inner),
        inner.map(lambda a: f"(abs {a})"),
    ),
    max_leaves=6,
)


def checked(src: str) -> bool:
    """Some step rejects the source, or the .mtpc holds a check for v."""
    try:
        slot = obj(mtpc(src), "v")["value"]
    except REJECTION:
        return True
    return "bound" in slot and slot["bound"][0] == "check"


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

    # The value of the expression at one value k0 of k lies in its range. So a condition that
    # this value breaks does not hold on the whole range, and is never proved.
    @examples(200)
    @given(EXPRESSIONS, st.floats(-10, 10), st.floats(0, 10), st.floats(0, 1))
    def test_a_condition_broken_at_one_value_is_never_proved(self, expr, lo, width, t):
        hi = lo + width
        k0 = min(max(lo + t * width, lo), hi)
        at = value(f"(real v {expr.replace('K', repr(k0))})", "v")
        k = f"(real k {lo!r} (>= {lo!r}) (<= {hi!r}))"
        e = expr.replace("K", "k")
        assert checked(f"{k} (real|none v {e} (<= {math.nextafter(at, -math.inf)!r}))")
        assert checked(f"{k} (real|none v {e} (>= {math.nextafter(at, math.inf)!r}))")
