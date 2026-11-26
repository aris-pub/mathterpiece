"""Conformance tests of the rule foreach-count (docs/spec/core.md)."""

from ._shared import rule, same_meaning


@rule("foreach-count")
class TestForeachCount:
    def test_a_count_means_a_range(self):
        same_meaning(
            "(scene s (foreach k 3 (circle @'c-{k}' (r 1))))",
            "(scene s (foreach k (range 0 3 (gap 1)) (circle @'c-{k}' (r 1))))",
        )
