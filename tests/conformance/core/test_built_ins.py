"""Conformance tests of the rule built-ins (docs/spec/core.md)."""

from ._shared import STEP_EASE, accepted, compile_error, in_folder, pytest, rule, value, xfail


@rule("built-ins")
class TestBuiltIns:
    def test_a_library_name_may_be_declared_again(self):
        assert value("(func max ((real a) (real b)) b) (real v (max 1 2))", "v") == 2

    @pytest.mark.parametrize("head", ["if", "when", "foreach", "circle"])
    def test_a_keyword_may_not(self, head):
        compile_error(f"(func {head} ((real a)) a)")

    def test_a_call_of_a_built_in_is_a_call(self):
        assert value("(real v (max 1 2))", "v") == 2

    def test_the_standard_library_is_ordinary_declarations(self, tmp_path):
        m = in_folder(tmp_path, {}, "(import math)\n(real v (math.clamp 5 0 2))\n")
        assert m.get("v").value.value == 2
        # A declaration of the source may take a name that the library declares.
        accepted("(func clamp ((real x)) x) (real v (clamp 5))")

    def test_a_declared_function_takes_the_name_of_a_built_in(self):
        assert value("(func max ((real a) (real b)) b) (real v (max 1 2))", "v") == 2

    @xfail("mtp-9rj1", "a declaration may take the name of an operator")
    def test_no_declaration_takes_the_name_of_an_operator(self):
        compile_error("(func + ((real a) (real b)) 7)")


@rule("built-ins")
@STEP_EASE
def test_step_is_a_library_function_that_a_declaration_may_replace():
    compile_error(
        "(real step 3) (real k 0) (button b (animation (move k (to 1) (duration 1) (ease (step "
        "2)))))"
    )
