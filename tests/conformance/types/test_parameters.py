"""Conformance tests of the rule parameters (docs/spec/types.md)."""

from ._shared import accepted, compile_error, pytest, rule


@rule("parameters")
class TestParameters:
    @pytest.mark.parametrize(
        "src",
        [
            "(func f ((real x 'a')) x)",
            "(real a 1) (func f ((real x a)) x)",
            "(func f (((real (>= 0)) x)) x) (real v (f -1))",
            "(func g ((func[real real real] h)) (h 2))",
        ],
    )
    def test_errors(self, src):
        compile_error(src)

    def test_a_parameter_left_out_holds_its_default(self):
        src = "(func f ((real x) (real y 5)) (+ x y)) (real v (f 1))"
        assert accepted(src).get("v").value.value == 6

    def test_a_parameter_with_no_default_holds_the_default_value_of_its_type(self):
        assert accepted("(func f ((real x) (real y)) y) (real v (f 1))").get("v").value.value == 0

    def test_a_bare_parameter_of_fn_takes_the_expected_type(self):
        assert accepted("(list[real] v (map {1 2} (fn x (* 2 x))))").get("v").value.value == [2, 4]
