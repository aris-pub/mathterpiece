"""Conformance tests of the rule color-literals (docs/spec/lexical.md)."""

from ._shared import accepted, compile_error, rule


@rule("color-literals")
class TestColorLiterals:
    def test_three_spellings_of_one_color(self):
        a = accepted("(color c #'red')").get("c").value.value
        assert a == accepted("(color c #'#ff0000')").get("c").value.value
        assert a == accepted("(color c #'ff0000')").get("c").value.value

    def test_a_string_is_never_a_color(self):
        accepted("(color c #'red')")
        compile_error("(color c 'red')")

    def test_a_string_in_a_fill_is_an_error(self):
        accepted("(scene s (circle c (r 1) (fill #'red')))")
        compile_error("(scene s (circle c (r 1) (fill 'red')))")

    def test_a_color_is_never_a_string(self):
        compile_error("(string s #'red')")
