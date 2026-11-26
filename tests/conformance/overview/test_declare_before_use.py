"""Conformance tests of the rule declare-before-use (docs/spec/overview.md)."""

from ._shared import accepted, compile_error, pytest, rule


@rule("declare-before-use")
class TestDeclareBeforeUse:
    @pytest.mark.parametrize(
        "src",
        [
            "(real a b) (real b 1)",
            "(real v (f 1)) (func f ((real x)) x)",
            "(func f ((real x)) (g x)) (func g ((real x)) x)",
            "(scene s (m a)) (motif m () (circle_ (r 1)))",
            "(scene s (circle c (r k)) (real k 1 (>= 0)))",
            "(scene s (circle c (r 1)) (circle d (like e)) (circle e (r 2)))",
            "(namespace n (real a n.b) (real b 1))",
            "(real k 0) (button b (animation a)) (animation a (move k (to 1) (duration 1)))",
        ],
    )
    def test_a_name_used_before_its_declaration_is_an_error(self, src):
        compile_error(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(real b 1) (real a b)",
            "(func g ((real x)) x) (func f ((real x)) (g x))",
            "(motif m () (circle_ (r 1))) (scene s (m a))",
            "(real k 1 (>= 0)) (scene s (circle c (r k)))",
        ],
    )
    def test_the_same_forms_in_the_other_order(self, src):
        accepted(src)
