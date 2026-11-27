"""Conformance tests of the rule expected-types (docs/spec/types.md)."""

from ._shared import accepted, compile_error, pytest, rule


@rule("expected-types")
class TestExpectedTypes:
    @pytest.mark.parametrize(
        "src",
        [
            "(real v 'a')",
            "(scene s (circle c (r 'a')))",
            "(func f ((real x)) x) (real v (f 'a'))",
            "(func[real] f ((real x)) 'a')",
            "(real v (if 1 2 3))",
            "(list[real] v {1 'a'})",
        ],
    )
    def test_an_expression_of_another_type_than_its_expected_type(self, src):
        compile_error(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(real v 1)",
            "(scene s (circle c (r 2)))",
            "(func f ((real x)) x) (real v (f 1))",
            "(func[real] f ((real x)) (* 2 x))",
            "(bool b true) (real v (if b 2 3))",
            "(list[real] v {1 2.5})",
        ],
    )
    def test_an_expression_of_its_expected_type(self, src):
        accepted(src)
