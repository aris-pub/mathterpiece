"""Conformance tests of the rule foreach-bounded-length (docs/spec/core.md)."""

from ._shared import BOUNDED_LIST, compile_error, mtpc, rule


@rule("foreach-bounded-length")
class TestForeachBoundedLength:
    def test_a_count_known_only_while_drawing_makes_its_upper_bound_of_copies(self):
        d = mtpc("(int n 3 (>= 0) (<= 5)) (scene s (foreach k n (circle @'c-{k}' (r 1))))")
        assert {f"c-{k}" for k in range(5)} <= set(d["names"])
        assert "c-5" not in d["names"]

    @BOUNDED_LIST
    def test_a_range_known_only_while_drawing(self):
        d = mtpc(
            "(int n 3 (>= 0) (<= 5)) "
            "(scene s (foreach k (range 0 n (gap 1)) (circle @'c-{k}' (r 1))))"
        )
        assert {f"c-{k}" for k in range(5)} <= set(d["names"])

    def test_with_no_upper_bound_it_is_an_error(self):
        compile_error("(int n 3 (>= 0)) (scene s (foreach k n (circle @'c-{k}' (r 1))))")
