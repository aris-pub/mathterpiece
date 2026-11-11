"""drawn: the share of a shape's outline that is drawn, from its start, as if by a pen
(mtp-ggsb). The author, 2026-11-10 and 2026-11-11: a real from 0 to 1, 1 by default, that
changes the outline only; a text has no outline, so drawn changes nothing on it."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.types import REAL, ListT, Refine

UNIT = Refine(REAL, ((">=", 0), ("<=", 1)))

SHAPES = [
    "(circle c)",
    "(rect c)",
    "(ellipse c)",
    "(line c)",
    "(triangle c)",
    "(polyline c (points [[0 0] [1 1]]))",
    "(polygon c (points [[0 0] [1 0] [0 1]]))",
    "(curve c)",
    "(arc c)",
    "(ring c)",
]


@pytest.mark.parametrize("shape", SHAPES)
def test_every_shape_is_drawn_whole_by_default(shape):
    assert model(f"(scene s {shape})").get("c").attrs["drawn"].value == 1


def test_given():
    assert model("(scene s (circle c (drawn 0.25)))").get("c").attrs["drawn"].value == 0.25


def test_from_0_to_1():
    error("(scene s (circle c (drawn 1.5)))", "breaks")
    error("(scene s (circle c (drawn -0.5)))", "breaks")


def test_a_text_takes_it_and_it_changes_nothing():
    # As dash: a text takes its own, and none from a container's defaults.
    assert model("(scene s (text t 'hi' (drawn 0.5)))").get("t").attrs["drawn"].value == 0.5
    m = model("(scene s (group g (defaults (drawn 0.5)) (text t 'hi') (line l)))")
    assert m.get("t").attrs["drawn"].value == 1
    assert m.get("l").attrs["drawn"].value == 0.5


def test_read():
    e = model("(scene s (circle c)) (real v c.drawn)").get("v").value.expr
    assert e.op == "read" and e.type == UNIT


def test_moved_by_an_animation():
    m = model("(scene s (circle c (drawn 0))) (animation a (move c.drawn (to 1) (duration 1)))")
    assert m.get("a").data["steps"][1] == (m.id("c"), "drawn")


def test_a_containers_is_every_members():
    m = model("(scene s (group g (line a) (circle b)) (list v g.drawn))")
    assert m.get("v").value.expr.type.base == ListT(UNIT)
    m = model(
        "(scene s (group g (line a) (circle b))) (animation n (move g.drawn (to 0) (duration 1)))"
    )
    assert m.get("n").data["steps"][1] == (m.id("g"), "drawn")


def test_a_container_has_none_of_its_own():
    error("(scene s (group g (drawn 0.5) (line a)))", "defaults")


def test_the_compiled_file_passes_the_schema():
    d = doc(
        "(scene s (circle c (drawn 0.5)) (line l (drawn 0) (head-end 'dart')))"
        " (animation a (move c.drawn (to 1) (duration 1)))"
    )
    assert errors(d) == []
    attrs = {o.get("name"): o.get("attrs", {}) for o in d["objects"]}
    assert attrs["c"]["drawn"] == {"type": attrs["c"]["opacity"]["type"], "free": 0.5}


def test_a_motif_instances_is_every_members():
    m = model(
        "(motif dial () (circle c) (line l))"
        " (scene s (dial d)) (animation n (move d.drawn (to 0) (duration 1)))"
    )
    assert m.get("n").data["steps"][1] == (m.id("d"), "drawn")
