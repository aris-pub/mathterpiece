"""Conformance tests of the rule name-brackets (docs/spec/grammar.md)."""

from ._shared import (
    Brackets,
    IntLit,
    PointLit,
    StrLit,
    form,
    items,
    name,
    pytest,
    rule,
    syntax_error,
)


@rule("name-brackets")
class TestNameBrackets:
    def test_one_expression(self):
        assert items("(f xs[0] xs[(+ k 1)] g['m1'])") == (
            name("xs", IntLit(0)),
            name("xs", form(name("+"), name("k"), IntLit(1))),
            name("g", StrLit("m1")),
        )

    def test_several_expressions(self):
        assert items("(f func[real real])") == (
            name("func", Brackets((name("real"), name("real")))),
        )

    def test_chains_of_brackets_and_parts(self):
        assert items("(f xs[0].pos.x m[0][1] a[0].b[1])") == (
            name("xs", IntLit(0), "pos", "x"),
            name("m", IntLit(0), IntLit(1)),
            name("a", IntLit(0), "b", IntLit(1)),
        )

    def test_a_bracket_after_whitespace_starts_a_point(self):
        assert items("(f xs [0 1])") == (name("xs"), PointLit((IntLit(0), IntLit(1))))

    @pytest.mark.parametrize("src", ["(f xs[])", "(f xs[0)", "(f xs[0].)"])
    def test_errors(self, src):
        syntax_error(src)
