"""Conformance tests of the rule name-underscore (docs/spec/lexical.md)."""

from ._shared import NoneLit, forms, name, pytest, rule, syntax_error


@rule("name-underscore")
class TestNameUnderscore:
    @pytest.mark.parametrize(
        "src, head",
        [
            ("(circle_ (r 1))", name("circle")),
            ("(marks.grid_ a)", name("marks", "grid")),
        ],
    )
    def test_an_underscore_at_the_end_of_a_head(self, src, head):
        assert forms(src)[0].items[:2] == (head, NoneLit())

    def test_an_underscore_after_a_broadened_type_and_after_none(self):
        assert len(forms("(line|none_ (r 1))")[0].items) == 3
        assert forms("(none_ a)")[0].items == (NoneLit(), NoneLit(), name("a"))

    @pytest.mark.parametrize(
        "text",
        [
            "x_",
            "a_b",
            "_x",
            "_",
            "a_.b",
            "a._",
            "_.a",
            "_[0]",
        ],
    )
    def test_an_underscore_in_any_other_place_is_an_error(self, text):
        syntax_error(f"(f {text})")

    @pytest.mark.parametrize("src", ["(a_.b x)", "(a._ x)", "(a_|b x)", "(a_[0] x)", "(+_ x)"])
    def test_an_underscore_inside_a_head_is_an_error(self, src):
        syntax_error(src)

    def test_an_underscore_after_the_last_part_of_a_head_with_several_parts(self):
        assert forms("(a.b-c_ x)")[0].items == (name("a", "b-c"), NoneLit(), name("x"))
