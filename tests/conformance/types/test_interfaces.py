"""Conformance tests of the rule interfaces (docs/spec/types.md)."""

from ._shared import MOVEMENT_INTERFACES, accepted, compile_error, rule


@rule("interfaces")
class TestInterfaces:
    def test_positioned_takes_points_and_shapes(self):
        src = "(func label-at ((positioned o)) o.x) "
        accepted(src + "(point p [1 2]) (real v (label-at p))")
        accepted(src + "(scene s (circle c (r 1) (x 3))) (real v (label-at c))")

    def test_a_value_is_read_only_through_the_attributes_of_its_interface(self):
        compile_error("(func f ((positioned o)) o.r)")

    def test_a_declared_interface(self):
        accepted(
            "(interface radial (real r)) (func area ((radial o)) (* pi o.r o.r))"
            " (motif dot ((real r 0.5 (>= 0))) (circle face (r r)))"
            " (scene s (circle c (r 1)) (dot d (r 0.5))) (real v (area c)) (real w (area d))"
        )

    def test_an_attribute_must_be_of_a_subtype_of_the_listed_type(self):
        src = "(namespace rec (real r 1)) (func f ((radial o)) o.r) (real v (f rec))"
        accepted("(interface radial (real r)) " + src)
        compile_error("(interface radial (real r (>= 0))) " + src)

    @MOVEMENT_INTERFACES
    def test_zero_duration_and_instant(self):
        accepted("(func f ((zero-duration m) (instant n)) 1)")
