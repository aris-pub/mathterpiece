import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import Evaluator, render
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Bound, Ellipse, Free, Line, Rect, Triangle, attributes


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


def stored(obj, *attrs):
    return tuple(getattr(obj, attributes(type(obj))[a].name) for a in attrs)


def free(*values):
    return tuple(Free(pytest.approx(v)) for v in values)


class TestModel:
    def test_defaults(self):
        assert stored(Rect(name="r"), "x", "y", "width", "height") == free(0, 0, 1, 1)
        assert stored(Ellipse(name="e"), "x", "y", "rx", "ry") == free(0, 0, 1, 1)
        assert stored(Line(name="l"), "x1", "y1", "x2", "y2") == free(0, 0, 1, 0)
        assert stored(Triangle(name="t"), "a", "b", "c") == (
            Free((0.0, 0.0)),
            Free((1.0, 0.0)),
            Free((0.0, 1.0)),
        )


class TestConstructors:
    @pytest.mark.parametrize(
        "attrs, expected",
        [
            ("(x 1) (y 2) (width 4) (height 3)", (1, 2, 4, 3)),
            ("(pos [1 2]) (size [4 3])", (1, 2, 4, 3)),
            ("(center [3 3.5]) (size [4 3])", (1, 2, 4, 3)),
            ("(center [3 3.5]) (width 4) (height 3)", (1, 2, 4, 3)),
            ("(from [1 2]) (to [5 5])", (1, 2, 4, 3)),
        ],
    )
    def test_rect(self, attrs, expected):
        r = get(scene(f"(rect 'r' {attrs})"), "r", Rect)
        assert stored(r, "x", "y", "width", "height") == free(*expected)

    @pytest.mark.parametrize(
        "attrs, expected",
        [
            ("(x 1) (y 2) (rx 3) (ry 4)", (1, 2, 3, 4)),
            ("(center [1 2]) (size [6 8])", (1, 2, 3, 4)),
            ("(pos [1 2]) (size [6 8])", (1, 2, 3, 4)),
        ],
    )
    def test_ellipse(self, attrs, expected):
        e = get(scene(f"(ellipse 'e' {attrs})"), "e", Ellipse)
        assert stored(e, "x", "y", "rx", "ry") == free(*expected)

    @pytest.mark.parametrize(
        "attrs, expected",
        [("(x1 1) (y1 2) (x2 3) (y2 4)", (1, 2, 3, 4)), ("(from [1 2]) (to [3 4])", (1, 2, 3, 4))],
    )
    def test_line(self, attrs, expected):
        line = get(scene(f"(line 'l' {attrs})"), "l", Line)
        assert stored(line, "x1", "y1", "x2", "y2") == free(*expected)

    def test_triangle_from_points(self):
        t = get(scene("(triangle 't' (a [0 0]) (b [2 0]) (c [0 2]))"), "t", Triangle)
        assert stored(t, "b") == (Free((2.0, 0.0)),)

    def test_equilateral_triangle(self):
        t = get(scene("(triangle 't' (center [5 5]) (r 2))"), "t", Triangle)
        assert stored(t, "x", "y") == free(5, 5)
        (a,) = stored(t, "a")
        assert isinstance(a, Free) and a.value == pytest.approx((0, 2))

    def test_bound_constructor(self):
        r = get(scene("(real 'k' 2) (rect 'r' (center [k 0]) (size [2 2]))"), "r", Rect)
        assert isinstance(r.x, Bound)
        assert r.width == Free(2.0)

    @pytest.mark.parametrize(
        "src",
        [
            "(rect 'r' (center [0 0]) (x 1))",
            "(rect 'r' (center [0 0]) (pos [0 0]))",
            "(rect 'r' (size [1 1]) (width 2))",
            "(rect 'r' (from [0 0]) (to [1 1]) (width 2))",
            "(rect 'r' (from [0 0]) (to [1 1]) (x 2))",
            "(rect 'r' (from [0 0]))",
            "(rect 'r' (r 1))",
            "(ellipse 'e' (center [0 0]) (y 1))",
            "(ellipse 'e' (size [1 1]) (rx 1))",
            "(line 'l' (from [0 0]) (to [1 1]) (x1 2))",
            "(line 'l' (from [0 0]) (to [1 1]) (pos [1 1]))",
            "(line 'l' (to [1 1]))",
            "(triangle 't' (center [0 0]) (a [1 1]))",
            "(triangle 't' (r 1) (b [1 1]))",
            "(triangle 't' (center [0 0]) (x 1))",
            "(triangle 't' (a 1))",
            "(rect 'r' (size [1 2 3]))",
        ],
    )
    def test_invalid(self, src):
        error(src)


