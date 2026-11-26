"""Conformance tests of the rule word-ends (docs/spec/lexical.md)."""

from hypothesis import given

from ._shared import (
    NAME_PARTS,
    NUMBERS,
    WORDS,
    examples,
    form,
    items,
    name,
    pytest,
    rule,
    st,
    syntax_error,
)

# Whitespace, a comment and a parenthesis each end a word.
ENDS = st.sampled_from([" ", "\t", "\n", "  \n\t", " ;c\n", ";c\n"])


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

    @examples(300)
    @given(st.lists(st.tuples(WORDS, ENDS), min_size=1, max_size=4))
    def test_each_word_ends_at_whitespace_or_a_comment(self, words):
        src = "(f " + "".join(w + end for w, end in words) + ")"
        assert items(src) == tuple(item for w, _ in words for item in items(f"(f {w})"))

    @examples(300)
    @given(WORDS)
    def test_a_word_ends_at_a_parenthesis(self, w):
        (word,) = items(f"(f {w})")
        assert items(f"(f {w}(g))") == (word, form(name("g")))
        assert items(f"(f (g {w}))") == (form(name("g"), word),)

    # A name followed by ' is not one word, except f, which starts an interpolated string.
    @examples(300)
    @given(WORDS.filter(lambda w: w != "f"), st.sampled_from(["'x'", "$'x'", "#'x'", "/b", "^b"]))
    def test_a_word_followed_by_a_character_that_does_not_end_it(self, w, tail):
        syntax_error(f"(f {w}{tail})")

    # The only letters in a number are e, E and i, so a number followed by any other letter is
    # not one word.
    @examples(300)
    @given(NUMBERS, NAME_PARTS.filter(lambda part: part[0] not in "eEi"))
    def test_a_number_followed_by_a_name(self, number, part):
        syntax_error(f"(f {number}{part})")
