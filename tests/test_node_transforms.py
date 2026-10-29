import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import EvalError, Evaluator, render
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.matrix import IDENTITY
from mathterpiece.model import Bound, Circle, Free, Group, Motif, Text, local_names


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


def member[T](motif, name, cls: type[T]) -> T:
    obj = local_names(motif)[name]
    assert isinstance(obj, cls)
    return obj


def maps(attr, point):
    assert isinstance(attr, Free)
    return pytest.approx(attr.value.apply(*point))


class TestModel:
    @pytest.mark.parametrize("cls", [Circle, Text, Group, Motif])
    def test_default_is_identity(self, cls):
        assert cls(name="o").transform == Free(IDENTITY)


class TestCompile:
    def test_on_a_group(self):
        g = get(scene("(group 'g' (transform (rotate 90)) (circle 'c'))"), "g", Group)
        assert maps(g.transform, (1, 0)) == (0, 1)

    def test_on_a_circle(self):
        c = get(scene("(circle 'c' (transform (scale 2 1)))"), "c", Circle)
        assert maps(c.transform, (1, 1)) == (2, 1)

    def test_motif_default(self):
        m = scene(
            "(motif 'm' (transform (rotate 90)) (circle 'c')) (m 'a') (m 'b' (transform (scale 2)))"
        )
        assert maps(get(m, "a", Motif).transform, (1, 0)) == (0, 1)
        assert maps(get(m, "b", Motif).transform, (1, 0)) == (2, 0)

    def test_motif_default_after_params(self):
        src = (
            "(motif 'm' (params (t 90.0)) (transform (rotate t)) (circle 'c'))"
            " (m 'a') (m 'b' (t 0))"
        )
        m = scene(src)
        assert maps(get(m, "a", Motif).transform, (1, 0)) == (0, 1)
        assert get(m, "b", Motif).transform == Free(IDENTITY)

    def test_motif_default_with_a_bound_param(self):
        src = (
            "(real 'k' 90.0) (motif 'm' (params (t 0.0)) (transform (rotate t))"
            " (circle 'c')) (m 'a' (t k))"
        )
        assert isinstance(get(scene(src), "a", Motif).transform, Bound)

    def test_group_reads_its_own_transform(self):
        m = scene(
            "(group 'g' (transform (rotate 90)) (circle _)) (canvas 'cnv' (transform g.transform))"
        )
        assert m["cnv"] is not None

    @pytest.mark.parametrize(
        "src",
        [
            "(motif 'm' (circle 'c') (transform (rotate 1)))",
            "(motif 'm' (transform (rotate 1)) (params (t 1)) (circle 'c'))",
            "(motif 'm' (transform (rotate 1)) (transform (rotate 2)) (circle 'c'))",
            "(group 'g' (circle 'c') (transform (rotate 1)))",
            "(circle 'c' (transform 1))",
            "(group 'g' (r 1))",
        ],
    )
    def test_invalid(self, src):
        error(src)


def ev_of(src):
    m = scene(src)
    return m, Evaluator(m, random.Random(0))


