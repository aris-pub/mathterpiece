"""Conformance tests of the rule number-literals (docs/spec/lexical.md)."""

from ._shared import (
    ComplexLit,
    Fraction,
    IntLit,
    RatioLit,
    RealLit,
    items,
    pytest,
    rule,
    syntax_error,
)


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
        (got,) = items(f"(f {text})")
        assert got == node
        assert type(got) is type(node)

    def test_a_real_is_the_nearest_double(self):
        (got,) = items("(f 0.1)")
        assert got.value == 0.1

    def test_each_part_of_a_complex_number_is_a_real(self):
        (got,) = items("(f 1+2i)")
        assert isinstance(got.value.real, float) and isinstance(got.value.imag, float)

    @pytest.mark.parametrize("src", ["(f 1/0)", "(f 1/-2)", "(f 1-2)", "(f 1e)", "(f 1/2/3)"])
    def test_not_numbers(self, src):
        syntax_error(src)

    @pytest.mark.parametrize("text", ["٣", "1/٣", "١.٥", "2e٣", "x٣", "²", "1²"])
    def test_only_ascii_digits_are_digits(self, text):
        syntax_error(f"(f {text})")
