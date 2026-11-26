"""Conformance tests of the rule formula-terms (docs/spec/grammar.md)."""

from ._shared import accepted, compile_error, rule


@rule("formula-terms")
class TestFormulaTerms:
    def test_the_string_declares_its_terms(self):
        accepted("(formula f $'\\term{a}{x}' (defaults (padding 3)) (term a (fill #'red')))")

    def test_the_string_after_the_defaults_is_an_error(self):
        compile_error("(formula f (defaults (padding 3)) $'\\term{a}{x}' (term a (fill #'red')))")

    def test_a_term_that_the_string_does_not_mark_is_an_error(self):
        compile_error("(formula f $'\\term{a}{x}' (term b (fill #'red')))")

    def test_a_term_before_the_string_is_an_error(self):
        compile_error("(formula f (term a (fill #'red')) $'\\term{a}{x}')")

    def test_a_variable_before_the_string_is_an_error(self):
        compile_error("(formula f (real k 1) $'x')")
