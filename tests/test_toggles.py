import pytest

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Bool, Canvas, Free, Toggle
from mathterpiece.parse import parse

SCENE = "(scene 'w' (group 'base' (circle 'c')) (group 'extra' (circle 'd')))"


def compile(src):
    return compile_model(parse(src if "(scene" in src else f"{src} (scene _)"))


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile(src)


class TestBool:
    def test_declares(self):
        b = compile("(bool 'show' true)")["show"]
        assert isinstance(b, Bool) and b.value == Free(True)

    def test_defaults_to_false(self):
        assert compile("(bool 'show')")["show"].value == Free(False)

    def test_states_read_it(self):
        m = compile("(bool 'show' true) (state 'hidden' (= show false))")
        assert len(m["hidden"].conditions) == 1

    def test_not_a_bool(self):
        error("(bool 'show' 3)", "expected bool")


class TestToggle:
    def test_self(self):
        t = compile("(toggle 'show-tan' self (label 'tan'))")["show-tan"]
        assert isinstance(t, Toggle)
        assert (t.target, t.label, t.value) == (None, Free("tan"), Free(False))

    def test_self_with_a_value(self):
        assert compile("(toggle 't' self (value true))")["t"].value == Free(True)

    def test_label_defaults_to_the_name(self):
        assert compile("(toggle 'show-tan' self)")["show-tan"].label == Free("show-tan")

    def test_a_scene_bool(self):
        m = compile("(bool 'show' true) (toggle 't' show)")
        t = m["t"]
        assert (t.target, t.attr, t.label) == (m["show"], "value", Free("show"))

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(toggle 't')", "toggle needs a target"),
            ("(bool 'b') (toggle 't' b (value true))", "only a toggle whose target is self"),
            ("(real 'k') (toggle 't' k)", "a toggle writes a bool, but k is a real"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestWhen:
    def test_a_canvas_shows_a_thing_only_while_its_condition_holds(self):
        m = compile(f"{SCENE} (toggle 'more' self) (canvas 'v' base (when more extra))")
        v = m["v"]
        assert isinstance(v, Canvas)
        assert [o.name for o in v.members] == ["base", "extra"]
        assert v.conditions[0] is None and v.conditions[1] is not None

    def test_a_scene_bool(self):
        assert compile(f"(bool 'b' true) {SCENE} (canvas 'v' (when b base))") is not None

    @pytest.mark.parametrize(
        "src, match",
        [
            (f"(real 'k') {SCENE} (canvas 'v' (when k base))", "true or false"),
            (f"{SCENE} (canvas 'v' (when base))", "when takes a condition and what it shows"),
            (
                "(toggle 't' self) (scene 'w' (circle 'c' (r (if t 1 2))))",
                "the scene cannot read the control 't'",
            ),
            ("(toggle 't' self) (state 's' (= t true))", "the scene cannot read the control 't'"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestExport:
    def test_writes_toggles_and_conditions(self):
        doc = to_json(
            compile(
                f"(bool 'b' true) {SCENE} (toggle 'more' self) (toggle 'tb' b)"
                " (canvas 'v' base (when more extra))"
            )
        )
        objs, names = doc["objects"], doc["names"]
        more, tb, v = objs[names["more"]], objs[names["tb"]], objs[names["v"]]
        assert more["kind"] == "toggle" and more["target"] is None
        assert more["attrs"] == {"label": "more", "value": False}
        assert tb["target"] == [names["b"], "value"]
        assert objs[names["b"]]["kind"] == "bool"
        assert v["shows"] == [names["base"], names["extra"]]
        assert v["when"] == [None, ["read", names["more"], "value"]]


class TestShowingAndHiding:
    def test_a_canvas_wide_transition_and_one_per_when(self):
        m = compile(
            f"{SCENE} (toggle 'more' self) (toggle 'base-on' self)"
            " (canvas 'v' (transition (duration 0.3) (path fade))"
            " (when base-on base)"
            " (when more extra (transition (duration 1) (ease 'ease-out') (path fade))))"
        )
        v = m["v"]
        assert [t.duration for t in v.transitions] == [0.3, 1.0]
        assert v.transitions[1].ease == "ease-out"

    def test_none_without_one(self):
        m = compile(f"{SCENE} (toggle 'more' self) (canvas 'v' base (when more extra))")
        assert m["v"].transitions == [None, None]

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(canvas 'v' (transition (duration 1)) (when t base))", "names its kind with a path"),
            ("(canvas 'v' (transition (path fade)) (when t base))", "needs a duration"),
            (
                "(canvas 'v' (when t base (transition (to 1) (duration 1) (path fade))))",
                "no from or to",
            ),
            ("(canvas 'v' (when t base (transition (duration 1) (path lerp))))", "fade"),
            ("(real 'k') (animation 'a' (k (transition (to 1) (path fade))))", "only for showing"),
        ],
    )
    def test_invalid(self, src, match):
        error(f"{SCENE} (toggle 't' self) {src}", match)

    def test_export(self):
        doc = to_json(
            compile(
                f"{SCENE} (toggle 'more' self)"
                " (canvas 'v' (transition (duration 0.3) (path fade)) base (when more extra))"
            )
        )
        v = doc["objects"][doc["names"]["v"]]
        fade = ["transition", {"duration": 0.3, "path": ["view", "fade"]}]
        assert v["transitions"] == [fade, fade]
