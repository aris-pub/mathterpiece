"""Conformance tests of the rule arguments-before-call (docs/spec/evaluation.md)."""

from ._shared import accepted, compile_error, rule


@rule("arguments-before-call")
class TestArgumentsBeforeCall:
    def test_an_argument_that_the_body_does_not_read_is_evaluated(self):
        # g never reads a, but (/ 1 x) is evaluated, and when it gives none the call gives none.
        src = "(real x 0 (>= -1) (<= 1)) (func g ((real a) (real b)) b)"
        compile_error(src + " (real v (g (/ 1 x) 2))")
        accepted(src + " (real|none v (g (/ 1 x) 2))")
