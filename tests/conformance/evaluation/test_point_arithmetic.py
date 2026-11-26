"""Conformance tests of the rule point-arithmetic (docs/spec/evaluation.md)."""

from ._shared import rule, value, xfail


@rule("point-arithmetic")
class TestPointArithmetic:
    def test_points_add_coordinate_by_coordinate(self):
        assert value("(point v (+ [1 2] [3 4]))", "v") == (4, 6)

    def test_a_point_times_a_real(self):
        assert value("(point v (* 2 [1 2]))", "v") == (2, 4)

    @xfail("mtp-5ir0", "no point-of, and no division of a point")
    def test_the_zero_and_the_other_operations(self):
        assert value("(point v (- (/ [2 4] 2) (point-of 0 0)))", "v") == (1, 2)
        assert value("(point v (- [1 2]))", "v") == (-1, -2)
