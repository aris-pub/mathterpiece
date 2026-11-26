"""Conformance tests of the rule one-declaration-per-scope (docs/spec/scope.md)."""

from ._shared import LET_TWICE, accepted, compile_error, pytest, rule


@rule("one-declaration-per-scope")
class TestOneDeclarationPerScope:
    @pytest.mark.parametrize(
        "src",
        [
            "(real a 1) (real a 2)",
            "(real f 1) (func f ((real x)) x)",
            "(type pos real (>= 0)) (real pos 1)",
            "(func f ((real x)) x) (scene s (circle f (r 1)))",
            "(scene s (group g (circle c (r 1))) (group h (circle c (r 1))))",
            "(func f ((real x) (real x)) x)",
            "(motif m () (circle c (r 1)) (circle c (r 2)))",
            "(motif m ((real c 1)) (circle c (r 1)))",
            "(import math dot dot)",
            pytest.param("(real v (let ((a 1) (a 2)) a))", marks=LET_TWICE),
        ],
    )
    def test_a_second_declaration_of_a_name_is_an_error(self, src):
        compile_error(src)

    def test_the_copies_of_a_foreach_declare_different_names(self):
        accepted("(scene s (foreach k 2 (circle @'dot-{k}' (r 1))))")
