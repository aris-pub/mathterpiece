"""Conformance tests of the rule prefix-forms (docs/spec/lexical.md)."""

from ._shared import (
    ColorLit,
    IntLit,
    StrLit,
    compile_error,
    form,
    items,
    name,
    pytest,
    rule,
    syntax_error,
)


@rule("prefix-forms")
class TestPrefixForms:
    def test_a_docstring(self):
        assert items("(f doc@'text')") == (form(name("doc"), StrLit("text")),)

    def test_a_free_starting_value(self):
        assert items("(f free@green)") == (form(name("free"), name("green")),)
        assert items("(f free@(g))") == (form(name("free"), form(name("g"))),)

    def test_an_optional_argument(self):
        assert items("(circle c r@1 fill@#'red')") == (
            name("c"),
            form(name("r"), IntLit(1)),
            form(name("fill"), ColorLit("#ff0000ff")),
        )

    @pytest.mark.parametrize(
        "src, written",
        [
            ("(f to@pointer.x)", "(f (to pointer.x))"),
            ("(f marks.grid@g)", "(f (marks.grid g))"),
            ("(f r@(* 2 k))", "(f (r (* 2 k)))"),
            ("(f pos@[1 2])", "(f (pos [1 2]))"),
            ("(f f@@'a-{k}')", "(f (f @'a-{k}'))"),
            ("(f x@xs[0] y@a|b)", "(f (x xs[0]) (y a|b))"),
            (
                "(f r@none s@true t@-1.5 u@$'q' v@f'{k}')",
                "(f (r none) (s true) (t -1.5) (u $'q') (v f'{k}'))",
            ),
            ("(f free@(g)x)", "(f (free (g)) x)"),
            ("(f f'{r@x:.2f}')", "(f f'{(r x):.2f}')"),
        ],
    )
    def test_it_is_the_form_of_the_head_and_the_item(self, src, written):
        assert items(src) == items(written)

    def test_the_form_and_its_head_have_the_position_of_its_first_character(self):
        (r,) = items("(f  r@1)")
        assert (r.pos.line, r.pos.col) == (1, 5)
        assert (r.items[0].pos.line, r.items[0].pos.col) == (1, 5)
        assert (r.items[1].pos.line, r.items[1].pos.col) == (1, 7)

    @pytest.mark.parametrize(
        "src",
        [
            "(f fill@free@green)",
            "(f r@a@b)",
            "(f +@1)",
            "(f .@1)",
            "(f circle_@c)",
            "(f none@1)",
            "(f true@1)",
            "(f 1@x)",
            "(f #'a'@1)",
            "(f @'a{b}'@1)",
            "(f xs[0]@1)",
            "(f a|r@1)",
            "(f r@ 1)",
            "(f r @1)",
            "(f doc@;c\n'x')",
            "(f r@)",
            "(f @x)",
            "(f a@b@)",
        ],
    )
    def test_nothing_between_the_prefix_and_its_item_and_no_other_at_sign(self, src):
        syntax_error(src)

    def test_the_form_must_be_allowed_where_it_is_written(self):
        compile_error("(bool c true) (real k if@c)")
