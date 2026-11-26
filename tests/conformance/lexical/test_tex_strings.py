"""Conformance tests of the rule tex-strings (docs/spec/lexical.md)."""

from ._shared import StrLit, items, rule


@rule("tex-strings")
class TestTexStrings:
    def test_backslashes_stay_as_written(self):
        assert items("(f $'\\frac12' $'\\q')") == (
            StrLit("\\frac12", tex=True),
            StrLit("\\q", tex=True),
        )

    def test_an_escaped_quote_is_a_quote(self):
        assert items("(f $'f\\'(x)')") == (StrLit("f'(x)", tex=True),)

    def test_a_backslash_and_the_next_character_are_read_together(self):
        assert items("(f $'a\\\\')") == (StrLit("a\\\\", tex=True),)
