"""Conformance tests of the rule form-types (docs/spec/types.md)."""

from ._shared import COLOR_OF, accepted, compile_error, pytest, rule


@rule("form-types")
class TestFormTypes:
    @pytest.mark.parametrize(
        "src",
        [
            "(bool on true) (int v (if on 1 2.5))",
            "(real v (as int 2.5))",
            "(list v {})",
            "(real v (type-of 3))",
            "(real a 1) (real v (= a 2))",
            "(real|none r none) (string v f'{r}')",
            "(list[int] xs {1 2}) (string|none v (. xs 0))",
        ],
    )
    def test_an_expression_whose_type_is_not_a_subtype_of_the_expected_type(self, src):
        compile_error(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(int n 1) (real v n)",
            "(list[real] v (as list[real] {}))",
            "(list[real] v {})",
            "(string v (type-of 3))",
            "(real a 1) (bool v (= a 2))",
            "(func f ((real x)) (/ 1 x)) (real v (or? (f 0) 5))",
            "(real|none r none) (string|none v f'{r}')",
            "(point p [1 2]) (real v p.x)",
            "(list[int] xs {1 2}) (int|none v (. xs 0))",
            "(real a 1) (real v (free (* 2 a)))",
        ],
    )
    def test_an_expression_whose_type_is_a_subtype_of_the_expected_type(self, src):
        accepted(src)

    @COLOR_OF
    def test_color_of(self):
        accepted("(color v (color-of 'red'))")
        accepted("(string s 'red') (color|none v (color-of s))")
        compile_error("(string s 'red') (color v (color-of s))")
