"""Conformance tests of the rule type-values (docs/spec/types.md)."""

from ._shared import (
    DEFAULT_UPPER,
    TYPES_REDESIGN,
    accepted,
    compile_error,
    pytest,
    rule,
    same_meaning,
)


@rule("type-values")
class TestTypeValues:
    @pytest.mark.parametrize(
        "src, expected",
        [
            ("(real v)", 0),
            ("(int v)", 0),
            ("(ratio v)", 0),
            ("(complex v)", 0),
            ("(real v (>= 1))", 1),
            ("(bool v)", False),
            ("(string v)", ""),
            ("(point v)", (0, 0)),
            ("(list[int] v)", []),
            ("(list[int] v (length 2))", [0, 0]),
            ("(real|none v)", None),
            ("(string v (one-of 'b' 'a'))", "b"),
            ("(func f ((real x) (real y)) y) (real v (f 1))", 0),
        ],
    )
    def test_the_default_value_of_a_type(self, src, expected):
        assert accepted(src).get("v").value.value == expected

    def test_the_default_color_is_black(self):
        same_meaning("(color v)", "(color v #'#000000')")

    @DEFAULT_UPPER
    def test_a_type_that_holds_only_an_upper_bound(self):
        assert accepted("(real v (<= -1))").get("v").value.value == -1

    @TYPES_REDESIGN
    def test_the_first_choice_that_meets_the_other_conditions(self):
        assert accepted("((int (one-of 5 1) (<= 3)) v)").get("v").value.value == 1

    @pytest.mark.parametrize(
        "src", ["(real v (> 1))", "(motif m ((circle c)) (circle_ (r 1))) (scene s (m a))"]
    )
    def test_leaving_out_a_value_of_a_type_with_no_default_is_an_error(self, src):
        compile_error(src)
