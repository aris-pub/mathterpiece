"""Heads on the ends of lines, polylines and arcs (mtp-brs). The author, 2026-11-05: one
attribute per end, (head-start …) and (head-end …), each 'none', 'dart', 'curved', 'open', 'bar'
or 'dot'; a head takes the shape's stroke and scales with its stroke width, times
(head-size …)."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

KINDS = ["none", "dart", "curved", "open", "bar", "dot"]


@pytest.mark.parametrize(
    "shape", ["(line l (to [3 0]))", "(polyline l (points [[0 0] [1 1]]))", "(arc l)"]
)
def test_the_shapes_with_ends_take_heads(shape):
    a = model(f"(scene s {shape})").get("l").attrs
    assert (a["head-start"].value, a["head-end"].value, a["head-size"].value) == ("none", "none", 1)


@pytest.mark.parametrize("kind", KINDS)
def test_each_kind(kind):
    a = model(f"(scene s (line l (head-end '{kind}') (head-start '{kind}')))").get("l").attrs
    assert a["head-end"].value == kind


def test_an_unknown_kind():
    error("(scene s (line l (head-end 'triangle')))", "one of")


@pytest.mark.parametrize("shape", ["circle", "polygon", "ring", "rect"])
def test_a_closed_shape_has_no_ends(shape):
    error(f"(scene s ({shape} l (head-end 'dart')))", "head-end")


def test_the_size_is_not_negative():
    error("(scene s (line l (head-size -1)))", "breaks")


def test_a_head_can_follow_a_variable():
    m = model("(bool on true) (scene s (line l (head-end (if on 'dart' 'none'))))")
    assert m.get("l").attrs["head-end"].bound


def test_the_compiled_file_passes_the_schema():
    d = doc(
        "(scene s (line l (head-end 'dart') (head-start 'bar') (head-size 1.5))"
        " (arc a (head-end 'curved')) (polyline p (points [[0 0] [1 0]]) (head-end 'dot')))"
    )
    assert errors(d) == []
