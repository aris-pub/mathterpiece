"""Conformance tests of the rule range-rules (docs/spec/evaluation.md)."""

from ._shared import accepted, compile_error, pytest, rule


@rule("range-rules")
class TestRangesAreClamped:
    @pytest.mark.parametrize(
        "src",
        [
            "(real k 1) (real v (* k k) (<= 1e150))",
            "(real k 1) (real v (* k k k) (>= -1e150))",
            "(real k 1) (real v (^ 2 k) (<= 1e150))",
            "(real k 1) (real v (exp k) (<= 1e150))",
            "(real k 2 (> 0)) (real h (/ 1 k) (<= 1e150))",
            "(real k -2 (< 0)) (real h (/ 1 k) (>= -1e150))",
            "(real k 1 (>= 1e-300)) (real h (* (/ 1 k) (/ 1 k)) (<= 1e150))",
        ],
    )
    def test_a_range_never_passes_the_number_limit(self, src):
        accepted(src)

    def test_a_range_past_the_largest_binary64_number_gives_no_none(self):
        accepted("(real k 2 (> 0)) (real h (/ 1 k))")
        accepted("(real a) (real b) (real c) (real d (* a b c))")

    def test_a_pole_still_gives_none(self):
        compile_error("(real k 2 (>= 0)) (real h (/ 1 k))")
        compile_error("(real k 1 (>= 0) (<= 180)) (real h (tand k))")
