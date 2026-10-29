import math
import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import Evaluator, render
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Bound, Circle, Free, Motif, Text, local_names


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


def folded(expr):
    """The value of a real attribute computed from expr at compile time."""
    return get(scene(f"(circle 'c' (r {expr}))"), "c", Circle).r


def evaluated(src, name="v", attr="value"):
    m = scene(src)
    return Evaluator(m, random.Random(0)).value(m[name], attr)


class TestListValues:
    @pytest.mark.parametrize(
        "expr, value",
        [
            ("(let ((p [3 4])) p.x)", 3.0),
            ("(let ((p [3 4])) p.y)", 4.0),
            ("(let ((p [3 4 5])) p.z)", 5.0),
            ("(let ((p [3 4])) p[1])", 4.0),
            ("(let ((p (+ [1 2] [3 4]))) p.y)", 6.0),
            ("(let ((p (- [5 5] [1 2]))) p.y)", 3.0),
            ("(let ((p (- [1 2]))) p.x)", -1.0),
            ("(let ((p (* 2 [1 2]))) p.y)", 4.0),
            ("(let ((p (* [1 2] 3))) p.y)", 6.0),
            ("(let ((p (/ [2 4] 2))) p.y)", 2.0),
            ("(dist [0 0] [3 4])", 5.0),
            ("(dist [0 0 0] [1 2 2])", 3.0),
            ("(let ((p (lerp [0 0] [10 20] 0.5))) p.y)", 10.0),
            ("(let ((p (polar 2 90))) p.y)", 2.0),
            ("(let ((p (polar 2 90))) p.x)", 0.0),
            ("(let ((p (polar 2 180))) p.x)", -2.0),
        ],
    )
    def test_folded(self, expr, value):
        assert folded(expr) == Free(pytest.approx(value))

    def test_elements_from_expressions(self):
        assert folded("(let ((k 2) (p [k (* 3 k)])) p.y)") == Free(6.0)

    def test_bound(self):
        c = get(scene("(real 'k') (circle 'c' (r (let ((p [k 1])) p.x)))"), "c", Circle)
        assert isinstance(c.r, Bound)

    def test_const_and_param_default(self):
        m = scene(
            "(const 'o' [1 2]) (motif 'm' (params (c [5 6])) (circle 'e' (r c.y))) (m 'i')"
            " (circle 'd' (r o.x))"
        )
        assert get(m, "d", Circle).r == Free(1.0)
        e = local_names(get(m, "i", Motif))["e"]
        assert isinstance(e, Circle) and e.r == Free(6.0)

    def test_in_a_string(self):
        t = get(scene("(text 't' (let ((p [1 2])) $'at {p}'))"), "t", Text)
        assert t.value == Free("at (1.0, 2.0)")

    def test_function_parameter(self):
        src = (
            "(func 'mid' (params (p [0 0]) (q [0 0])) (lerp p q 0.5))"
            " (circle 'c' (r (let ((m (mid [0 0] [4 8]))) m.y)))"
        )
        assert get(scene(src), "c", Circle).r == Free(4.0)

    @pytest.mark.parametrize(
        "expr",
        [
            "[1 2]",
            "(+ [1 2] [1 2 3])",
            "(+ [1 2] 1)",
            "(let ((p (* [1 2] [3 4]))) p.x)",
            "(let ((p (/ 2 [1 2]))) p.x)",
            "(let ((p [1 2])) p.z)",
            "(let ((p [1 2])) p[2])",
            "(let ((p [1 'a'])) p.x)",
            "(let ((p [[1 2] 3])) p.y)",
            "(let ((p [true 1])) p.x)",
            "(< [1 2] [3 4])",
            "(dist [0 0] [0 0 0])",
            "(let ((p (lerp [0 0] [1 1] [1 1]))) p.x)",
            "(let ((p [1 2])) p.w)",
        ],
    )
    def test_invalid(self, expr):
        error(f"(circle 'c' (r {expr}))")

    def test_equality(self):
        c = get(scene("(circle 'c' (fill (if (= [1 2] [1 2]) 'red' 'blue')))"), "c", Circle)
        assert c.fill == Free("red")


