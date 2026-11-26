"""Conformance tests of the rule equality-by-content (docs/spec/evaluation.md)."""

from ._shared import INVERSE, pytest, rule, value


@rule("equality-by-content")
class TestEqualityByContent:
    @pytest.mark.parametrize(
        "a, b, result",
        [
            ("0", "-0.0", True),
            ("1", "1.0", True),
            ("1/2", "0.5", True),
            ("1+0i", "1.0", True),
            ("1+2i", "1+2i", True),
            ("(+ 0.1 0.2)", "0.3", False),
            ("'a'", "'a'", True),
            ("'a'", "'A'", False),
            ("true", "true", True),
            ("{1 2}", "{1 2}", True),
            ("{1 2}", "{1 2 3}", False),
            ("(as point [1 2])", "(as point [1 2])", True),
            ("(as color #'navy')", "(as color #'#000080')", True),
        ],
    )
    def test_values_compare_by_content(self, a, b, result):
        assert value(f"(bool v (= {a} {b}))", "v") is result
        assert value(f"(bool v (!= {a} {b}))", "v") is (not result)

    def test_none_equals_only_none(self):
        assert value(INVERSE + "(bool v (= (f 0) (f 0)))", "v") is True
        assert value(INVERSE + "(bool v (= (f 0) 1))", "v") is False