class TestPositions:
    def test_group_places_its_members(self):
        m, ev = ev_of("(group 'g' (transform (rotate 90)) (circle 'c' (x 1)))")
        assert ev.point(m["c"]) == pytest.approx((0, 1))

    def test_motif_position_is_outside_its_transform(self):
        m, ev = ev_of("(motif 'm' (circle 'c' (x 1))) (m 'd' (pos [3 0]) (transform (rotate 90)))")
        assert ev.point(member(get(m, "d", Motif), "c", Circle)) == pytest.approx((3, 1))

    def test_nested(self):
        src = (
            "(motif 'm' (group 'g' (transform (scale 2)) (circle 'c' (x 1))))"
            " (m 'd' (pos [0 5]) (transform (rotate 90)))"
        )
        m, ev = ev_of(src)
        g = member(get(m, "d", Motif), "g", Group)
        assert ev.point(g.members[0]) == pytest.approx((0, 7))

    def test_read_from_outside_in_scene_coordinates(self):
        src = (
            "(motif 'm' (circle 'c' (x 1))) (m 'd' (pos [3 0])"
            " (transform (rotate 90))) (real 'v' d.c.y)"
        )
        m, ev = ev_of(src)
        assert ev.value(m["v"], "value") == pytest.approx(1)

    def test_read_into_a_turned_group(self):
        src = (
            "(motif 'm' (circle 'c' (x 1)) (group 'g' (transform (rotate 90))"
            " (circle 'e' (x c.x) (y c.y)))) (m 'd')"
        )
        m, ev = ev_of(src)
        e = member(get(m, "d", Motif), "e", Circle)
        assert (ev.value(e, "x"), ev.value(e, "y")) == pytest.approx((0, -1))
        assert ev.point(e) == pytest.approx((1, 0))

    def test_dist_in_scene_coordinates(self):
        src = (
            "(group 'g' (transform (scale 3)) (circle 'c' (x 1))) (circle 'o')"
            " (real 'v' (dist g[0] o))"
        )
        m, ev = ev_of(src)
        assert ev.value(m["v"], "value") == pytest.approx(3)

    def test_pos_read_converts_both_parts(self):
        src = (
            "(group 'g' (transform (rotate 90)) (circle 'c' (x 2)))"
            " (real 'v' (let ((p g[0].pos)) p.y))"
        )
        m, ev = ev_of(src)
        assert ev.value(m["v"], "value") == pytest.approx(2)

    def test_singular_transform_when_reading_into_it(self):
        src = "(circle 'c' (x 1)) (group 'g' (transform (scale 0)) (circle 'e' (x c.x)))"
        m, ev = ev_of(src)
        with pytest.raises(EvalError, match="inverse"):
            ev.value(get(m, "g", Group).members[0], "x")


def drawn(src):
    ((_, ax),) = render(scene(src), random.Random(0))
    return ax


def extents(patch, ax):
    return patch.get_path().transformed(patch.get_transform() - ax.transData).get_extents()


class TestDrawing:
    def test_scale_on_a_motif_scales_shapes(self):
        ax = drawn("(motif 'm' (circle 'c' (x 1))) (m 'd' (transform (scale 2))) (canvas 'cnv' d)")
        (circle,) = ax.patches
        box = extents(circle, ax)
        assert (box.x0, box.x1, box.width) == pytest.approx((0, 4, 4))

    def test_own_transform_turns_a_shape_around_its_anchor(self):
        ax = drawn("(circle 'c' (x 2) (transform (scale 2 1))) (canvas 'cnv' c)")
        (circle,) = ax.patches
        box = extents(circle, ax)
        assert (box.x0, box.x1, box.y0, box.y1) == pytest.approx((0, 4, -1, 1))

    def test_text_turns_with_its_group(self):
        def size(transform):
            ax = drawn(f"(group 'g' {transform} (text 't' 'hhhhhhhh')) (canvas 'cnv' g)")
            (text,) = ax.patches
            box = extents(text, ax)
            return box.width, box.height

        width, height = size("")
        turned = size("(transform (rotate 90))")
        assert turned == pytest.approx((height, width))

    def test_stroke_width_scales_with_the_node(self):
        def width(transform):
            src = (
                f"(group 'g' {transform} (circle 'c' (stroke 'red') (stroke-width 1)))"
                f" (canvas 'cnv' g)"
            )
            ((fig, ax),) = render(scene(src))
            (circle,) = ax.patches
            return circle.get_linewidth()

        assert width("(transform (scale 3))") == pytest.approx(3 * width(""))

    def test_a_member_shown_directly_keeps_its_frame(self):
        ax = drawn("(group 'g' (transform (rotate 90)) (circle 'c' (x 1))) (canvas 'cnv' c)")
        (circle,) = ax.patches
        assert tuple((circle.get_transform() - ax.transData).transform((0, 0))) == pytest.approx(
            (0, 1)
        )
