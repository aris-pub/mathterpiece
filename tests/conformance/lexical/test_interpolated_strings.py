"""Conformance tests of the rule interpolated-strings (docs/spec/lexical.md)."""

from ._shared import Form, StrLit, field, form, interp, items, name, pytest, rule, syntax_error


@rule("interpolated-strings")
class TestInterpolatedStrings:
    def test_text_and_braces(self):
        assert items("(f f'a = {a}')") == (interp(("a = ", name("a"))),)

    def test_doubled_braces_and_escapes(self):
        assert items("(f f'{{x}}\\'')") == (interp(("{x}'",)),)

    def test_a_format_spec(self):
        assert items("(f f'{x:.2f}')") == (interp((field(name("x"), ".2f"),)),)

    def test_whitespace_around_the_expression(self):
        assert items("(f f'{ x }')") == items("(f f'{x}')")

    def test_a_comment_inside_a_form_in_the_braces(self):
        assert items("(f f'{(g ; c\n x)}')") == items("(f f'{(g x)}')")

    @pytest.mark.parametrize(
        "src", ["(f f'{x ; c\n}')", "(f f'{ ;c\n x}')", "(f @'a{k ;c\n}')", "(f f'{(g) ;c\n:>5}')"]
    )
    def test_a_comment_around_the_expression_is_an_error(self, src):
        syntax_error(src)

    def test_a_name_string(self):
        assert items("(f @'dot-{k}')") == (form(name("name"), interp(("dot-", name("k")))),)

    @pytest.mark.parametrize(
        "src", ["(f f'}')", "(f f'a}b')", "(f @'plain')", "(f f'{}')", "(f f'{a b}')"]
    )
    def test_errors(self, src):
        syntax_error(src)

    def test_a_colon_in_a_nested_expression_is_an_error(self):
        syntax_error("(f f'{(g a:b)}')")

    def test_braces_are_read_the_same_at_every_depth(self):
        assert items("(f f'{f'{a}'}')") == (interp((interp((name("a"),)),)),)

    def test_after_a_nested_name_string_the_braces_go_on(self):
        (s,) = items("(f f'{@'n-{k}'.x:y}')")
        (_, piece) = s.items
        assert isinstance(piece, Form) and piece.items[2] == StrLit("y")
        assert isinstance(piece.items[1], Form)