class TestPos:
    def test_sets_x_and_y(self):
        c = get(scene("(circle 'c' (pos [3 4]))"), "c", Circle)
        assert (c.x, c.y) == (Free(3.0), Free(4.0))

    def test_with_polar(self):
        c = get(scene("(circle 'c' (pos (polar 2 90)))"), "c", Circle)
        assert (c.x, c.y) == (Free(0.0), Free(2.0))

    def test_bound_is_computed_once(self):
        c = get(scene("(real 'k') (circle 'c' (pos (polar 1 k)))"), "c", Circle)
        assert isinstance(c.x, Bound) and isinstance(c.y, Bound)

    def test_read(self):
        assert isinstance(get(scene("(circle 'a') (circle 'c' (r a.pos.x))"), "c", Circle).r, Bound)

    def test_self(self):
        c = get(scene("(circle 'c' (x 3) (r self.pos.x))"), "c", Circle)
        assert isinstance(c.r, Bound)

    def test_motif_instance(self):
        m = scene("(motif 'dot' (circle 'e')) (dot 'd' (pos [1 2]))")
        d = get(m, "d", Motif)
        assert (d.x, d.y) == (Free(1.0), Free(2.0))

    def test_text(self):
        t = get(scene("(text 't' 'hi' (pos [1 2]))"), "t", Text)
        assert (t.x, t.y) == (Free(1.0), Free(2.0))

    @pytest.mark.parametrize(
        "attrs",
        [
            "(pos [1 2]) (x 3)",
            "(y 3) (pos [1 2])",
            "(pos [1 2]) (pos [1 2])",
            "(pos [1 2 3])",
            "(pos 1)",
        ],
    )
    def test_invalid(self, attrs):
        error(f"(circle 'c' {attrs})")

    def test_cycle(self):
        error("(circle 'c' (pos [self.y 1]))", match="circular")

    def test_canvas_has_no_pos(self):
        error("(canvas 'cnv' (pos [1 2]))")


class TestInStoredExpressions:
    def test_loop_variable_in_a_list(self):
        m = scene("(real 'k') (repeat i 2 (circle $'c{i}' (pos [i k])))")
        c = get(m, "c1", Circle)
        assert isinstance(c.x, Bound)
        assert Evaluator(m, random.Random(0)).value(c, "x") == 1.0

    def test_ref_in_a_list(self):
        m = scene("(real 'k') (circle 'a' (x 2)) (circle 'c' (pos [(ref 'a.x') k]))")
        assert Evaluator(m, random.Random(0)).value(m["c"], "x") == 2.0


class TestEvaluation:
    def test_bound_list(self):
        assert evaluated("(real 'k' 2) (real 'v' (let ((p (+ [k 1] [1 k]))) p.y))") == 3.0

    def test_pos_reads_scene_coordinates_from_outside(self):
        src = "(motif 'dot' (circle 'e' (x 1))) (dot 'd' (pos [3 4])) (real 'v' d.e.pos.x)"
        assert evaluated(src) == 4.0

    def test_bound_pos_shares_one_value(self):
        m = scene("(circle 'c' (pos [(rand) (rand)]) (r (- self.pos.x self.x)))")
        ev = Evaluator(m, random.Random(0))
        assert ev.value(m["c"], "r") == 0.0

    def test_polar_bound(self):
        assert evaluated("(real 'k' 90) (real 'v' (let ((p (polar 2 k))) p.y))") == 2.0

    def test_dist_between_object_and_list(self):
        assert evaluated("(circle 'a' (x 3) (y 4)) (real 'v' (dist a [0 0]))") == 5.0

    def test_lerp_bound(self):
        assert evaluated("(real 'k' 0.25) (real 'v' (let ((p (lerp [0 0] [8 4] k))) p.x))") == 2.0

    def test_string(self):
        src = "(real 'k' 0) (text 't' (let ((p (polar 1 k))) $'{p}'))"
        assert evaluated(src, "t") == "(1.0, 0.0)"

    def test_drawn_at_pos(self):
        ((_, ax),) = render(scene("(real 'k' 90) (circle 'c' (pos (polar 2 k))) (canvas 'cnv' c)"))
        (circle,) = ax.patches
        center = (circle.get_transform() - ax.transData).transform((0, 0))
        assert tuple(center) == pytest.approx((0, 2))

    def test_real_value_from_a_list(self):
        assert evaluated("(real 'v' (let ((p [1 2])) p.y))") == 2.0
        assert math.isclose(evaluated("(real 'k' 1) (real 'v' (dist [0 0] [k k]))"), math.sqrt(2))
