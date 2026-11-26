"""Conformance tests of the rule subtypes (docs/spec/types.md)."""

from ._shared import TYPES_REDESIGN, accepted, compile_error, pytest, rule


@rule("subtypes")
class TestSubtypes:
    @pytest.mark.parametrize(
        "src",
        [
            "(func f ((real|none x)) 1) (real v (f 2))",
            "(func f ((list[real] xs)) 1) (real v (f {1 2}))",
            "(int n 1) (real v n)",
            "((real (>= 0)) a 2) ((real (>= -1)) v a)",
            "((int (> 0)) a 2) ((int (>= 1)) v a)",
            "(type u real (>= 0) (<= 1)) (func g ((func[u real] h)) (h 0.5))"
            " (func twice ((real x)) (* 2 x)) (real v (g twice))",
        ],
    )
    def test_a_subtype_is_accepted(self, src):
        accepted(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(string s 'a') (real v s)",
            "((real (>= -1)) a 2) ((real (>= 0)) v a)",
            "(type u real (>= 0) (<= 1)) (func g ((func[real real] h)) (h 0.5))"
            " (func twice ((u x)) (* 2 x)) (real v (g twice))",
        ],
    )
    def test_a_type_that_is_not_a_subtype_is_an_error(self, src):
        compile_error(src)

    @TYPES_REDESIGN
    def test_a_modular_type_is_not_a_subtype_of_real(self):
        accepted("((mod real 0 360) theta 10)")
        compile_error("((mod real 0 360) theta 10) (real v theta)")
