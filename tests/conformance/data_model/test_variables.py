"""Conformance tests of the rule variables (docs/spec/data-model.md)."""

from ._shared import UNNAMED, accepted, compile_error, rule


@rule("variables")
class TestVariables:
    def test_a_bound_variable_follows_its_expression(self):
        m = accepted("(real a 1) (real b (* 2 a))")
        assert m.get("b").value.bound

    @UNNAMED
    def test_a_variable_with_no_name_is_an_error(self):
        compile_error("(real_ 1)")
