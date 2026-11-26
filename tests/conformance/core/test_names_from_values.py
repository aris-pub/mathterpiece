"""Conformance tests of the rule names-from-values (docs/spec/core.md)."""

from ._shared import mtpc, rejected, rule


@rule("names-from-values")
class TestNamesFromValues:
    def test_a_name_built_from_the_variable_of_a_foreach(self):
        d = mtpc(
            "(scene s (foreach k 3 (circle @'d-{k}' (pos [k 0])"
            " (r (if (= k 0) 1 (/ @'d-{(- k 1)}'.r 2))))))"
        )
        assert set(d["names"]) >= {"d-0", "d-1", "d-2"}

    def test_a_name_that_names_no_declaration_before_it_is_an_error(self):
        rejected("(scene s (foreach k 2 (circle @'d-{k}' (r @'d-{(+ k 1)}'.r))))")
