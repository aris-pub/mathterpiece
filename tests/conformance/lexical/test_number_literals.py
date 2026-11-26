"""Conformance tests of the rule number-literals (docs/spec/lexical.md)."""

from hypothesis import example, given

from ._shared import (
    DIGITS,
    INTS,
    REALS,
    SIGNS,
    ComplexLit,
    Fraction,
    IntLit,
    RatioLit,
    RealLit,
    examples,
    items,
    pytest,
    rule,
    st,
    syntax_error,
    unsigned_reals,
)


def read(text: str):
    (got,) = items(f"(f {text})")
    return got


@rule("number-literals")
class TestNumberLiterals:
    @pytest.mark.parametrize(
        "text, node",
        [
            ("3", IntLit(3)),
            ("007", IntLit(7)),
            ("+4", IntLit(4)),
            ("-12", IntLit(-12)),
            ("123456789012345678901234567890", IntLit(123456789012345678901234567890)),
            ("1/3", RatioLit(Fraction(1, 3))),
            ("-2/4", RatioLit(Fraction(-1, 2))),
            ("2.5", RealLit(2.5)),
            ("1.", RealLit(1.0)),
            (".5", RealLit(0.5)),
            ("1e3", RealLit(1000.0)),
            ("1.5E-3", RealLit(0.0015)),
            ("2i", ComplexLit(2j)),
            ("-1.5e3i", ComplexLit(-1500j)),
            ("1+2i", ComplexLit(1 + 2j)),
            ("-1e+2-3.5i", ComplexLit(-100 - 3.5j)),
        ],
    )
    def test_each_kind_of_number(self, text, node):
        got = read(text)
        assert got == node
        assert type(got) is type(node)

    @examples(300)
    @given(INTS)
    def test_an_int_of_any_size(self, text):
        got = read(text)
        assert type(got) is IntLit
        assert got.value == int(text)

    @examples(300)
    @given(SIGNS, DIGITS, DIGITS.filter(lambda d: int(d) != 0))
    def test_a_ratio_is_reduced_with_the_sign_on_the_numerator(self, sign, n, d):
        got = read(f"{sign}{n}/{d}")
        assert type(got) is RatioLit
        assert got.value == Fraction(int(sign + n), int(d))

    @examples(100)
    @given(SIGNS, DIGITS, st.integers(1, 3))
    def test_a_denominator_of_0_is_an_error(self, sign, n, zeros):
        syntax_error(f"(f {sign}{n}/{'0' * zeros})")

    # Python's float() gives the binary64 number nearest to a decimal.
    @examples(300)
    @example("0.1")
    @given(REALS)
    def test_a_real_is_the_nearest_binary64_number(self, text):
        got = read(text)
        assert type(got) is RealLit
        assert got.value == float(text)

    @examples(300)
    @given(SIGNS, unsigned_reals(plain=True))
    def test_an_imaginary_number_has_real_part_0(self, sign, text):
        got = read(f"{sign}{text}i")
        assert type(got) is ComplexLit
        assert got.value == complex(0, float(sign + text))

    @examples(300)
    @given(SIGNS, unsigned_reals(plain=True), st.sampled_from("+-"), unsigned_reals(plain=True))
    def test_each_part_of_a_complex_number_is_read_as_a_real(self, sign, re, sign_im, im):
        got = read(f"{sign}{re}{sign_im}{im}i")
        assert type(got) is ComplexLit
        assert got.value == complex(float(sign + re), float(sign_im + im))

    def test_each_part_of_a_complex_number_is_a_real(self):
        got = read("1+2i")
        assert isinstance(got.value.real, float) and isinstance(got.value.imag, float)

    @pytest.mark.parametrize("src", ["(f 1/0)", "(f 1/-2)", "(f 1-2)", "(f 1e)", "(f 1/2/3)"])
    def test_not_numbers(self, src):
        syntax_error(src)

    @pytest.mark.parametrize("text", ["٣", "1/٣", "١.٥", "2e٣", "x٣", "²", "1²"])
    def test_only_ascii_digits_are_digits(self, text):
        syntax_error(f"(f {text})")
