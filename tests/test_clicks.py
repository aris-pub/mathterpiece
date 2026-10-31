import pytest

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Animation, Click
from mathterpiece.parse import parse

SCENE = "(real 'k' 0) (scene 's' (group 'points' (circle _ (pos [0 0])) (circle _ (pos [1 0]))))"
GROW = "(animation 'grow' (k (transition (to 1) (duration 1))))"


def compile(src):
    return compile_model(parse(f"{SCENE} {GROW} {src}"))


def clicks(model) -> list[Click]:
    return [o for o in model if isinstance(o, Click)]


class TestOnClick:
    def test_sets_off_a_named_animation(self):
        m = compile("(on-click points grow)")
        (c,) = clicks(m)
        assert c.node is m["points"] and c.animation is m["grow"] and c.when is None

    def test_an_animation_written_in_place(self):
        (c,) = clicks(compile("(on-click points (animation (k (transition (to 2) (duration 1)))))"))
        assert isinstance(c.animation, Animation) and c.animation.name is None

    def test_one_per_member_with_repeat(self):
        m = compile(
            "(repeat 2 i (on-click points[i] (animation (k (transition (to i) (duration 1))))))"
        )
        assert len(clicks(m)) == 2

    def test_when(self):
        (c,) = clicks(compile("(on-click points grow (when (> k 0)))"))
        assert c.when is not None

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(on-click points)", "on-click needs the object clicked and an animation"),
            ("(on-click k grow)", "cannot be clicked"),
            ("(on-click points nope)", "'nope' is not an animation"),
            ("(on-click points (animation (k (transition (to 1)))))", "needs a duration"),
            ("(on-click points grow (r 1))", "unexpected"),
        ],
    )
    def test_invalid(self, src, match):
        with pytest.raises(CompileError, match=match):
            compile(src)

    def test_export(self):
        doc = to_json(compile("(on-click points grow (when (> k 0)))"))
        (c,) = [o for o in doc["objects"] if o["kind"] == "on-click"]
        assert c["node"] == doc["names"]["points"]
        assert c["animation"] == doc["names"]["grow"]
        assert c["when"] == [">", ["read", doc["names"]["k"], "value"], 0.0]


def test_clicks_are_listeners():
    m = compile("(on-click points grow)")
    assert m.listeners == clicks(m)
