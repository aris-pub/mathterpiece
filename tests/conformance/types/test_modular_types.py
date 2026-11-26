"""Conformance tests of the rule modular-types (docs/spec/types.md)."""

from hypothesis import example, given
from hypothesis import strategies as st

from ..support import examples
from ._shared import TYPES_REDESIGN, accepted, compile_error, pytest, rule

INTS = st.integers(-1000, 1000)
NO_MODULAR_TYPES = pytest.mark.xfail(
    strict=True,
    reason="mtp-rk1i: the compiler has no modular types, so ((mod int 0 1) h 0 (const)) is a "
    "compile error",
)


def wrapped(v: int, lo: int, hi: int) -> int:
    return lo + (v - lo) % (hi - lo)


@rule("modular-types")
class TestModularTypes:
    @TYPES_REDESIGN
    def test_a_modular_type_brings_a_value_in(self):
        m = accepted("((mod real 0 360) theta 400 (const))")
        assert m.get("theta").value.value == 40

    @TYPES_REDESIGN
    def test_a_modular_type_takes_no_comparison(self):
        accepted("((mod real 0 360) theta 10)")
        compile_error("((mod real 0 360) theta 10) (bool v (< theta 90))")

    @NO_MODULAR_TYPES
    @examples(50)
    @example(0, 1, 0, 0)
    @given(INTS, st.integers(1, 100), INTS, INTS)
    def test_a_received_number_and_a_sum_wrap(self, lo, width, v, n):
        hi = lo + width
        m = accepted(f"((mod int {lo} {hi}) h {v} (const)) (int u (unwrap (+ h {n})))")
        assert m.get("h").value.value == wrapped(v, lo, hi)
        assert m.get("u").value.value == wrapped(wrapped(v, lo, hi) + n, lo, hi)
