"""Conformance tests of the rule identity (docs/spec/data-model.md)."""

from ._shared import accepted, rule


@rule("identity")
class TestIdentity:
    def test_two_circles_declared_alike_are_two_objects(self):
        m = accepted("(scene s (circle c (r 1)) (circle d (r 1)))")
        assert m.id("c") != m.id("d")

    def test_parts_of_values_can_be_read(self):
        accepted("(point p [1 2]) (real v p.y) (complex z 1+2i) (real w z.im)")
