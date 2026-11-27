"""Conformance tests of the rule where-types-are-written (docs/spec/types.md)."""

from ._shared import accepted, compile_error, pytest, rule


@rule("where-types-are-written")
class TestWhereTypesAreWritten:
    def test_types_where_types_are_expected(self):
        accepted("(type pos real (>= 0)) (func f ((pos x)) x) (pos k 1)")

    @pytest.mark.parametrize("src", ["(real a real)", "(real a 1) (real b (+ a int))"])
    def test_a_type_where_a_value_is_expected(self, src):
        compile_error(src)

    @pytest.mark.parametrize("src", ["(func f ((3 x)) x)", "(real a 1) (a b 2)"])
    def test_a_value_where_a_type_is_expected(self, src):
        compile_error(src)
