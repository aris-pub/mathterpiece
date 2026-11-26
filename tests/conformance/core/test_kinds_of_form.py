"""Conformance tests of the rule kinds-of-form (docs/spec/core.md)."""

from ._shared import rule, same_meaning


@rule("kinds-of-form")
class TestKindsOfForm:
    def test_one_head_begins_both_kinds(self):
        # Two names in one foreach are syntactic sugar for two foreach forms of one name each.
        same_meaning(
            "(scene t (foreach ((a {1 2}) (b {3 4})) (circle @'c-{a}-{b}' (r a))))",
            "(scene t (foreach a {1 2} (foreach b {3 4} (circle @'c-{a}-{b}' (r a)))))",
        )
