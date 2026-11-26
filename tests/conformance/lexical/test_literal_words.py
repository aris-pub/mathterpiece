"""Conformance tests of the rule literal-words (docs/spec/lexical.md)."""

from ._shared import BoolLit, NoneLit, items, name, pytest, rule, syntax_error


@rule("literal-words")
class TestLiteralWords:
    def test_bools_and_none(self):
        assert items("(f true false none)") == (BoolLit(True), BoolLit(False), NoneLit())

    @pytest.mark.parametrize("op", ["+", "-", "*", "/", "^", "<", "<=", ">", ">=", "=", "!=", "."])
    def test_each_operator_is_a_name_of_one_part(self, op):
        assert items(f"(f {op})") == (name(op),)

    @pytest.mark.parametrize(
        "src",
        [
            "(f +[0])",
            "(f true[0])",
            "(f none[0])",
            "(f 3[0])",
            "(f !=x)",
        ],
    )
    def test_brackets_after_an_operator_a_bool_none_or_a_number_are_errors(self, src):
        syntax_error(src)
