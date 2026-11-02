"""Built-in functions and constants (docs/reference.md "Operators", "Functions" and
"Constants"; docs/type-system.md 5.c for where they are undefined)."""

import math

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import POINT, REAL, Maybe


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def value(src, name="v"):
    place = model(src).get(name).value
    assert not place.bound, f"{name} is not known when compiling"
    return place.value


def typ(src, name="v"):
    place = model(src).get(name).value
    return place.expr.type if place.bound else place.type


class TestNumbers:
    def test_sqrt(self):
        assert value("(real v (sqrt 9))") == 3
        error("(real v (sqrt -1))", "undefined")
        assert typ("(real k) (real|none v (sqrt k))") == Maybe(REAL)
        assert typ("(real k 1 (>= 0)) (real v (sqrt k))") == REAL

    def test_round_halves_away_from_zero(self):
        assert value("(int v (round 2.5))") == 3
        assert value("(int v (round -2.5))") == -3
        assert value("(real v (round 2.675 2))") == 2.68
        assert value("(real v (round 1234 -2))") == 1200

    def test_floor_ceil_exp_log(self):
        assert value("(int v (floor 2.7))") == 2 and value("(int v (ceil 2.1))") == 3
        assert value("(real v (log 100 10))") == pytest.approx(2)
        error("(real v (log 0))", "undefined")
        assert typ("(real k) (real|none v (exp k))") == Maybe(REAL)
        assert typ("(real k 1 (<= 100)) (real v (exp k))") == REAL

    def test_min_max(self):
        assert value("(real v (max 1 5 3))") == 5
        assert value("(real v (min [4 2 8]))") == 2
        assert value("(real v (min [4 2 8] 1))") == 1

    def test_min_max_of_lists_and_reals_mixed(self):
        m = model("(scene s (group g (circle a) (circle b)) (real v (min g.r 5)))")
        assert m.get("v").value.expr.type == REAL

    def test_lerp(self):
        assert value("(real v (lerp 0 10 0.5))") == 5
        assert value("(point v (lerp [0 0] [2 4] 0.5))") == (1, 2)

    def test_rand(self):
        m = model("(real v (rand)) (real w (rand 2 3))")
        assert m.get("v").value.expr.op == "rand"
        assert m.get("w").value.expr.range == (2, 3)
        error("(func f (real x) (+ x (rand)))", "rand inside a function")


class TestAngles:
    def test_degrees_are_exact_at_right_angles(self):
        assert value("(real v (sind 180))") == 0
        assert value("(real v (cosd 90))") == 0
        assert value("(real v (sin (/ pi 2)))") == 1

    def test_where_they_are_undefined(self):
        error("(real v (tand 90))", "undefined")
        error("(real v (secd 270))", "undefined")
        error("(real v (cotd 0))", "undefined")
        error("(real v (asind 2))", "undefined")
        assert typ("(real a) (real|none v (secd a))") == Maybe(REAL)
        assert typ("(real a 0 (>= 0) (<= 80)) (real v (secd a))") == REAL

    def test_ranges(self):
        model("(real a) (scene s (circle c (r (+ 1 (sind a)))))")

    def test_conversions(self):
        assert value("(real v (turn 0.5))") == 180
        assert value("(real v (to-rad 180))") == pytest.approx(math.pi)


class TestPointsTransformsColors:
    def test_polar_and_dist(self):
        assert value("(point v (polar 2 90))") == (0, 2)
        assert value("(real v (dist [0 0] [3 4]))") == 5
        assert typ("(point p) (point|none v (to-polar p))") == Maybe(POINT)

    def test_point_arithmetic(self):
        assert value("(point v (+ [1 2] [3 4]))") == (4, 6)
        assert value("(list v (* [1 2 3] [2 2 2]))") == [2, 4, 6]
        error("(list v (+ [1 2] [1 2 3]))", "equal length")

    def test_transforms(self):
        assert value("(transform v (translate 1 2))") == (1, 0, 0, 1, 1, 2)
        assert value("(transform v (transform (scale 2) (translate 1 0)))") == (2, 0, 0, 2, 1, 0)

    def test_colors(self):
        m = model("(scene s (circle c (fill (mix 'black' 'white' 0.5))))")
        assert m.get("c").attrs["fill"].value == "#808080ff"


class TestConstants:
    def test_pi_and_tau(self):
        assert value("(real v pi)") == math.pi
        assert value("(real v τ)") == math.tau


class TestFunctionsAsValues:
    def test_a_built_in_passed_by_name(self):
        m = model("(real k) (list v (map [k 4] sqrt))")
        assert m.get("v").value.expr.args[1].op == "builtinfunc"

    def test_a_declared_function_replaces_a_built_in(self):
        assert value("(func sqrt (real x) (* 2 x)) (real v (sqrt 3))") == 6
