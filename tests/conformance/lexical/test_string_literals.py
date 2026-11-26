"""Conformance tests of the rule string-literals (docs/spec/lexical.md)."""

from ._shared import StrLit, items, rule, syntax_error


@rule("string-literals")
class TestStringLiterals:
    def test_the_three_escapes(self):
        assert items("(f 'it\\'s' 'a\\\\b' 'a\\nb')") == (
            StrLit("it's"),
            StrLit("a\\b"),
            StrLit("a\nb"),
        )

    def test_a_line_feed_is_itself(self):
        assert items("(f 'a\nb')") == (StrLit("a\nb"),)

    def test_any_other_escape_is_an_error(self):
        syntax_error("(f 'a\\q')")

    def test_an_unclosed_string_is_an_error(self):
        syntax_error("(f 'a)")
