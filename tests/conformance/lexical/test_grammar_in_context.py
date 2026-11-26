"""Conformance tests of the rule grammar-in-context (docs/spec/lexical.md)."""

from ._shared import (
    ComplexLit,
    Fraction,
    IntLit,
    NoneLit,
    RatioLit,
    RealLit,
    form,
    forms,
    items,
    name,
    rule,
    syntax_error,
)


@rule("grammar-in-context")
class TestGrammarInContext:
    def test_a_word_that_starts_with_true_is_one_name(self):
        assert items("(f truex)") == (name("truex"),)

    def test_the_longest_number_is_read(self):
        assert items("(f 1/2 1.5 2i)") == (
            RatioLit(Fraction(1, 2)),
            RealLit(1.5),
            ComplexLit(complex(0, 2)),
        )

    def test_a_head_with_an_underscore_is_read_only_where_a_head_may_be(self):
        assert forms("(circle_ (r 1))") == (
            form(name("circle"), NoneLit(), form(name("r"), IntLit(1))),
        )

    def test_the_same_text_as_an_argument_is_an_error(self):
        syntax_error("(f circle_)")
