"""Built-in functions and constants (docs/reference.md "Operators", "Functions" and
"Constants"; docs/type-system.md 5.c for where they are undefined)."""

import json
import math

import pytest
from helpers import doc, error, model, typ, value
from mtpc_check import errors

from mathterpiece.types import BOOL, INT, POINT, REAL, ListT, Maybe


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

    def test_euler(self):
        # mtp-asl: decided 2026-10-28, lost in the rebuild.
        assert value("(real v euler)") == math.e


class TestFunctionsAsValues:
    def test_a_built_in_passed_by_name(self):
        m = model("(real k) (list v (map [k 4] sqrt))")
        assert m.get("v").value.expr.args[1].op == "builtinfunc"

    def test_a_declared_function_replaces_a_built_in(self):
        assert value("(func sqrt (real x) (* 2 x)) (real v (sqrt 3))") == 6


def test_lerp_folds_points_known_when_compiling():
    # mtp-7id: the compiler used to crash subtracting the two lists.
    m = model(
        "(func top ((real k)) (/ 6 k)) (func pt ((real a) (real b)) (lerp [a b] [(* 2 a) b] 0.5))"
        " (point q (pt (or? (top 2) 0) 1))"
    )
    assert tuple(m.get("q").value.value) == (4.5, 1)


def test_log_stays_within_the_number_bound():
    # mtp-r0f: type-system.md 5.c, every number lies within ±10^150.
    model("(real x 5 (>= 1) (<= 100)) (real y (* (log x 10) 2))")


class TestNumberTimesList:
    # mtp-y4x: a number times a point or a list multiplies each item.
    def test_folds(self):
        assert value("(point v (* 2 [1 2]))") == (2, 4)
        assert value("(list v (* [1 2 3] 2))") == [2, 4, 6]
        assert value("(list v (* 0.5 [1 2] 2))") == [1, 2]

    def test_the_item_type_widens_with_the_number(self):
        assert typ("(real k) (list v (* k [1 2]))").base == ListT(REAL)
        assert typ("(int k) (list v (* k [1 2]))").base == ListT(INT)

    def test_the_result_keeps_the_length(self):
        # So a fixed position on it never gives none.
        assert typ("(real k) (list xs (* k [1 2])) (real v xs[1])") == REAL
        assert typ("(real k) (list xs (+ [k 1] [1 2])) (real v xs[1])") == REAL

    def test_only_multiplication_takes_a_number_with_a_list(self):
        error("(list v (+ 1 [1 2]))", "all points or all lists")


class TestInfinity:
    # mtp-asl: infty and ∞ are the float infinity, above the ±10^150 bound. It appears only in
    # values known when compiling; while drawing a result that is ∞ is none.
    def test_the_constants(self):
        assert value("(real v infty (const))") == math.inf
        assert value("(real v ∞ (const))") == math.inf
        assert value("(real v (- infty) (const))") == -math.inf

    def test_arithmetic(self):
        assert value("(real v (+ infty 1))") == math.inf
        assert value("(real v (* 2 infty))") == math.inf
        assert value("(real v (/ 1 infty))") == 0
        assert value("(bool v (< 1e150 infty))") is True
        assert value("(real v (sqrt infty))") == math.inf

    def test_undefined_forms(self):
        error("(real v (- infty infty))", "undefined")
        error("(real v (* 0 infty))", "undefined")
        error("(real v (sind infty))", "undefined at infty")

    def test_only_a_variable_that_never_changes_holds_it(self):
        error("(real k infty)", "k would hold infty")
        error("(scene s (circle c (r infty)))", "c's r would be infty")

    def test_a_result_that_may_be_infinite_while_drawing_may_be_none(self):
        error("(real x 1) (real v (+ x infty))", "may be none")
        model("(real x 1) (real|none v (+ x infty))")
        assert typ("(real x 1) (bool v (< x infty))") == BOOL

    def test_shown_in_a_string(self):
        assert value("(string v $'{infty}')") == "∞"

    def test_the_compiled_file(self):
        d = doc("(real x 1) (bool b (< x infty))")
        assert errors(d) == []
        bound = d["objects"][d["names"]["b"]]["value"]["bound"]
        assert "infty" in json.dumps(bound)
