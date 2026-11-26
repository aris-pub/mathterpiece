"""Conformance tests of the rule no-name-part-after-form (docs/spec/lexical.md)."""

from ._shared import IntLit, form, items, name, pytest, rule, syntax_error


@rule("no-name-part-after-form")
class TestNoPartAfterForm:
    @pytest.mark.parametrize("src", ["(f (sort xs).x)", "(f (sort xs)[0])"])
    def test_a_part_after_a_form_is_an_error(self, src):
        syntax_error(src)

    def test_a_part_of_a_form_is_read_with_the_dot_form(self):
        assert items("(f (. (sort xs) 0))") == (
            form(name("."), form(name("sort"), name("xs")), IntLit(0)),
        )
