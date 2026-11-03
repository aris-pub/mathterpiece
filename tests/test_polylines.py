"""Polylines and polygons: shapes through a list of points (mtp-4nt; docs/reference.md, "The
scene and shapes"). The author, 2026-11-03: (polyline name (points ps)) is an open path and
(polygon name (points ps)) a closed region of its own; the position of either is the mean of its
points, as a line's and a triangle's is."""

from helpers import bound, doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import _core
from mathterpiece.types import POINT, REAL

PTS = "(points [[0 0] [4 0] [4 2]])"


class TestDeclaring:
    def test_points(self):
        for kind in ("polyline", "polygon"):
            a = model(f"(scene s ({kind} p {PTS}))").get("p").attrs
            assert a["points"].value == [(0, 0), (4, 0), (4, 2)]

    def test_no_points_by_default(self):
        assert model("(scene s (polyline p))").get("p").attrs["points"].value == []

    def test_points_are_a_list_of_points(self):
        error("(scene s (polyline p (points [1 2 3])))", "expected point")
        error("(scene s (polyline p (points 3)))", "expected list")

    def test_they_take_the_stroke_attributes(self):
        a = (
            model(f"(scene s (polyline p {PTS} (stroke 'red') (dash [4 2]) (line-cap 'round')))")
            .get("p")
            .attrs
        )
        assert a["stroke"].value == "#ff0000ff" and a["line-cap"].value == "round"

    def test_a_polygon_is_filled_and_a_polyline_is_not(self):
        assert model(f"(scene s (polygon p {PTS}))").get("p").attrs["fill"].value == "#000000ff"
        # As a line's, a polyline's fill is never drawn.
        assert "fill" in model(f"(scene s (polyline p {PTS}))").get("p").attrs

    def test_points_from_a_map(self):
        m = model("(real k 1) (scene s (polyline p (points (map 5 (fn (int i) [i (* k i)])))))")
        e = m.get("p").attrs["points"].expr
        assert e.op == "map" and _core(_core(e.type).item) == POINT


class TestPosition:
    def test_the_mean_of_the_points(self):
        # A read of a shape's attribute is bound, as the points may be written; the runtime
        # computes the mean (web/test/polyline.test.ts).
        src = f"(scene s (polygon p {PTS}))"
        assert bound(src + " (real v p.x)").args[0].op == "points-mean"
        assert _core(bound(src + " (point v p.pos)").type) == POINT

    def test_while_drawing(self):
        e = bound("(real k 1) (scene s (polyline p (points [[0 0] [k 0]]))) (real v p.x)")
        assert _core(e.type) == REAL

    def test_writing_it_moves_every_point(self):
        model(f"(scene s (polyline p {PTS})) (canvas v s) (on-drag p p.pos)")
        model(f"(scene s (polygon p {PTS})) (animation a (move p.x (to 5) (duration 1)))")

    def test_bound_points_cannot_be_moved_by_their_position(self):
        error(
            "(real k 1) (scene s (polyline p (points [[0 0] [k 0]])))"
            " (animation a (move p.x (to 5) (duration 1)))",
            "bound",
        )

    def test_placement_reads_the_box_of_the_points(self):
        m = model(f"(scene s (polygon p {PTS}) (circle c (pos (top-right p))))")
        assert m.get("c").attrs["x"].bound


class TestAsAClip:
    def test_a_polygon_may_be_a_clip(self):
        model(f"(scene s (group g (clip (polygon_ {PTS})) (circle a)))")

    def test_a_polyline_may_not(self):
        error(f"(scene s (group g (clip (polyline_ {PTS})) (circle a)))", "a clip is a circle")


def test_the_compiled_file():
    d = doc(
        f"(real k 1) (scene s (polyline p (points [[0 0] [k 1]])) (polygon q {PTS})) (real v p.x)"
    )
    assert errors(d) == []
    assert d["objects"][d["names"]["p"]]["kind"] == "polyline"
    assert d["objects"][d["names"]["q"]]["kind"] == "polygon"
