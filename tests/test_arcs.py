"""Arcs and rings (mtp-5zmn; docs/reference.md, "The scene and shapes"). The author, 2026-11-04:
(arc name (r 2) (from 30) (to 120)) is part of a circle's outline, and (ring name (r 2) (width 1))
the region between two circles, the outer at r and the inner at r - width, so width = r is a pie
slice. Both are placed at their center, as a circle is, and take angles in degrees, (from a) (to b),
running from a to b: counterclockwise when b is larger, clockwise when smaller, at most one turn.
With no angles, the arc or ring is whole."""

from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import _core
from mathterpiece.types import POINT, REAL


def attrs(src, name="a"):
    return model(src).get(name).attrs


class TestDeclaring:
    def test_an_arc(self):
        a = attrs("(scene s (arc a (pos [1 2]) (r 2) (from 30) (to 120)))")
        assert (a["x"].value, a["y"].value) == (1, 2)
        assert (a["r"].value, a["from"].value, a["to"].value) == (2, 30, 120)

    def test_a_ring(self):
        a = attrs("(scene s (ring a (r 2) (width 1) (from 30) (to 120)))")
        assert (a["r"].value, a["width"].value, a["from"].value, a["to"].value) == (2, 1, 30, 120)

    def test_whole_by_default(self):
        for kind in ("arc", "ring"):
            a = attrs(f"(scene s ({kind} a))")
            assert (a["r"].value, a["from"].value, a["to"].value) == (1, 0, 360)
        assert attrs("(scene s (ring a))")["width"].value == 0.5

    def test_the_angles_are_numbers(self):
        # Not points, as a line's from and to are.
        error("(scene s (arc a (from [0 0])))", "expected real")
        error("(scene s (ring a (to 'up')))", "expected real")

    def test_the_radius_and_the_width_are_not_negative(self):
        error("(scene s (arc a (r -1)))", "breaks")
        error("(scene s (ring a (width -1)))", "breaks")

    def test_an_arc_takes_the_stroke_attributes(self):
        a = attrs("(scene s (arc a (stroke 'red') (dash [4 2]) (line-cap 'round')))")
        assert a["stroke"].value == "#ff0000ff" and a["line-cap"].value == "round"

    def test_a_ring_is_filled(self):
        assert attrs("(scene s (ring a))")["fill"].value == "#000000ff"

    def test_the_angles_follow_a_variable(self):
        a = attrs("(real t 90) (scene s (arc a (to t)))")
        assert a["to"].bound and _core(a["to"].expr.type) == REAL


class TestPosition:
    def test_the_center(self):
        m = model("(scene s (ring a (pos [3 4]))) (point v a.pos)")
        assert _core(m.get("v").value.expr.type) == POINT

    def test_written_by_a_drag(self):
        model("(scene s (arc a (stroke 'black'))) (on-drag a a.pos)")

    def test_an_angle_is_dragged_through_a_handle(self):
        # A drag writes a number the shape's position depends on, and an arc's center does not
        # depend on its angles, so a handle on the arc's end is dragged instead.
        model(
            "(real t 90) (scene s (arc a (to t) (stroke 'black'))"
            " (circle h (pos (polar 1 t)) (r 0.1))) (on-drag h t)"
        )


class TestClip:
    def test_a_ring_clips_a_container(self):
        model("(scene s (group g (clip (ring_ (r 3) (width 1))) (circle c (r 3))))")

    def test_an_arc_has_no_inside(self):
        error("(scene s (group g (clip (arc_)) (circle c)))", "clip")


def test_the_compiled_file_passes_the_schema():
    src = (
        "(real t 90) (scene s (arc a (r 2) (to t) (stroke 'black'))"
        " (ring b (r 2) (width 1) (from 30) (to 120))"
        " (group g (clip (ring_ (r 3))) (circle c)))"
    )
    d = doc(src)
    assert errors(d) == []
    assert {o["kind"] for o in d["objects"]} >= {"arc", "ring"}
