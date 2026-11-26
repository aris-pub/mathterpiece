"""Conformance tests of the rule reserved-characters (docs/spec/lexical.md)."""

from ._shared import StrLit, items, pytest, rule, syntax_error


@rule("reserved-characters")
class TestReservedCharacters:
    @pytest.mark.parametrize(
        "src",
        [
            "(f })",
            '(f "x")',
            "(f $x)",
            "(f #x)",
            "(f :a)",
            "(f 'a':b)",
        ],
    )
    def test_reserved_characters_outside_strings_are_errors(self, src):
        syntax_error(src)

    def test_inside_a_string_they_are_text(self):
        assert items("(f '{a} \"b\" $c #d :e')") == (StrLit('{a} "b" $c #d :e'),)
