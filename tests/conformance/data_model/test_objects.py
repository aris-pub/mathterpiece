"""Conformance tests of the rule objects (docs/spec/data-model.md)."""

from ._shared import NAME, accepted, rule


@rule("objects")
class TestObjects:
    def test_two_circles_with_the_same_attributes_are_two_objects(self):
        m = accepted("(scene s (circle a (r 1)) (circle b (r 1)))")
        assert m.id("a") != m.id("b")

    def test_a_shape_has_its_name(self):
        assert accepted("(scene s (circle c (r 1))) (string v c.name)").get("v").value.value == "c"

    @NAME
    def test_a_function_has_its_name(self):
        accepted("(func f ((real x)) x) (string v f.name)")