def ev_of(src):
    m = scene(src)
    return m, Evaluator(m, random.Random(0))


def read(src, expr):
    m, ev = ev_of(f"{src} (real 'v' {expr})")
    return ev.value(m["v"], "value")


class TestProperties:
    @pytest.mark.parametrize(
        "expr, value",
        [
            ("(let ((p r.center)) p.x)", 3),
            ("(let ((p r.center)) p.y)", 3.5),
            ("(let ((p r.size)) p.y)", 3),
            ("(let ((p r.to)) p.x)", 5),
            ("(let ((p r.from)) p.y)", 2),
            ("(let ((p r.pos)) p.x)", 1),
        ],
    )
    def test_rect(self, expr, value):
        assert read("(rect 'r' (x 1) (y 2) (width 4) (height 3))", expr) == pytest.approx(value)

    def test_ellipse(self):
        src = "(ellipse 'e' (x 1) (y 2) (rx 3) (ry 4))"
        assert read(src, "(let ((p e.size)) p.y)") == pytest.approx(8)
        assert read(src, "(let ((p e.center)) p.x)") == pytest.approx(1)

    def test_line_points_are_measured_from_its_position(self):
        src = "(line 'l' (pos [10 0]) (x1 1) (y1 2) (x2 3) (y2 4))"
        assert read(src, "(let ((p l.from)) p.x)") == pytest.approx(11)
        assert read(src, "(let ((p l.to)) p.y)") == pytest.approx(4)

    def test_triangle(self):
        src = "(triangle 't' (center [5 5]) (r 2))"
        assert read(src, "(let ((p t.center)) p.y)") == pytest.approx(5)
        assert read(src, "t.r") == pytest.approx(2)

    def test_compile_time_types(self):
        error("(rect 'r') (real 'v' r.center)")
        error("(rect 'r') (real 'v' r.nope)")

    def test_points_convert_into_the_readers_coordinates(self):
        src = "(group 'g' (transform (rotate 90)) (rect 'r' (center [2 0]) (size [1 1])))"
        assert read(src, "(let ((p g[0].center)) p.y)") == pytest.approx(2)

    def test_self(self):
        m, ev = ev_of("(rect 'r' (x 3) (width (let ((p self.from)) p.x)))")
        assert ev.value(m["r"], "width") == 3

    def test_cycle_through_a_property(self):
        error("(rect 'r' (width (let ((c self.center)) c.x)))", match="circular")


def drawn(src):
    ((_, ax),) = render(scene(src), random.Random(0))
    (patch,) = ax.patches
    box = patch.get_path().transformed(patch.get_transform() - ax.transData).get_extents()
    return patch, box


class TestDrawing:
    def test_rect(self):
        _, box = drawn("(rect 'r' (x 1) (y 2) (width 4) (height 3)) (canvas 'cnv' r)")
        assert (box.x0, box.y0, box.x1, box.y1) == pytest.approx((1, 2, 5, 5))

    def test_rect_turns_around_its_corner(self):
        _, box = drawn(
            "(rect 'r' (x 1) (y 0) (width 2) (height 1) (transform (rotate 90))) (canvas 'cnv' r)"
        )
        assert (box.x0, box.y0, box.x1, box.y1) == pytest.approx((0, 0, 1, 2))

    def test_ellipse(self):
        _, box = drawn("(ellipse 'e' (x 1) (y 2) (rx 3) (ry 1)) (canvas 'cnv' e)")
        assert (box.x0, box.y0, box.x1, box.y1) == pytest.approx((-2, 1, 4, 3))

    def test_line(self):
        patch, box = drawn("(line 'l' (from [1 1]) (to [4 5]) (stroke 'red')) (canvas 'cnv' l)")
        assert (box.x0, box.y0, box.x1, box.y1) == pytest.approx((1, 1, 4, 5))
        assert patch.get_facecolor()[3] == 0

    def test_line_moves_with_pos(self):
        _, box = drawn("(line 'l' (pos [10 0]) (x1 0) (y1 0) (x2 1) (y2 1)) (canvas 'cnv' l)")
        assert (box.x0, box.x1) == pytest.approx((10, 11))

    def test_triangle(self):
        _, box = drawn("(triangle 't' (a [0 0]) (b [2 0]) (c [0 3])) (canvas 'cnv' t)")
        assert (box.x0, box.y0, box.x1, box.y1) == pytest.approx((0, 0, 2, 3))

    def test_in_a_motif_with_inherited_fill(self):
        patch, _ = drawn("(motif 'm' (rect 'r')) (m 'd' (fill 'red')) (canvas 'cnv' d)")
        assert patch.get_facecolor()[:3] == (1, 0, 0)
