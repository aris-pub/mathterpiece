"""Conformance tests of the rule call-depth-limit (docs/spec/evaluation.md)."""

from ._shared import DEPTH, compile_error, rule, value


@rule("call-depth-limit")
class TestCallDepthLimit:
    DOWN = "(func[int] down ((int m)) (if (<= m 0) 0 (+ 1 (down (- m 1)))))\n"

    def test_a_short_chain_is_folded(self):
        assert value(self.DOWN + "(int v (down 10))", "v") == 10

    @DEPTH
    def test_a_chain_of_depth_256_is_folded(self):
        assert value(self.DOWN + "(int v (down 255))", "v") == 255

    @DEPTH
    def test_a_chain_deeper_than_256_is_a_compile_error(self):
        compile_error(self.DOWN + "(int v (down 256))")
