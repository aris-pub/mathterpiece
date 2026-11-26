"""Conformance tests of the rule motif-and-variant-types (docs/spec/types.md)."""

from ._shared import VARIANT_PARAMETER, accepted, compile_error, pytest, rule


@rule("motif-and-variant-types")
class TestMotifAndVariantTypes:
    BAR = "(variant bar ((real p 0)) (rect_ (width 0.8) (height (* 5 p)))) "
    M = "(motif m () (circle_ (r 1))) "

    def test_a_variant_is_a_subtype_of_the_type_of_its_shape(self):
        accepted(
            self.BAR + "(func area ((rect q)) (* q.width q.height))"
            " (scene s (bar b1 (p 1))) (real v (area b1))"
        )

    @pytest.mark.parametrize("attr", ["width", "height"])
    def test_a_variant_may_not_set_an_attribute_that_its_shape_sets(self, attr):
        compile_error(self.BAR + f"(scene s (bar b2 ({attr} 2)))")

    def test_a_parameter_named_like_an_attribute(self):
        compile_error("(variant bar ((real width 1)) (rect_ (width width) (height 1)))")

    @VARIANT_PARAMETER
    def test_a_parameter_that_the_shape_does_not_read(self):
        compile_error("(variant bar ((real p 0) (real q 1)) (rect_ (width 0.8) (height (* 5 p))))")

    def test_a_motif_type_is_disjoint_from_every_other_type(self):
        accepted(self.M + "(func f ((m c)) 1) (scene s (m a)) (real v (f a))")
        compile_error(self.M + "(func f ((circle c)) 1) (scene s (m a)) (real v (f a))")
        compile_error(self.M + "(func f ((m c)) 1) (scene s (circle b (r 1))) (real v (f b))")
