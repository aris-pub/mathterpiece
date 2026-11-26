"""Conformance tests of the rule lists (docs/spec/grammar.md)."""

from ._shared import (
    IntLit,
    ListLit,
    PointLit,
    StrLit,
    compile_error,
    dot,
    form,
    items,
    name,
    pytest,
    rule,
    syntax_error,
)


@rule("lists")
class TestLists:
    def test_lists(self):
        assert items("(f {} {0 1} {(g x) 'a'})") == (
            ListLit(()),
            ListLit((IntLit(0), IntLit(1))),
            ListLit((form(name("g"), name("x")), StrLit("a"))),
        )

    def test_points(self):
        assert items("(f [0 1] [(f x) 2])") == (
            PointLit((IntLit(0), IntLit(1))),
            PointLit((form(name("f"), name("x")), IntLit(2))),
        )

    def test_a_point_has_exactly_two_items(self):
        # The parser reads [1 2 3]; the compiler rejects it (core.md, rule sugar-rewrites).
        assert items("(f [1 2 3])") == (PointLit((IntLit(1), IntLit(2), IntLit(3))),)
        compile_error("(point p [1 2 3])")
        compile_error("(point p [1])")

    def test_brackets_after_a_list(self):
        assert items("(f {a b c}[h])") == (
            dot(ListLit((name("a"), name("b"), name("c"))), name("h")),
        )

    @pytest.mark.parametrize(
        "src", ["(f {1}[0 1])", "(f {1}[])", "(f {1)", "(f [1][0 1])", "(f [1)"]
    )
    def test_brackets_after_a_list_hold_exactly_one_expression(self, src):
        syntax_error(src)
