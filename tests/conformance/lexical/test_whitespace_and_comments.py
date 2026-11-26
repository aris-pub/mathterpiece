"""Conformance tests of the rule whitespace-and-comments (docs/spec/lexical.md)."""

from ._shared import StrLit, forms, items, name, pytest, rule, syntax_error


@rule("whitespace-and-comments")
class TestWhitespaceAndComments:
    def test_the_three_whitespace_characters_separate_items(self):
        assert items("(f a\tb\nc d)") == tuple(name(c) for c in "abcd")

    def test_a_comment_runs_to_the_next_line_feed(self):
        assert forms("(f ; a comment (g)\n a)") == forms("(f a)")

    def test_a_comment_may_end_the_source(self):
        assert forms("(f a) ; the end") == forms("(f a)")

    def test_inside_a_string_a_semicolon_and_whitespace_are_text(self):
        assert items("(f 'a ; b\tc')") == (StrLit("a ; b\tc"),)

    @pytest.mark.parametrize(
        "ch",
        [
            pytest.param(" ", id="no-break-space"),
            pytest.param(" ", id="line-separator"),
            pytest.param("\x0c", id="form-feed"),
            pytest.param("\x0b", id="vertical-tab"),
            pytest.param("　", id="ideographic-space"),
        ],
    )
    def test_other_space_characters_are_errors(self, ch):
        syntax_error(f"(f a{ch}b)")

    @pytest.mark.parametrize(
        "src",
        [
            "\xa0(f)",
            "(f)\xa0",
            "(f a\xa0)",
            "(f 'a'\xa0)",
            "(f [1]\xa0)",
            "(f xs[0]\xa0)",
            "(f r@\xa01)",
            "(f f'{\xa0x}')",
            "(f f'{x\xa0}')",
            "(f\ra)",
            "(f\r\na)",
        ],
    )
    def test_they_are_errors_in_every_place(self, src):
        syntax_error(src)

    def test_inside_strings_and_comments_they_are_text(self):
        assert items("(f 'a\xa0b c' ; d\xa0e\x0cf\n)") == (StrLit("a\xa0b c"),)
