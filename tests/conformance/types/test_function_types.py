"""Conformance tests of the rule function-types (docs/spec/types.md)."""

from ._shared import FUNCTION_VALUES, accepted, compile_error, pytest, rule


@rule("function-types")
class TestFunctionTypes:
    def test_a_parameter_may_be_a_function(self):
        src = "(func twice ((func[real real] f) (real x)) (f (f x)))"
        v = accepted(src + " (real v (twice (fn ((real x)) (* 2 x)) 3))").get("v").value.value
        assert v == 12

    def test_the_type_of_fn_has_the_type_of_its_body_as_its_result(self):
        compile_error("(func g ((func[real real] h)) (h 2)) (real v (g (fn ((real x)) 'a')))")

    @FUNCTION_VALUES
    @pytest.mark.parametrize(
        "src",
        [
            "(list[func[real real]] fs {sind cosd})",
            "(list fs {sind cosd})",
            "(func g () sind)",
            "(func g () {sind cosd})",
        ],
    )
    def test_no_variable_and_no_result_holds_a_function(self, src):
        compile_error(src)
