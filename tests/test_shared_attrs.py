"""Shared attribute values (mtp-jru8): the compiled file writes a value that every shape of one
kind has once, in the top-level table shared, and leaves it out of those shapes; the runtime puts
it back when it loads the file. Found 2026-11-05: examples/colormaps.mtp compiled to 2.4 MB, about
2 KB per rect, most of it attributes left at their defaults."""

import json

from helpers import doc
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.mtpc import VERSION, write

GRID = "(scene s (foreach i 5 (circle_ (x i) (r 0.4) (stroke none))))"


def raw(src):
    return json.loads(write(compile_source(src)))


def test_a_value_every_shape_of_a_kind_has_is_written_once():
    d = raw(GRID)
    shared = d["shared"]["circle"]
    assert shared["r"]["free"] == 0.4 and shared["stroke"]["free"] is None
    circles = [o for o in d["objects"] if o["kind"] == "circle"]
    assert all("r" not in c["attrs"] and "stroke" not in c["attrs"] for c in circles)
    # x differs from one circle to the next, so each keeps its own.
    assert [c["attrs"]["x"]["free"] for c in circles] == [0, 1, 2, 3, 4]


def test_a_shape_put_back_together_is_as_written_before():
    d = raw(GRID)
    whole = doc(GRID)
    for o, w in zip(d["objects"], whole["objects"], strict=True):
        if o["kind"] == "circle":
            assert {**d["shared"]["circle"], **o["attrs"]} == w["attrs"]


def test_instances_are_grouped_by_their_motif():
    src = (
        "(motif dot ((real size 1 (>= 0))) (circle c (r size)))"
        " (motif spot ((real size 2 (>= 0))) (circle c (r size)))"
        " (scene s (dot a) (dot b) (spot e) (spot f))"
    )
    d = raw(src)
    assert "instance:dot" in d["shared"] and "instance:spot" in d["shared"]
    assert d["shared"]["instance:dot"]["size"]["free"] == 1
    assert d["shared"]["instance:spot"]["size"]["free"] == 2


def test_only_what_every_shape_of_the_kind_has():
    src = "(scene s (circle a (r 1)) (circle b (r 2)))"
    assert "r" not in raw(src).get("shared", {}).get("circle", {})


def test_the_file_passes_the_schema_and_has_the_new_version():
    d = raw(GRID)
    assert d["mtpc"] == VERSION == 3
    assert errors(d) == []
