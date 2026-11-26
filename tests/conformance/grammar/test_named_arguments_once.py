"""Conformance tests of the rule named-arguments-once (docs/spec/grammar.md)."""

from ._shared import compile_error, rule


@rule("named-arguments-once")
class TestOptionalArgumentsOnce:
    def test_twice_is_an_error(self):
        compile_error("(scene s (circle c (fill #'red') (fill #'blue')))")

    def test_pos_and_x_give_x_twice(self):
        compile_error("(scene s (circle c (pos [1 2]) (x 3) (r 1)))")
