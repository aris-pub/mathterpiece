"""Conformance tests of the rule forms (docs/spec/grammar.md)."""

from ._shared import IntLit, form, forms, items, name, pytest, rule


@rule("forms")
class TestForms:
    def test_the_items_of_a_form_are_expressions(self):
        assert forms("(circle c (r 1))") == (
            form(name("circle"), name("c"), form(name("r"), IntLit(1))),
        )

    @pytest.mark.parametrize(
        "src", ["(f [1 2])", "(f 'a')", "(f f'a{b}')", "(f real|none)", "(f 2.5)"]
    )
    def test_an_item_may_be_any_kind_of_expression(self, src):
        assert len(items(src)) == 1

    def test_the_empty_form_has_no_items(self):
        assert forms("(f ())") == (form(name("f"), form()),)
