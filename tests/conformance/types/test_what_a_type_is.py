"""Conformance tests of the rule what-a-type-is (docs/spec/types.md)."""

from ._shared import UNION, accepted, compile_error, rule


@rule("what-a-type-is")
class TestWhatATypeIs:
    def test_a_value_outside_the_set_is_an_error(self):
        compile_error("((real (>= 0)) k -1)")
        accepted("((real (>= 0)) k 1)")

    @UNION
    def test_a_union_of_two_types(self):
        accepted("(func f ((point|circle p)) 1)")

    @UNION
    def test_a_variable_whose_type_is_an_interface(self):
        accepted("(interface inky (color ink)) (namespace day (color ink #'navy')) (inky look day)")
