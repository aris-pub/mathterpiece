"""Conformance tests of the rule name-lookup (docs/spec/scope.md)."""

from ._shared import accepted, compile_error, pytest, rule, value


@rule("name-lookup")
class TestNameLookup:
    def test_a_parameter_hides_a_variable(self):
        src = "(real x 1 (>= 0) (<= 4)) (func tenfold ((real x)) (* 10 x)) (real v (tenfold 2))"
        assert value(src, "v") == 20

    def test_a_let_name_hides_a_name_of_the_file_scope(self):
        assert value("(real k 5 (const)) (real v (let ((k 2)) k))", "v") == 2

    def test_a_foreach_name_hides_a_name_of_the_file_scope(self):
        src = "(real i 5 (const)) (scene s (foreach i 2 (circle @'c-{i}' (r (+ i 1)))))"
        assert value(src + " (real v c-1.r)", "v") == 2

    def test_an_attribute_of_a_record_hides_a_top_level_name_inside_the_record(self):
        src = "(real w 5 (const)) (namespace n (real w 1 (const)) (real u w)) (real v n.u)"
        assert value(src, "v") == 1

    def test_a_built_in_is_found_when_no_scope_has_the_name(self):
        assert value("(real v (max 1 2))", "v") == 2

    def test_a_declaration_hides_a_built_in_from_there_on(self):
        src = "(real u (max 1 2)) (func max ((real a) (real b)) a) (real v (max 1 2))"
        assert value(src, "u") == 2
        assert value(src, "v") == 1
        assert value("(real pi 3 (const)) (real v (* 2 pi))", "v") == 6

    def test_the_parts_after_the_first_are_not_looked_up(self):
        m = accepted("(real r 5 (const)) (scene s (circle p (r 1))) (real v p.r)")
        assert (m.id("p"), "r") in m.get("v").value.deps

    @pytest.mark.parametrize(
        "src", ["(real v zz)", "(int v (rand-int 1 6))", "(int v (rand.rand-int 1 6))"]
    )
    def test_a_name_that_is_not_found_is_an_error(self, src):
        compile_error(src)
