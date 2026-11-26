"""Conformance tests of the rule word-ends (docs/spec/lexical.md)."""

from ._shared import form, items, name, pytest, rule, syntax_error


@rule("word-ends")
class TestWordEnds:
    @pytest.mark.parametrize("src", ["(f af'x')", "(f 1x)", "(f a#'x')"])
    def test_text_that_is_not_one_word_is_an_error(self, src):
        syntax_error(src)

    def test_a_quote_does_not_end_a_word(self):
        syntax_error("(f a'b)")

    def test_a_word_ends_at_a_parenthesis_a_bracket_a_semicolon_or_a_bar(self):
        assert items("(f a(g))") == (name("a"), form(name("g")))
        assert items("(f a;c\n)") == (name("a"),)

    def test_a_word_ends_at_a_colon(self):
        syntax_error("(f a:b)")
