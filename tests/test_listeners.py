import pytest
from helpers import with_scene

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Bound, Drag, State, local_names


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def drag(model) -> Drag:
    (found,) = model.listeners
    return found


PIN = "(motif 'pin' (params) (circle 'head' (r 0.2)) (line 'stem' (from [0 0]) (to [0 -1])))"


class TestOnDrag:
    def test_drags_a_shape(self):
        m = scene("(circle 'u' (pos [0 1])) (on-drag u u.pos)")
        d = drag(m)
        assert d.node is m["u"]
        assert d.conditions == ()
        assert d.when is None
        assert d.name is None

    def test_drags_a_motif(self):
        m = scene(f"{PIN} (pin 'p') (on-drag p p.pos)")
        assert drag(m).node is m["p"]

    def test_drags_a_member_by_path(self):
        m = scene(f"{PIN} (pin 'p') (on-drag p.head p.head.pos)")
        assert drag(m).node is local_names(m["p"])["head"]

    @pytest.mark.parametrize("target", ["x", "y", "pos"])
    def test_target(self, target):
        assert drag(scene(f"(circle 'u') (on-drag u u.{target})")).target == target

    def test_moves_one_coordinate_while_the_other_is_computed(self):
        m = scene("(circle 'bar') (circle 'h' (x 0) (y bar.y)) (on-drag h h.x (>= h.x 0))")
        assert drag(m).target == "x"

    def test_conditions(self):
        m = scene(
            "(circle 'c') (circle 'u' (pos [0 1])) (on-drag u u.pos (<= (dist u c) 3) (>= u.y 0))"
        )
        assert len(drag(m).conditions) == 2

    def test_when_a_condition(self):
        m = scene("(real 'k' 1) (circle 'u') (on-drag u u.pos (when (> k 0)))")
        assert drag(m).when is not None

    def test_when_a_state(self):
        m = scene("(real 'k' 1) (state 'on' (= k 1)) (circle 'u') (on-drag u u.pos (when on))")
        assert isinstance(drag(m).when, State)

    def test_position_stays_reactive(self):
        m = scene("(circle 'u' (pos [0 1])) (circle 'f' (x u.x)) (on-drag u u.pos)")
        assert isinstance(m["f"].x, Bound)

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(on-drag)", "on-drag needs"),
            ("(circle 'u') (on-drag u)", "on-drag needs"),
            ("(circle 'u') (on-drag nope nope.pos)", "nope"),
            ("(real 'k') (on-drag k k.value)", "cannot be dragged"),
            ("(circle 'c') (circle 'u' (x c.x)) (on-drag u u.pos)", "computed"),
            ("(circle 'c') (circle 'u' (x c.x)) (on-drag u u.x)", "computed"),
            ("(circle 'c') (circle 'u') (on-drag u c.pos)", "part of u's position"),
            ("(circle 'u') (on-drag u u.r)", "part of u's position"),
            ("(circle 'u') (on-drag u u.pos 3)", "true or false"),
            ("(circle 'u') (on-drag u u.pos (when 3))", "true or false"),
            ("(circle 'u') (on-drag u u.pos (when (> 1 0)) (when (> 1 0)))", "twice"),
            ("(circle 'u') (on-drag u u.pos (r 3))", "unexpected"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestExport:
    def test_writes_the_listener(self):
        doc = to_json(
            scene(
                "(real 'k' 1) (state 'on' (= k 1)) (circle 'u')"
                " (on-drag u u.pos (> u.x 0) (when on))"
            )
        )
        (d,) = [o for o in doc["objects"] if o["kind"] == "on-drag"]
        u, on = doc["names"]["u"], doc["names"]["on"]
        assert d["target"] == [u, "pos"]
        assert d["conditions"] == [[">", ["read", u, "x", None], 0.0]]
        assert d["when"] == ["holds", on]

    def test_no_when(self):
        doc = to_json(scene("(circle 'u') (on-drag u u.pos)"))
        (d,) = [o for o in doc["objects"] if o["kind"] == "on-drag"]
        assert d["when"] is None
