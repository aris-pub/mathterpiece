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
        m = scene("(circle 'u' (pos [0 1])) (on-drag u)")
        d = drag(m)
        assert d.node is m["u"]
        assert d.conditions == ()
        assert d.when is None
        assert d.name is None

    def test_drags_a_motif(self):
        m = scene(f"{PIN} (pin 'p') (on-drag p)")
        assert drag(m).node is m["p"]

    def test_drags_a_member_by_path(self):
        m = scene(f"{PIN} (pin 'p') (on-drag p.head)")
        assert drag(m).node is local_names(m["p"])["head"]

    def test_conditions(self):
        m = scene("(circle 'c') (circle 'u' (pos [0 1])) (on-drag u (<= (dist u c) 3) (>= u.y 0))")
        assert len(drag(m).conditions) == 2

    def test_when_a_condition(self):
        m = scene("(real 'k' 1) (circle 'u') (on-drag u (when (> k 0)))")
        assert drag(m).when is not None

    def test_when_a_state(self):
        m = scene("(real 'k' 1) (state 'on' (= k 1)) (circle 'u') (on-drag u (when on))")
        assert isinstance(drag(m).when, State)

    def test_position_stays_reactive(self):
        m = scene("(circle 'u' (pos [0 1])) (circle 'f' (x u.x)) (on-drag u)")
        assert isinstance(m["f"].x, Bound)

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(on-drag)", "on-drag needs"),
            ("(circle 'u') (on-drag nope)", "nope"),
            ("(real 'k') (on-drag k)", "cannot be dragged"),
            ("(circle 'c') (circle 'u' (x c.x)) (on-drag u)", "u.x is computed"),
            ("(circle 'u') (on-drag u 3)", "true or false"),
            ("(circle 'u') (on-drag u (when 3))", "true or false"),
            ("(circle 'u') (on-drag u (when (> 1 0)) (when (> 1 0)))", "twice"),
            ("(circle 'u') (on-drag u (r 3))", "unexpected"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestExport:
    def test_writes_the_listener(self):
        doc = to_json(
            scene("(real 'k' 1) (state 'on' (= k 1)) (circle 'u') (on-drag u (> u.x 0) (when on))")
        )
        (d,) = [o for o in doc["objects"] if o["kind"] == "on-drag"]
        u, on = doc["names"]["u"], doc["names"]["on"]
        assert d["node"] == u
        assert d["conditions"] == [[">", ["read", u, "x", None], 0.0]]
        assert d["when"] == ["holds", on]

    def test_no_when(self):
        doc = to_json(scene("(circle 'u') (on-drag u)"))
        (d,) = [o for o in doc["objects"] if o["kind"] == "on-drag"]
        assert d["when"] is None
