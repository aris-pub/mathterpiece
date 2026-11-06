"""Bézier curves (mtp-oya; docs/reference.md, "The scene and shapes"). The author, 2026-11-06:
(curve name (from p) (to q) (controls [k])) is a quadratic and (controls [k1 k2]) a cubic; its
position is the mean of its ends and its controls, as a polyline's is of its points, and a write
to it moves them all; like a line and an arc it takes heads and is never filled."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import _core
from mathterpiece.types import POINT, REAL


class TestDeclaring:
    def test_ends_and_controls(self):
        a = model("(scene s (curve c (from [0 0]) (to [4 0]) (controls [[2 3]])))").get("c").attrs
        assert (a["from"].value, a["to"].value, a["controls"].value) == ((0, 0), (4, 0), [(2, 3)])

    def test_an_arch_by_default(self):
        a = model("(scene s (curve c))").get("c").attrs
        assert (a["from"].value, a["to"].value, a["controls"].value) == ((0, 0), (1, 0), [(0.5, 1)])

    def test_two_controls(self):
        a = model("(scene s (curve c (controls [[1 1] [3 1]])))").get("c").attrs
        assert len(a["controls"].value) == 2

    @pytest.mark.parametrize("controls", ["[]", "[[0 0] [1 1] [2 2]]"])
    def test_one_control_or_two(self, controls):
        error(f"(scene s (curve c (controls {controls})))", "one control or two")

    def test_how_many_known_when_compiling(self):
        assert model("(real k 1) (scene s (curve c (controls [[1 k] [3 k]])))").get("c")
        error(
            "(int n 2) (scene s (curve c (controls (map n (fn (int i) [i i])))))",
            "known when compiling",
        )

    def test_heads_and_stroke(self):
        a = model("(scene s (curve c (stroke 'red') (head-end 'dart')))").get("c").attrs
        assert a["head-end"].value == "dart" and a["stroke"].value == "#ff0000ff"

    def test_no_position_of_its_own(self):
        error("(scene s (curve c (x 1)))", "takes no argument 'x'")

    def test_the_compiled_model_passes_the_schema(self):
        assert errors(doc("(scene s (curve c (controls [[1 1] [3 1]]))) (canvas v s)")) == []


class TestPosition:
    def test_the_mean_of_its_ends_and_controls(self):
        m = model(
            "(scene s (curve c (from [0 0]) (to [4 0]) (controls [[1 3] [3 3]]))"
            " (circle d (pos c.pos)))"
        )
        e = m.get("d").attrs["x"]
        assert e.bound and _core(e.type) == REAL

    def test_while_drawing(self):
        m = model("(real k 1) (scene s (curve c (controls [[k k]]))) (point v c.pos)")
        assert _core(m.get("v").value.type) == POINT

    def test_writing_it_needs_every_point_free(self):
        model("(scene s (curve c)) (on-drag c c.pos)")
        error(
            "(real k 1) (scene s (curve c (to [k 0]))) (on-drag c c.pos)",
            "bound",
        )
