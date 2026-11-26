"""Conformance tests of the rule dot-name-part (docs/spec/core.md)."""

from ._shared import LOCAL_PART, MEMBER_BY_NAME, SCENE, accepted, rule, value


@rule("dot-name-part")
class TestDotPart:
    def test_an_attribute(self):
        m = accepted(SCENE + "(real v (. q r))")
        assert m.get("v").value.expr.args[:2] == (m.id("q"), "r")

    def test_a_position(self):
        assert value("(list[real] xs {3 4} (const)) (real v (. xs 1))", "v") == 4

    def test_a_member_of_a_group_by_its_position(self):
        m = accepted(SCENE + "(real v (. (. g 0) r))")
        assert m.get("v").value.expr.args[:2] == (m.id("q"), "r")

    @LOCAL_PART
    def test_a_name_that_is_no_attribute_is_an_expression(self):
        assert value("(list[real] xs {3 4} (const)) (real v (let ((r 1)) xs.r))", "v") == 4

    @MEMBER_BY_NAME
    def test_a_member_is_read_by_its_name(self):
        assert (
            value(
                "(color yellow #'red') (namespace n (color yellow #'gold')) (color v (. n yellow))",
                "v",
            )
            == "#ffd700ff"
        )
