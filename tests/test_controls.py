import pytest
from helpers import with_scene

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Animation, Bound, Button, Free, Motif, Play, Slider, local_names

DOT = "(motif 'dot' (params (r 1.0) (n 3)) (circle 'c' (r r)))"
BASE = "(real 'k' 1) (circle 'disk' (r 1) (fill 'teal'))"
GROW = "(animation 'grow' (disk.r (transition (from 1) (to 5) (duration 1))))"


def scene(src):
    return compile_model(with_scene(src))


def error(src, match):
    with pytest.raises(CompileError, match=match):
        scene(src)


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


class TestButton:
    def test_presses_a_named_animation(self):
        m = scene(f"{BASE} {GROW} (button 'b' grow)")
        b = get(m, "b", Button)
        assert b.animation is m["grow"]
        assert b.label == Free("b")

    def test_an_animation_written_in_place(self):
        m = scene(
            f"{BASE} (button 'b' (animation (k (transition (to 3) (duration 1)))) (label 'go'))"
        )
        b = get(m, "b", Button)
        assert isinstance(b.animation, Animation) and b.animation.name is None
        assert b.label == Free("go")

    def test_every_transition_needs_a_duration(self):
        error(f"{BASE} (button 'b' (animation (k (transition (to 3)))))", "needs a duration")

    def test_a_default_duration_supplies_one(self):
        src = (
            f"{BASE} (button 'b'"
            " (animation (at-once (default-duration 1) (k (transition (to 3))))))"
        )
        assert scene(src) is not None


class TestSlider:
    def test_scrubs_an_animation(self):
        m = scene(f"{BASE} {GROW} (slider 's' grow (step 4))")
        s = get(m, "s", Slider)
        assert s.animation is m["grow"]
        assert s.step == Free(4)
        assert s.label == Free("s")

    def test_durations_are_not_needed(self):
        assert (
            scene(f"{BASE} (slider 's' (animation (k (transition (from 0) (to 10)))))") is not None
        )

    def test_each_target_needs_a_start(self):
        error(f"{BASE} (slider 's' (animation (k (transition (to 10)))))", "k needs a from")

    def test_only_the_first_transition_of_a_target_needs_a_start(self):
        src = (
            f"{BASE} (slider 's' (animation (in-order (k (transition (from 0) (to 5)))"
            " (k (transition (to 10))))))"
        )
        assert scene(src) is not None

    # (step n) is n evenly spaced places, both ends included; a slider needs at least 2.
    @pytest.mark.parametrize("step", ["0", "1", "2.5", "'none'"])
    def test_step_is_a_number_of_places(self, step):
        error(
            f"{BASE} {GROW} (slider 's' grow (step {step}))",
            "step is a whole number of places, at least 2",
        )


class TestPlay:
    def test_plays_an_animation(self):
        m = scene(
            f"{BASE} {GROW} (animation 'tour' (in-order grow (wait 1) grow))"
            " (play 'p' tour (buttons true))"
        )
        p = get(m, "p", Play)
        assert p.animation is m["tour"]
        assert p.buttons == Free(True)
        assert p.label == Free("p")

    def test_needs_durations(self):
        error(f"{BASE} (play 'p' (animation (k (transition (to 3)))))", "needs a duration")


class TestErrors:
    @pytest.mark.parametrize(
        "src, match",
        [
            ("(button 'b')", "button needs an animation"),
            ("(button 'b' k)", "'k' is not an animation"),
            ("(steps 'x' (states a))", "steps"),
            (f"{GROW} (button 'b' grow (duration 1))", "unexpected value in button"),
        ],
    )
    def test_invalid(self, src, match):
        error(f"{BASE} {src}", match)


class TestReactivity:
    def test_a_written_parameter_is_not_folded(self):
        m = scene(
            f"{DOT} (dot 'd') (button 'b' (animation (d.r (transition (to 3) (duration 1)))))"
        )
        assert isinstance(local_names(get(m, "d", Motif))["c"].r, Bound)  # ty: ignore[unresolved-attribute]

    def test_an_unwritten_parameter_is_folded(self):
        m = scene(
            f"{DOT} (dot 'd') (dot 'e')"
            " (button 'b' (animation (d.r (transition (to 3) (duration 1)))))"
        )
        assert local_names(get(m, "e", Motif))["c"].r == Free(1.0)  # ty: ignore[unresolved-attribute]


class TestExport:
    def test_controls_point_at_their_animations(self):
        doc = to_json(
            scene(
                f"{BASE} {GROW} (button 'b' grow) (slider 's' grow (step 4))"
                " (play 'p' (animation (k (transition (to 2) (duration 1)))) (buttons true))"
            )
        )
        names, objs = doc["names"], doc["objects"]
        assert objs[names["b"]]["animation"] == names["grow"]
        assert objs[names["s"]]["animation"] == names["grow"]
        assert objs[names["s"]]["attrs"]["step"] == 4
        p = objs[names["p"]]
        inline = objs[p["animation"]]
        assert inline["kind"] == "animation" and inline["name"] is None
        assert p["attrs"]["buttons"] is True
