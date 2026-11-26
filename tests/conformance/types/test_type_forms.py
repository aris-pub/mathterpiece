"""Conformance tests of the rule type-forms (docs/spec/types.md)."""

from ._shared import TYPE_FORMS, UNION, accepted, compile_error, pytest, rule, same_meaning


@rule("type-forms")
class TestTypeForms:
    def test_list_and_func_take_types_in_brackets(self):
        assert accepted("(list[int] v {1 2})").get("v").value.value == [1, 2]
        accepted("(func f ((func[real real] h)) (h 1)) (real v (f sind))")

    @pytest.mark.parametrize("src", ["(real[int] v 1)", "(list[int real] v {1})"])
    def test_other_types_in_brackets_are_an_error(self, src):
        compile_error(src)

    def test_list_with_no_item_type_takes_the_type_of_its_value(self):
        same_meaning("(list v {1 2})", "(list[int] v {1 2})")

    @pytest.mark.parametrize("src", ["(list v)", "(func f ((list xs)) 1)"])
    def test_list_with_no_item_type_and_no_value(self, src):
        compile_error(src)

    @UNION
    def test_a_union_of_a_type_with_itself(self):
        same_meaning("(real|real v 1)", "(real v 1)")

    @TYPE_FORMS
    def test_the_type_forms_written_out(self):
        same_meaning("((type-apply list int) v {1 2})", "(list[int] v {1 2})")
