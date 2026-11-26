"""Conformance tests of the rule compiler-never-acts-while-drawing
(docs/spec/compiler-runtime.md)."""

from ._shared import RAND, mtpc, obj, rule


@rule("compiler-never-acts-while-drawing")
class TestCompilerNeverActsWhileDrawing:
    def test_no_animation_is_played(self):
        d = mtpc("(real k 0) (animation a (move k (to 5) (duration 1))) (button b (animation a))")
        assert obj(d, "k")["value"]["free"] == 0

    def test_a_token_is_written_with_its_declared_value_and_never_folded(self):
        d = mtpc("(color ink #'navy') (scene s (circle c (r 1) (fill ink)))")
        assert obj(d, "ink")["value"]["free"] == "#000080ff"
        fill = obj(d, "c")["attrs"]["fill"]
        assert fill["bound"][0] == "read" and fill["bound"][2] == d["names"]["ink"]

    def test_no_random_value_is_drawn(self):
        d = mtpc(RAND + "(rand-seed sd 1) (real v (rand))")
        assert "bound" in obj(d, "v")["value"]
