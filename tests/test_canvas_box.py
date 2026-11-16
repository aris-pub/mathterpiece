"""A canvas's view box: all four of x, y, width and height, or none, and then the canvas shows
the box of its shapes (the author, 2026-11-16)."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

S = "(scene s (circle c (r 2)))"
FOUR = ("x", "y", "width", "height")


def canvas(d, name="v"):
    return d["objects"][d["names"][name]]


class TestAllFourOrNone:
    @pytest.mark.parametrize(
        "given, message",
        [
            (["x"], "gives x but not y, width and height"),
            (["width"], "gives width but not x, y and height"),
            (["x", "y"], "gives x and y but not width and height"),
            (["y", "height"], "gives y and height but not x and width"),
            (["x", "y", "width"], "gives x, y and width but not height"),
            (["x", "width", "height"], "gives x, width and height but not y"),
        ],
    )
    def test_some_of_the_four_is_an_error_that_names_the_missing_ones(self, given, message):
        attrs = " ".join(f"({a} 1)" for a in given)
        error(
            f"{S} (canvas v {attrs} c)",
            rf"the canvas v {message}: give all four of x, y, width and height, or none of them"
            r" to show the box of its shapes",
        )

    def test_the_error_is_at_the_canvas(self):
        with pytest.raises(Exception) as found:
            model(f"{S}\n(canvas v (x 1) c)")
        assert found.value.pos.line == 2

    def test_all_four_are_the_view_box(self):
        v = canvas(doc(f"{S} (canvas v (x -3) (y -2) (width 6) (height 4) c)"))
        assert "fit" not in v
        assert {a: v["attrs"][a]["free"] for a in FOUR} == {
            "x": -3,
            "y": -2,
            "width": 6,
            "height": 4,
        }

    def test_none_of_the_four_fits_the_shapes(self):
        v = canvas(doc(f"{S} (canvas v c)"))
        assert v["fit"] is True
        assert not set(FOUR) & set(v["attrs"])
        # The rest of its attributes are as before.
        assert {"transform", "pan", "zoom"} <= set(v["attrs"])

    def test_both_match_the_schema(self):
        assert errors(doc(f"{S} (canvas v c)")) == []
        assert errors(doc(f"{S} (canvas v (x -3) (y -2) (width 6) (height 4) c)")) == []


class TestTheBoxOfAFitCanvasHasNoAttributes:
    # Its box is worked out on the page, so nothing in the source can read or move it.
    def test_reading_its_width_is_an_error(self):
        error(
            f"{S} (canvas v c) (real a v.width)",
            r"the canvas v shows the box of its shapes, so it has no width: give it \(x …\)"
            r" \(y …\) \(width …\) \(height …\) to read or move its view box",
        )

    def test_moving_its_x_is_an_error(self):
        error(
            f"{S} (canvas v c) (animation an (move v.x (to 3) (duration 1)))",
            r"the canvas v shows the box of its shapes, so it has no x",
        )

    def test_a_canvas_with_all_four_may_move_them(self):
        model(
            f"{S} (canvas v (x 0) (y 0) (width 1) (height 1) c)"
            " (real a v.width) (animation an (move v.width (to 3) (duration 1)))"
        )


class TestTheSchema:
    # The .mtpc says "fit" in so many words, so that a runtime that does not know it refuses the
    # file instead of drawing a canvas with no view box.
    def doc(self, **canvas_changes):
        d = doc(f"{S} (canvas v c)")
        canvas(d).update(canvas_changes)
        return d

    def test_fit_with_a_view_box_is_wrong(self):
        d = doc(f"{S} (canvas v (x -3) (y -2) (width 6) (height 4) c)")
        canvas(d)["fit"] = True
        assert errors(d) != []

    def test_fit_is_only_true(self):
        assert errors(self.doc(fit=False)) != []

    def test_a_view_box_shared_by_canvases_is_not_put_into_one_that_fits(self):
        # A value in shared goes back into every canvas that does not give it, so the view box is
        # shared only when every canvas has one.
        box = "(x 0) (y 0) (width 4) (height 4)"
        d = doc(f"{S} (canvas a {box} c) (canvas b {box} c) (canvas f c)")
        assert not set(FOUR) & set(canvas(d, "f")["attrs"])
        assert canvas(d, "a")["attrs"]["width"]["free"] == 4
