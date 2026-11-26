"""Conformance tests of the rule name-characters (docs/spec/lexical.md)."""

from ._shared import NAMES_OK, items, name, pytest, rule, syntax_error


@rule("name-characters")
class TestNameCharacters:
    @pytest.mark.parametrize("text", NAMES_OK)
    def test_names(self, text):
        assert items(f"(f {text})") == (name(*text.split(".")),)

    @pytest.mark.parametrize(
        "text",
        [
            "2x",
            "-x",
            "a?b",
            "x'",
            "a!b",
            "a*b",
            "a=b",
            "a:b",
            "θ",
            "π",
            "x²",
            "ünï",
        ],
    )
    def test_not_names(self, text):
        syntax_error(f"(f {text})")

    @pytest.mark.parametrize(
        "text",
        [
            "true.x",
            "p.true",
            "none.x",
            "xs[0].none",
            "none[0]",
            "a.false.b",
            "none.x[0]",
            "r@none.x",
            "@'a{k}'.true",
        ],
    )
    def test_a_part_that_is_true_false_or_none_is_an_error(self, text):
        syntax_error(f"(f {text})")

    @pytest.mark.parametrize("text", ["a|$'q'", "xs[0].$'q'"])
    def test_a_tex_string_after_a_bar_or_a_dot_is_an_error(self, text):
        syntax_error(f"(f {text})")

    def test_pi_written_as_a_greek_letter_is_no_name(self):
        syntax_error("(real v π)")
