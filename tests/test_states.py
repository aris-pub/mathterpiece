import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import State
from mathterpiece.parse import parse

BASE = "(real 'k' 1) (circle 'disk' (r 1) (fill 'teal')) (circle 'other' (r 2))"
STATES = (
    "(state 'start' (= k 1) (= disk.fill 'teal'))"
    " (state 'middle' (= k 2))"
    " (state 'big' (> k 3) (< disk.r other.r))"
)


def scene(src):
    return compile_model(with_scene(src))


def ev_of(src):
    m = scene(src)
    return m, Evaluator(m, random.Random(0))


def get(model, name) -> State:
    obj = model[name]
    assert isinstance(obj, State)
    return obj


class TestStates:
    def test_conditions(self):
        assert len(get(scene(f"{BASE} {STATES}"), "start").conditions) == 2

    def test_any_comparison(self):
        assert len(get(scene(f"{BASE} {STATES}"), "big").conditions) == 2

    def test_conditions_on_computed_values(self):
        assert scene(f"{BASE} (state 's' (= (* 2 disk.r) other.r))") is not None

    @pytest.mark.parametrize("src", ["(state 's')", "(state 's' 3)", "(state 's' (+ 1 2))"])
    def test_invalid(self, src):
        with pytest.raises(CompileError):
            scene(f"{BASE} {src}")

    def test_export_has_only_conditions(self):
        doc = to_json(scene(f"{BASE} (state 's' (= k 2))"))
        s = doc["objects"][doc["names"]["s"]]
        assert s["conditions"] == [["=", ["read", doc["names"]["k"], "value"], 2.0]]
        assert "moves" not in s


class TestEvaluation:
    def test_active(self):
        m, ev = ev_of(f"{BASE} {STATES}")
        assert [s.name for s in m.states if ev.holds(s)] == ["start"]

    def test_tolerance(self):
        m, ev = ev_of(f"{BASE} {STATES}")
        ev.write(m["k"], "value", 2.0000000001)
        assert ev.holds(get(m, "middle"))

    def test_ordinary_equality_is_exact(self):
        m, ev = ev_of("(real 'k' 1) (text 't' (if (= k 2) 'yes' 'no'))")
        ev.write(m["k"], "value", 2.0000000001)
        assert ev.value(m["t"], "value") == "no"

    def test_other_comparisons(self):
        m, ev = ev_of(f"{BASE} {STATES}")
        ev.write(m["k"], "value", 4.0)
        assert ev.holds(get(m, "big"))


class TestStatesAsBools:
    def test_the_scene_reads_a_state_of_scene_values(self):
        src = "(real 'k' 2) (state 'big' (> k 1)) (scene 's' (circle 'c' (r (if big 2 1))))"
        assert compile_model(parse(src))

    def test_the_scene_cannot_read_a_state_that_reads_a_control(self):
        src = (
            "(toggle 'show' self) (state 'on' (= show true))"
            " (scene 's' (circle 'c' (r (if on 2 1))))"
        )
        with pytest.raises(CompileError, match="the scene cannot read the state 'on'"):
            compile_model(parse(src))
