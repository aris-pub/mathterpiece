"""Conformance tests of the rule collection-defaults (docs/spec/world-model.md)."""

from ._shared import compile_error, rule, same_meaning


@rule("collection-defaults")
class TestCollectionDefaults:
    def test_defaults_on_a_group(self):
        same_meaning(
            "(scene s (group g (defaults (fill #'red')) (circle c (r 1)) (circle d (r 1) (fill "
            "#'blue'))))",
            "(scene s (group g (circle c (r 1) (fill #'red')) (circle d (r 1) (fill #'blue'))))",
        )

    def test_defaults_at_any_depth_the_nearest_collection_first(self):
        same_meaning(
            "(scene s (group g (defaults (fill #'red')) (group h (defaults (fill #'blue'))"
            " (circle c (r 1)))))",
            "(scene s (group g (group h (circle c (r 1) (fill #'blue')))))",
        )

    def test_a_default_that_no_collection_gives(self):
        compile_error("(scene s (group g (defaults (r 2)) (circle c)))")

    def test_pointer_events_in_defaults(self):
        same_meaning(
            "(scene s (group g (defaults (pointer-events false)) (circle c (r 1))))",
            "(scene s (group g (circle c (r 1) (pointer-events false))))",
        )
