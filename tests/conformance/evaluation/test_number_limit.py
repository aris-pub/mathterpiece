"""Conformance tests of the rule number-limit (docs/spec/evaluation.md)."""

from hypothesis import example, given
from hypothesis import strategies as st

from ..support import examples
from ._shared import (
    REAL_LIMIT,
    Fraction,
    accepted,
    clamped,
    compile_error,
    mtpc,
    obj,
    pytest,
    rule,
    value,
)

LIMIT = 10**150
INTS = st.integers(-LIMIT, LIMIT)
REALS = st.floats(-REAL_LIMIT, REAL_LIMIT)


@rule("number-limit")
class TestNumberLimit:
    @examples(200)
    @example("1e151")
    @example("-1e151")
    @given(
        st.builds(
            lambda sign, m, e: f"{sign}{m}e{e}",
            st.sampled_from(["", "-"]),
            st.floats(1, 10, exclude_max=True),
            st.integers(151, 300),
        )
    )
    def test_a_real_literal_beyond_the_limit(self, lit):
        compile_error(f"(real v {lit})")

    @examples(200)
    @example(10**151)
    @given(st.integers(LIMIT + 1, 10**300).flatmap(lambda n: st.sampled_from([n, -n])))
    def test_an_int_literal_beyond_the_limit(self, n):
        compile_error(f"(int v {n})")

    def test_a_literal_at_the_limit(self):
        accepted("(real v 1e150)")
        accepted("(int v -1" + "0" * 150 + ")")

    @pytest.mark.parametrize(
        "expr, limit",
        [("(f 1e100)", 1e150), ("(f -1e100)", 1e150), ("(- (f 1e100))", -1e150)],
    )
    def test_a_real_result_is_clamped(self, expr, limit):
        assert value(f"(func f ((real x)) (* x x)) (real v {expr})", "v") == limit

    def test_a_result_beyond_the_largest_real_is_clamped(self):
        assert value("(real v (* 1e150 1e150 1e150))", "v") == 1e150

    def test_an_int_result_is_clamped_to_exactly_the_limit(self):
        assert value("(int v (* (^ 10 100) (^ 10 100)))", "v") == 10**150

    def test_a_ratio_result_is_clamped_to_exactly_the_limit(self):
        assert value("(ratio v (* (/ (^ 10 100) 3) (^ 10 100)))", "v") == 10**150

    def test_each_operation_is_clamped_on_its_own(self):
        # (^ 10 200) is clamped to 10^150 before it is divided.
        assert value("(ratio v (/ (^ 10 200) 3))", "v") == Fraction(10**150, 3)

    def test_an_int_inside_the_limit_stays_exact(self):
        assert value("(int v (+ (^ 10 149) 1))", "v") == 10**149 + 1

    @examples(300)
    @given(st.sampled_from("+-*"), INTS, INTS)
    def test_an_int_result_is_exact_then_clamped_to_exactly_the_limit(self, op, a, b):
        exact = {"+": a + b, "-": a - b, "*": a * b}[op]
        assert value(f"(int v ({op} {a} {b}))", "v") == max(-LIMIT, min(LIMIT, exact))

    @examples(300)
    @given(st.sampled_from("+-*"), REALS, REALS)
    def test_a_real_result_is_rounded_then_clamped(self, op, a, b):
        x, y = Fraction(a), Fraction(b)
        exact = {"+": x + y, "-": x - y, "*": x * y}[op]
        assert value(f"(real v ({op} {a!r} {b!r}))", "v") == clamped(exact)

    def test_an_operation_with_several_arguments_is_clamped_once(self):
        # Clamped after each product, the value would be 1e-50.
        assert value("(real v (* 1e150 1e150 1e-200))", "v") == pytest.approx(1e100)

    def test_a_starting_value_known_when_compiling_is_clamped(self):
        assert value("(real k (* 1e100 1e100))", "k") == 1e150

    def test_a_free_starting_value_is_clamped(self):
        assert obj(mtpc("(real k free@(* 1e100 1e100))"), "k")["value"]["free"] == 1e150

    def test_a_product_past_the_largest_binary64_number_is_clamped_once(self):
        # The product of the first three is past the largest binary64 number, and the exact
        # product of the four is 1e140.
        v = value("(real v (* 1e150 1e150 1e150 1e-310))", "v")
        assert v == pytest.approx(1e140)

    @pytest.mark.parametrize(
        "expr, limit",
        [
            ("(+ 1e150 1e150)", 1e150),
            ("(- -1e150 1e150)", -1e150),
            ("(/ 1 1e-200)", 1e150),
            ("(/ -1e150 1e-10)", -1e150),
            ("(^ 10.0 400)", 1e150),
            ("(^ -10.0 401)", -1e150),
            ("(^ 1e150 1.5)", 1e150),
            ("(sum {1e150 1e150})", 1e150),
            ("(abs 1e150+1e150i)", 1e150),
        ],
    )
    def test_each_operation_is_clamped(self, expr, limit):
        assert value(f"(real v {expr})", "v") == limit

    @pytest.mark.parametrize(
        "expr, limit",
        [
            ("(exp 1000)", 1e150),
            ("(rad 1e150)", 1e150),
            ("(turn -1e150)", -1e150),
            ("(dist [-1e150 0] [1e150 0])", 1e150),
            ("(lerp 0 1e150 1e150)", 1e150),
        ],
    )
    def test_each_built_in_function_is_clamped(self, expr, limit):
        assert value(f"(real v {expr})", "v") == limit

    def test_an_exact_power_is_clamped_to_exactly_the_limit(self):
        assert value("(int v (^ 10 1000))", "v") == 10**150
        assert value("(int v (^ -10 1001))", "v") == -(10**150)

    def test_a_power_with_a_very_large_exponent(self):
        # The exact value has more than 10^100 digits, so it is never worked out.
        assert value("(int v (^ 2 (^ 10 100)))", "v") == 10**150
        assert value("(int v (^ -3 (+ (^ 10 100) 1)))", "v") == -(10**150)

    def test_each_part_of_a_complex_is_clamped(self):
        assert value("(complex v (* 1e100+1e100i 1e100))", "v") == complex(1e150, 1e150)
        assert value("(complex v (^ 1e150+0i 3))", "v") == complex(1e150, 0)

    def test_each_number_of_a_point_or_a_list_is_clamped(self):
        assert value("(point v (* [1e100 -1e100] 1e100))", "v") == (1e150, -1e150)
        assert value("(list[real] v (+ {1e150 1} {1e150 1}))", "v") == [1e150, 2]
        assert value("(point v (polar 1e150 45))", "v") == pytest.approx(
            (1e150 / 2**0.5, 1e150 / 2**0.5)
        )

    def test_a_product_of_ints_with_no_bounds_is_an_int(self):
        accepted("(int n 1) (int v (* n n n))")
