"""Conformance tests for docs/spec/world-model.md."""

import pytest

from .support import compile_error, same_meaning

rule = pytest.mark.rule


@rule("container-defaults")
class TestContainerDefaults:
    def test_defaults_on_a_group(self):
        same_meaning(
            "(scene s (group g (defaults (fill #'red')) (circle c (r 1)) (circle d (r 1) (fill "
            "#'blue'))))",
            "(scene s (group g (circle c (r 1) (fill #'red')) (circle d (r 1) (fill #'blue'))))",
        )

    def test_defaults_at_any_depth_the_nearest_container_first(self):
        same_meaning(
            "(scene s (group g (defaults (fill #'red')) (group h (defaults (fill #'blue'))"
            " (circle c (r 1)))))",
            "(scene s (group g (group h (circle c (r 1) (fill #'blue')))))",
        )

    def test_a_default_that_no_container_gives(self):
        compile_error("(scene s (group g (defaults (r 2)) (circle c)))")

    def test_pointer_events_in_defaults(self):
        same_meaning(
            "(scene s (group g (defaults (pointer-events false)) (circle c (r 1))))",
            "(scene s (group g (circle c (r 1) (pointer-events false))))",
        )


@rule("formula-defaults")
class TestFormulaDefaults:
    def test_defaults_in_a_formula(self):
        same_meaning(
            "(formula f $'\\term{a}{x}\\term{b}{y}' (defaults (fill #'red')) (term a (fill "
            "#'blue')))",
            "(formula f $'\\term{a}{x}\\term{b}{y}' (term a (fill #'blue'))"
            " (term b (fill #'red')))",
        )
