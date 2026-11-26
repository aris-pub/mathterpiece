"""Conformance tests of the rule sugar-form (docs/spec/core.md)."""

from ._shared import SCENE, rule, same_meaning


@rule("sugar-form")
class TestSugarForm:
    def test_a_rewrite_may_resolve_a_name(self):
        # p.r is rewritten into (. p r) by reading which shape p names.
        same_meaning(SCENE + "(real v p.r)", SCENE + "(real v (. p r))")

    def test_a_sugar_form_means_exactly_its_rewrite(self):
        same_meaning(
            "(bool c true) (real|none v (when c 1))", "(bool c true) (real|none v (if c 1 none))"
        )
