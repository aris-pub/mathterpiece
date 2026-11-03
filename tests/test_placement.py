"""Placing shapes relative to others (mtp-50n): eight functions give a point on a shape's box,
the middle of a side or a corner, pushed out by an optional gap (docs/reference.md, "Placing")."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.types import POINT, Maybe

SIDES = ["top", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right"]


@pytest.mark.parametrize("side", SIDES)
def test_each_gives_a_point_that_follows_the_shape(side):
    m = model(f"(scene s (circle c (pos [1 2]) (r 1)) (point p ({side} c)))")
    e = m.get("p").value.expr
    assert e.type == POINT
    assert {(m.id("c"), "x"), (m.id("c"), "r")} <= e.deps


def test_a_gap():
    m = model("(scene s (circle c (r 1)) (real g 0.5) (point p (top c g)))")
    assert (m.id("g"), None) in m.get("p").value.expr.deps


def test_a_container_follows_its_members_and_its_frame():
    m = model(
        "(scene s (group g (translate [10 0]) (circle a (r 1)) (rect b (width 2) (height 4)))"
        " (point p (bottom g)))"
    )
    deps = m.get("p").value.expr.deps
    assert {(m.id("a"), "r"), (m.id("b"), "height"), (m.id("g"), "translate")} <= deps


def test_a_shape_that_may_not_exist_gives_a_point_that_may_be_none():
    m = model("(scene s (real k 1) (circle|none c) (exists-when c (> k 0)) (point|none p (top c)))")
    assert m.get("p").value.expr.type == Maybe(POINT)
    error(
        "(scene s (real k 1) (circle|none c) (exists-when c (> k 0)) (point p (top c)))",
        "may be none",
    )


def test_a_text_has_no_box_yet():
    error("(scene s (text t 'hi') (point p (top t)))", "a text's box")
    error("(scene s (group g (text t 'hi')) (point p (top g)))", "a text's box")


def test_it_takes_a_shape():
    error("(scene s (real k 1) (point p (top k)))", "takes a shape")


def test_the_compiled_file():
    d = doc("(scene s (circle c (r 1)) (point p (top-right c 0.5)))")
    assert errors(d) == []
    assert d["objects"][d["names"]["p"]]["value"]["bound"][0] == "anchor"


class TestRowsAndColumns:
    # mtp-50n: a row or column is a group whose members after the first are each placed a gap
    # after the box of the one before, lined up by an edge (the middle by default).
    def test_a_row_is_a_group_with_a_layout(self):
        m = model("(scene s (row r (gap 0.5) (align 'bottom') (circle a) (circle b)))")
        r = m.get("r")
        assert r.kind == "group"
        assert r.data["layout"]["axis"] == "row"
        assert r.data["layout"]["gap"].value == 0.5
        assert r.data["layout"]["align"].value == "bottom"

    def test_defaults(self):
        layout = model("(scene s (column c (circle a) (circle b)))").get("c").data["layout"]
        assert (layout["axis"], layout["gap"].value, layout["align"].value) == (
            "column",
            0,
            "middle",
        )

    def test_align_by_axis(self):
        error("(scene s (row r (align 'left') (circle a)))", "'left' is not one of")
        error("(scene s (column c (align 'top') (circle a)))", "'top' is not one of")

    def test_a_members_place_follows_the_ones_before(self):
        m = model("(scene s (row r (circle a (r 1)) (circle b)) (point p b.pos))")
        assert (m.id("a"), "r") in m.get("p").value.expr.deps

    def test_no_text_yet(self):
        error("(scene s (row r (circle a) (text t 'hi')))", "a text's box")

    def test_the_compiled_file(self):
        d = doc("(scene s (row r (gap 1) (circle a) (circle b)))")
        assert errors(d) == []
        assert d["objects"][d["names"]["r"]]["layout"]["axis"] == "row"
