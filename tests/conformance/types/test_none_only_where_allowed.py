"""Conformance tests of the rule none-only-where-allowed (docs/spec/types.md)."""

from ._shared import accepted, compile_error, pytest, rule


@rule("none-only-where-allowed")
class TestNoneOnlyWhereAllowed:
    SECANT = "(real theta 90) (real|none s (secd theta)) "
    NONE = "(real|none r none) "

    def test_an_argument_of_a_call(self):
        accepted(self.SECANT + "(real|none v (* 2 s))")
        compile_error(self.SECANT + "(real v (* 2 s))")

    def test_an_attribute_of_a_shape_declared_with_none(self):
        accepted(self.NONE + "(scene s (circle|none c (pos [0 0]) (r r)))")
        compile_error(self.NONE + "(scene s (circle k (pos [0 0]) (r r)))")

    @pytest.mark.parametrize("src", [NONE + "(real v r)", "(bool|none c none) (real v (if c 1 2))"])
    def test_nowhere_else(self, src):
        compile_error(src)
