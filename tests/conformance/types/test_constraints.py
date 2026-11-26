"""Conformance tests of the rule constraints (docs/spec/types.md)."""

from ._shared import TYPES_REDESIGN, accepted, compile_error, pytest, rule


@rule("constraints")
class TestConstraints:
    def test_the_conditions(self):
        accepted("(real k 1 (>= 0) (< 2))")
        accepted("(list[int] xs {1 2} (length 2))")
        accepted("(string s 'a' (one-of 'a' 'b'))")

    @TYPES_REDESIGN
    @pytest.mark.parametrize(
        "src",
        ["(string s 'ab' (length 2))", "(int n 1 (one-of 1 2))", "(bool b true (one-of true))"],
    )
    def test_length_on_strings_and_one_of_on_other_types(self, src):
        accepted(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(bool b true (>= 0))",
            "(string s 'a' (>= 0))",
            "(real k 1 (length 2))",
            "(real k 1 (foo 2))",
            "(func f (((circle (>= 0)) c)) 1)",
            "(real a 1) (real k 1 (>= a))",
            "(list[int] xs {} (length -1))",
        ],
    )
    def test_any_other_condition_is_an_error(self, src):
        compile_error(src)

    @TYPES_REDESIGN
    @pytest.mark.parametrize("src", ["((real (const)) k 1)", "((real (wrap 0 360)) k 1)"])
    def test_const_and_wrap_are_not_conditions(self, src):
        compile_error(src)
