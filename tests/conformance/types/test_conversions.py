"""Conformance tests of the rule conversions (docs/spec/types.md)."""

from ._shared import COLOR_OF, accepted, compile_error, pytest, rule


@rule("conversions")
class TestConversions:
    @pytest.mark.parametrize(
        "src", ["(string s 'red') (scene sc (circle d (fill s)))", "(int v 2.5)", "(string v 3)"]
    )
    def test_no_value_changes_type_by_itself(self, src):
        compile_error(src)

    def test_a_form_that_asks_for_it(self):
        accepted("(int v (round 2.5))")

    @COLOR_OF
    def test_color_of(self):
        accepted("(string s 'red') (scene sc (circle d (fill (color-of s))))")
