"""Conformance tests of the rule number-types (docs/spec/evaluation.md)."""

from ._shared import Fraction, compile_error, mtpc, obj, rule, value


@rule("number-types")
class TestNumberTypes:
    def test_an_int_is_exact(self):
        assert value("(int v (+ (^ 2 60) 1))", "v") == 2**60 + 1

    def test_a_ratio_is_exact(self):
        assert value("(ratio v (+ (/ 1 10) 1/5))", "v") == Fraction(3, 10)

    def test_the_mtpc_writes_a_ratio_in_lowest_terms(self):
        d = mtpc("(ratio v 2/4)")
        assert obj(d, "v")["value"]["free"] == [1, 2]

    def test_a_real_is_a_double(self):
        assert value("(real v (+ 0.1 0.2))", "v") == 0.1 + 0.2

    def test_a_complex_is_two_doubles(self):
        assert value("(complex v (* 1+2i 2))", "v") == complex(2, 4)

    def test_a_real_is_finite_so_there_is_no_constant_for_infinity(self):
        compile_error("(real v infty)")
