"""Conformance tests of the rule equality-by-content (docs/spec/evaluation.md)."""

from hypothesis import assume, given
from hypothesis import strategies as st

from ..support import examples
from ._shared import INVERSE, Fraction, pytest, rule, value

VALUES = st.one_of(
    st.integers(-(10**20), 10**20).map(Fraction),
    st.fractions(max_denominator=12),
    st.floats(-1e20, 1e20).map(Fraction),
    st.sampled_from([0, 1, -1]).map(Fraction),
)


def literals(v: Fraction) -> list[str]:
    """Each literal that is exactly the number v: an int, a ratio, a real and a complex."""
    texts = [f"{v.numerator}/{v.denominator}"]
    if v.denominator == 1:
        texts.append(str(v.numerator))
    if Fraction(float(v)) == v:
        texts += [repr(float(v)), f"{float(v)!r}+0i"]
    if v == 0:
        texts.append("-0.0")
    return texts


def number(v: Fraction):
    return st.sampled_from(literals(v))


# The characters that a string literal holds as they are, and the three escapes.
CHARACTERS = st.one_of(
    st.characters(min_codepoint=0x20, max_codepoint=0x7E, exclude_characters="'\\"),
    st.sampled_from(["\\'", "\\\\", "\\n"]),
)
STRINGS = st.lists(CHARACTERS, max_size=4).map("".join)


@rule("equality-by-content")
class TestEqualityByContent:
    @pytest.mark.parametrize(
        "a, b, result",
        [
            ("0", "-0.0", True),
            ("1", "1.0", True),
            ("1/2", "0.5", True),
            ("1+0i", "1.0", True),
            ("1+2i", "1+2i", True),
            ("(+ 0.1 0.2)", "0.3", False),
            ("'a'", "'a'", True),
            ("'a'", "'A'", False),
            ("true", "true", True),
            ("{1 2}", "{1 2}", True),
            ("{1 2}", "{1 2 3}", False),
            ("(as point [1 2])", "(as point [1 2])", True),
            ("(as color #'navy')", "(as color #'#000080')", True),
        ],
    )
    def test_values_compare_by_content(self, a, b, result):
        assert value(f"(bool v (= {a} {b}))", "v") is result
        assert value(f"(bool v (!= {a} {b}))", "v") is (not result)

    # The spec does not make clear whether an int or a ratio equals the real nearest to it, as
    # (= 1/3 0.3333333333333333) would, so two numbers that differ only that way are left out.
    @examples(300)
    @given(st.data(), VALUES, VALUES)
    def test_numbers_are_equal_when_they_are_the_same_number(self, data, a, b):
        if data.draw(st.booleans()):
            b = a
        assume(a == b or float(a) != float(b))
        x, y = data.draw(number(a)), data.draw(number(b))
        equal = a == b
        assert value(f"(bool v (= {x} {y}))", "v") is equal
        assert value(f"(bool v (!= {x} {y}))", "v") is (not equal)

    @examples(300)
    @given(st.lists(st.integers(-3, 3), max_size=4), st.lists(st.integers(-3, 3), max_size=4))
    def test_lists_are_equal_when_their_items_are(self, a, b):
        xs, ys = (f"(as list[int] {{{' '.join(map(str, items))}}})" for items in (a, b))
        assert value(f"(bool v (= {xs} {ys}))", "v") is (a == b)

    @examples(300)
    @given(STRINGS, STRINGS)
    def test_strings_are_equal_when_they_are_exactly_the_same(self, a, b):
        assert value(f"(bool v (= '{a}' '{b}'))", "v") is (a == b)

    def test_none_equals_only_none(self):
        assert value(INVERSE + "(bool v (= (f 0) (f 0)))", "v") is True
        assert value(INVERSE + "(bool v (= (f 0) 1))", "v") is False
