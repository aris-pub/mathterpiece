"""Conformance tests of the rule function-result-type (docs/spec/types.md)."""

from ._shared import FACTORIAL, RECURSION, accepted, compile_error, rule


@rule("function-result-type")
class TestFunctionResultType:
    def test_a_declared_result_type(self):
        compile_error("(func[real] f ((real x)) 'a')")

    def test_the_type_of_the_body(self):
        assert accepted("(func f ((real x)) 'a') (string v (f 1))").get("v").value.value == "a"
        compile_error("(func f ((real x)) 'a') (real v (f 1))")

    def test_a_function_that_calls_itself_with_its_result_type(self):
        assert accepted("(func[int] f " + FACTORIAL + " (int v (f 4))").get("v").value.value == 24

    @RECURSION
    def test_a_function_that_calls_itself_without_its_result_type(self):
        compile_error("(func f " + FACTORIAL)
