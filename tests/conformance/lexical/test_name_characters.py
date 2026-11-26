"""Conformance tests of the rule name-characters (docs/spec/lexical.md)."""

from hypothesis import assume, given

from ._shared import (
    LITERAL_WORDS,
    NAME_PARTS,
    NAMES_OK,
    examples,
    items,
    name,
    pytest,
    rule,
    st,
    syntax_error,
)

# ASCII characters that are neither a letter, a digit nor a hyphen. The others have a meaning
# right after a name: . and [ start a name part or brackets, | a broadened type, @ a prefixed
# form, and whitespace, ( ) ] { } and ; end the word.
NOT_IN_A_NAME = "!*=%&~<>+,\\`$#/^:_?'\""


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

    @examples(300)
    @given(st.lists(NAME_PARTS, min_size=1, max_size=4))
    def test_every_name_of_letters_digits_and_hyphens(self, parts):
        assert items(f"(f {'.'.join(parts)})") == (name(*parts),)

    @examples(300)
    @given(NAME_PARTS, st.sampled_from(NOT_IN_A_NAME), st.data())
    def test_a_name_with_another_ascii_character(self, part, c, data):
        i = data.draw(st.integers(1, len(part)))
        assume(not (c == "?" and i == len(part) and not part.endswith("?")))
        syntax_error(f"(f {part[:i]}{c}{part[i:]})")

    @examples(300)
    @given(NAME_PARTS, st.characters(min_codepoint=0x80), st.data())
    def test_a_name_with_a_character_that_is_not_ascii(self, part, c, data):
        i = data.draw(st.integers(0, len(part)))
        syntax_error(f"(f {part[:i]}{c}{part[i:]})")

    # A digit or a hyphen may not start a name. The text is no number either, since the only
    # letters in a number are e, E and i.
    @examples(300)
    @given(st.sampled_from("0123456789-"), NAME_PARTS.filter(lambda part: part[0] not in "eEi"))
    def test_a_name_starts_with_a_letter(self, first, part):
        syntax_error(f"(f {first}{part})")

    @examples(300)
    @given(st.lists(NAME_PARTS, min_size=1, max_size=3), st.sampled_from(LITERAL_WORDS), st.data())
    def test_a_name_part_that_is_true_false_or_none(self, parts, word, data):
        parts.insert(data.draw(st.integers(0, len(parts))), word)
        syntax_error(f"(f {'.'.join(parts)})")
