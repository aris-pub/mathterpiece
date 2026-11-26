"""Conformance tests of the rule formula-defaults (docs/spec/world-model.md)."""

from ._shared import rule, same_meaning


@rule("formula-defaults")
class TestFormulaDefaults:
    def test_defaults_in_a_formula(self):
        same_meaning(
            "(formula f $'\\term{a}{x}\\term{b}{y}' (defaults (fill #'red')) (term a (fill "
            "#'blue')))",
            "(formula f $'\\term{a}{x}\\term{b}{y}' (term a (fill #'blue'))"
            " (term b (fill #'red')))",
        )
