"""Conformance tests of the rule top-level-forms (docs/spec/grammar.md)."""

from ._shared import accepted, forms, pytest, rule, syntax_error


@rule("top-level-forms")
class TestTopLevelForms:
    @pytest.mark.parametrize("src", ["", "  ; only a comment\n", "(a)(b)", "\n(a)\n ; c\n(b)"])
    def test_any_number_of_forms(self, src):
        forms(src)

    @pytest.mark.parametrize("src", ["x", "'s'", "[1 2]", "{1}", "(a)x", "1", "(a) )"])
    def test_anything_else_is_an_error(self, src):
        syntax_error(src)

    def test_a_source_with_no_form_compiles(self):
        accepted("")
