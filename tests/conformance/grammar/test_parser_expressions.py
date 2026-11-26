"""Conformance tests of the rule parser-expressions (docs/spec/grammar.md)."""

from ._shared import (
    Bar,
    ComplexLit,
    IntLit,
    ListLit,
    NoneLit,
    PointLit,
    RatioLit,
    RealLit,
    StrLit,
    field,
    form,
    forms,
    interp,
    items,
    name,
    pytest,
    rule,
)


@rule("parser-expressions")
class TestParserExpressions:
    def test_one_expression_for_each_form_in_order(self):
        assert forms("(a) (b)") == (form(name("a")), form(name("b")))

    @pytest.mark.parametrize(
        "text, node",
        [
            ("(g x)", form(name("g"), name("x"))),
            ("{1}", ListLit((IntLit(1),))),
            ("[1 2]", PointLit((IntLit(1), IntLit(2)))),
            ("p.pos.x", name("p", "pos", "x")),
            ("xs[0].y", name("xs", IntLit(0), "y")),
            ("xs[(f)]", name("xs", form(name("f")))),
            ("real|none", Bar((name("real"), NoneLit()))),
            ("'s'", StrLit("s")),
            ("$'s'", StrLit("s", tex=True)),
            ("f'a{x}'", interp(("a", name("x")))),
            ("f'{x:.2f}'", interp((field(name("x"), ".2f"),))),
            ("3", IntLit(3)),
            ("1/3", RatioLit(__import__("fractions").Fraction(1, 3))),
            ("2.5", RealLit(2.5)),
            ("1+2i", ComplexLit(1 + 2j)),
            ("none", NoneLit()),
        ],
    )
    def test_each_kind_of_expression(self, text, node):
        assert items(f"(f {text})") == (node,)

    def test_two_pieces_of_text_are_never_next_to_each_other(self):
        assert items("(f f'a{{b}}c')") == (interp(("a{b}c",)),)
