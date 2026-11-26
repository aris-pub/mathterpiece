"""Conformance tests of the rule named-arguments-first (docs/spec/grammar.md)."""

from ._shared import accepted, compile_error, mtpc, rule


@rule("named-arguments-first")
class TestOptionalArgumentsFirst:
    def test_in_any_order_before_the_body(self):
        assert mtpc("(scene s (circle c (r 1) (fill #'red')))") == mtpc(
            "(scene s (circle c (fill #'red') (r 1)))"
        )

    def test_an_optional_argument_after_the_body_is_an_error(self):
        compile_error("(scene s (circle c (r 1)) (background #'white'))")

    def test_like_comes_first(self):
        compile_error("(scene s (circle a (r 1)) (circle b (fill #'red') (like a)))")
        accepted("(scene s (circle a (r 1)) (circle b (like a) (fill #'red')))")

    def test_the_defaults_of_a_formula(self):
        compile_error("(formula f $'\\term{a}{x}' (term a (fill #'red')) (defaults (padding 3)))")

    def test_the_font_of_a_readout(self):
        compile_error("(font f (size 12)) (readout r 'x' (on-live (animation)) (font f))")

    def test_the_kind_of_a_display(self):
        compile_error("(formula f $'x') (display d f (on-live (animation)) (kind 'block'))")

    def test_the_font_of_a_readout_before_its_listeners(self):
        accepted("(font f (size 12)) (readout r 'x' (font f) (on-live (animation)))")

    def test_the_kind_of_a_display_before_its_listeners(self):
        accepted("(formula f $'x') (display d f (kind 'block') (on-live (animation)))")
