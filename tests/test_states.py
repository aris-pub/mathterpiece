import random

import pytest
from helpers import with_scene
from matplotlib.colors import to_rgba

from mathterpiece.backends.mpl import Evaluator, advance, choose, controls, press, render
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Bound, Button, Free, Motif, Play, State, Steps, local_names

BASE = "(real 'k' 1) (circle 'disk' (r 1) (fill 'teal')) (circle 'other' (r 2))"
STATES = (
    "(state 'start' (= k 1) (= disk.fill 'teal'))"
    " (state 'middle' (= k 2))"
    " (state 'end' (= k 4) (= disk.fill 'red'))"
)


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


class TestStates:
    def test_conditions(self):
        m = scene(f"{BASE} (state 'big' (= k 3) (< (dist disk other) 2))")
        s = get(m, "big", State)
        assert len(s.conditions) == 2
        assert m.states == [s]

    def test_a_reachable_state_knows_its_moves(self):
        m = scene(f"{BASE} (state 'big' (= k 3) (= disk.r other.r))")
        s = get(m, "big", State)
        assert s.problem is None
        assert [(obj.name, attr) for obj, attr, _ in s.moves] == [("k", "value"), ("disk", "r")]

    def test_the_free_side_moves(self):
        s = get(scene(f"{BASE} (state 'big' (= 3 k))"), "big", State)
        assert [(obj.name, attr) for obj, attr, _ in s.moves] == [("k", "value")]

    @pytest.mark.parametrize(
        "conditions, why",
        [
            ("(< k 3)", "="),
            ("(= (dist disk other) 2)", "computed"),
            ("(= k 2) (= k 3)", "twice"),
            ("(= disk.r k) (= k 2)", "reads"),
        ],
    )
    def test_states_that_cannot_be_animated_to(self, conditions, why):
        s = get(scene(f"{BASE} (state 's' {conditions})"), "s", State)
        assert s.problem is not None and why in s.problem

    @pytest.mark.parametrize(
        "src",
        [
            f"{BASE} (state 's' 3)",
            f"{BASE} (state 's' (+ k 1))",
            f"{BASE} (state 's')",
            "(scene _ (state 's' (= 1 1)))",
        ],
    )
    def test_invalid(self, src):
        error(src)

    def test_moved_parameter_is_not_folded(self):
        src = "(motif 'm' (params (r 1.0)) (circle 'c' (r r))) (m 'd') (state 's' (= d.r 3))"
        d = get(scene(src), "d", Motif)
        assert isinstance(local_names(d)["c"].r, Bound)  # ty: ignore[unresolved-attribute]


class TestButtonsGoToStates:
    def test_shorthand(self):
        b = get(scene(f"{BASE} (button 'b' disk.fill 'red')"), "b", Button)
        assert b.state is not None and b.state.name is None
        assert [(obj.name, attr) for obj, attr, _ in b.state.moves] == [("disk", "fill")]
        assert (b.duration, b.ease) == (Free(0.0), Free("linear"))

    def test_named_state(self):
        m = scene(f"{BASE} {STATES} (button 'b' end (duration 2) (ease 'ease-in-out'))")
        b = get(m, "b", Button)
        assert b.state is m["end"]
        assert (b.duration, b.ease, b.label) == (Free(2.0), Free("ease-in-out"), Free("end"))

    @pytest.mark.parametrize(
        "src, match",
        [
            (f"{BASE} (state 'near' (< k 3)) (button 'b' near)", "cannot animate to state 'near'"),
            (f"{BASE} (button 'b' disk.r 1 (ease 'wobbly'))", "ease"),
            (f"{BASE} (button 'b' disk.r 1 (duration -1))", "duration"),
            (f"{BASE} (button 'b' disk.r 1 (duration k))", "duration"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestSteps:
    def test_states_in_order(self):
        m = scene(f"{BASE} {STATES} (steps 'tour' (states start middle end) (duration 0.6))")
        s = get(m, "tour", Steps)
        assert s.states == [m["start"], m["middle"], m["end"]]
        assert (s.duration, s.ease) == (Free(0.6), Free("linear"))

    @pytest.mark.parametrize(
        "src",
        ["(steps 't')", "(steps 't' (states k))", "(state 'n' (< k 3)) (steps 't' (states n))"],
    )
    def test_invalid(self, src):
        error(f"{BASE} {src}")


class TestPlay:
    def test_sequence(self):
        src = (
            f"{BASE} {STATES} (play 'guide' (from start) (wait 1)"
            f" (to middle (duration 2)) (to end))"
        )
        p = get(scene(src), "guide", Play)
        assert p.start is not None and p.start.name == "start"
        assert [(step.kind, step.state.name if step.state else None) for step in p.steps] == [
            ("wait", None),
            ("to", "middle"),
            ("to", "end"),
        ]
        assert p.steps[1].duration == Free(2.0)

    def test_from_is_optional(self):
        p = get(scene(f"{BASE} {STATES} (play 'guide' (to end))"), "guide", Play)
        assert p.start is None

    @pytest.mark.parametrize(
        "steps",
        ["", "(wait)", "(to)", "(to k)", "(jump end)", "(to end) (from start)", "(wait -1)"],
    )
    def test_invalid(self, steps):
        error(f"{BASE} {STATES} (play 'guide' {steps})")


def ev_of(src):
    m = scene(src)
    return m, Evaluator(m, random.Random(0))


class TestEvaluation:
    def test_active(self):
        m, ev = ev_of(f"{BASE} {STATES}")
        assert [s.name for s in m.states if ev.holds(s)] == ["start"]

    def test_tolerance(self):
        m, ev = ev_of(f"{BASE} {STATES}")
        ev.write(m["k"], "value", 2.0000000001)
        assert ev.holds(get(m, "middle", State))

    def test_ordinary_equality_is_exact(self):
        m, ev = ev_of("(real 'k' 1) (text 't' (if (= k 2) 'yes' 'no'))")
        ev.write(m["k"], "value", 2.0000000001)
        assert ev.value(m["t"], "value") == "no"

    def test_targets_are_computed_now(self):
        m, ev = ev_of(f"{BASE} (state 'matched' (= disk.r other.r))")
        ev.write(m["other"], "r", 5.0)
        assert ev.targets(get(m, "matched", State)) == [(m["disk"], "r", 5.0)]


def figure(src):
    ((fig, ax),) = render(scene(src), random.Random(0))
    return fig


def radius(fig):
    ax = fig.axes[0]
    circle = ax.patches[0]
    box = circle.get_path().transformed(circle.get_transform() - ax.transData).get_extents()
    return box.width / 2


SHOWN = "(real 'k' 1) (circle 'disk' (r k) (fill 'teal')) (canvas 'cnv' disk)"


class TestAnimation:
    def test_instant_button(self):
        fig = figure(f"{SHOWN} (button 'b' k 3)")
        press(fig, "b")
        assert radius(fig) == pytest.approx(3)

    def test_button_with_a_duration(self):
        fig = figure(f"{SHOWN} (button 'b' k 3 (duration 2))")
        press(fig, "b")
        advance(fig, 1)
        assert radius(fig) == pytest.approx(2)
        advance(fig, 1.5)
        assert radius(fig) == pytest.approx(3)

    def test_easing(self):
        fig = figure(f"{SHOWN} (button 'b' k 3 (duration 2) (ease 'ease-in'))")
        press(fig, "b")
        advance(fig, 1)
        assert 1 < radius(fig) < 2

    def test_steps(self):
        src = (
            f"{SHOWN} (state 'big' (= k 4)) (state 'small' (= k 1))"
            f" (steps 's' (states small big) (duration 1))"
        )
        fig = figure(src)
        choose(fig, "s", 1)
        advance(fig, 0.5)
        assert radius(fig) == pytest.approx(2.5)

    def test_active_step_is_highlighted(self):
        src = (
            f"{SHOWN} (state 'small' (= k 1)) (state 'big' (= k 4)) (steps 's' (states small big))"
        )
        fig = figure(src)
        small, big = controls(fig)["s"]
        lit, unlit = small.color, big.color
        assert lit != unlit
        choose(fig, "s", 1)
        assert (small.color, big.color) == (unlit, lit)

    def test_play(self):
        src = (
            f"{SHOWN} (state 'small' (= k 1)) (state 'big' (= k 3))"
            " (play 'p' (from small) (wait 1) (to big (duration 2)))"
        )
        fig = figure(src)
        press(fig, "p")
        advance(fig, 0.5)
        assert radius(fig) == pytest.approx(1)
        advance(fig, 1.5)
        assert radius(fig) == pytest.approx(2)
        advance(fig, 5)
        assert radius(fig) == pytest.approx(3)

    def test_user_input_cancels_the_tour(self):
        src = (
            f"{SHOWN} (state 'big' (= k 3)) (play 'p' (to big (duration 2)))"
            " (slider 's' k (min 0) (max 5))"
        )
        fig = figure(src)
        press(fig, "p")
        advance(fig, 1)
        controls(fig)["s"].set_val(0.5)
        advance(fig, 5)
        assert radius(fig) == pytest.approx(0.5)

    def test_play_again_starts_over(self):
        src = (
            f"{SHOWN} (state 'small' (= k 1)) (state 'big' (= k 3))"
            f" (play 'p' (from small) (to big (duration 1)))"
        )
        fig = figure(src)
        press(fig, "p")
        advance(fig, 5)
        press(fig, "p")
        assert radius(fig) == pytest.approx(1)

    def test_colors_move_in_rgb(self):
        fig = figure(
            "(circle 'disk' (fill '#000000')) (canvas 'cnv' disk)"
            " (button 'b' disk.fill '#ffffff' (duration 2))"
        )
        press(fig, "b")
        advance(fig, 1)
        (patch,) = fig.axes[0].patches
        assert patch.get_facecolor()[:3] == pytest.approx((0.5, 0.5, 0.5), abs=0.01)

    def test_fill_from_none_fades_in(self):
        fig = figure(
            "(circle 'disk' (fill 'none')) (canvas 'cnv' disk)"
            " (button 'b' disk.fill 'red' (duration 2))"
        )
        press(fig, "b")
        advance(fig, 1)
        (patch,) = fig.axes[0].patches
        assert patch.get_facecolor() == pytest.approx((1, 0, 0, 0.5), abs=0.01)

    def test_text_switches_at_the_start_and_crossfades(self):
        src = (
            "(text 't' 'small') (canvas 'cnv' t) (state 'big' (= t.value 'large'))"
            " (button 'b' big (duration 2))"
        )
        m = scene(src)
        ((fig, _),) = render(m, random.Random(0))
        press(fig, "b")
        advance(fig, 1)
        texts = fig.axes[0].patches
        assert sorted(str(p.get_label()) for p in texts) == ["large", "small"]
        alphas = [to_rgba(p.get_facecolor())[3] for p in texts]
        assert alphas == pytest.approx([0.5, 0.5], abs=0.01)


class TestPoints:
    def moves(self, model, name):
        state = get(model, name, State)
        return state.problem, [(obj.name, attr) for obj, attr, _ in state.moves]

    @pytest.mark.parametrize("value", ["[1 2]", "(polar 1 90)", "other.pos"])
    def test_condition_on_a_point(self, value):
        m = scene(f"{BASE} (state 's' (= disk.pos {value}))")
        assert self.moves(m, "s") == (None, [("disk", "pos")])

    def test_button_shorthand(self):
        m = scene(f"{BASE} (button 'b' disk.pos [1 2])")
        b = get(m, "b", Button)
        assert b.state is not None
        assert [(o.name, a) for o, a, _ in b.state.moves] == [("disk", "pos")]

    def test_wrong_type(self):
        error(f"{BASE} (state 's' (= disk.pos 3))", match="list2")

    @pytest.mark.parametrize(
        "conditions, why",
        [
            ("(= disk.pos [1 2]) (= disk.x 3)", "twice"),
            ("(= disk.pos [1 2]) (= other.r disk.x)", "another condition moves"),
            ("(= disk.x 3) (= other.pos disk.pos)", "another condition moves"),
        ],
    )
    def test_problems(self, conditions, why):
        problem, _ = self.moves(scene(f"{BASE} (state 's' {conditions})"), "s")
        assert problem is not None and why in problem

    def test_computed_position(self):
        problem, _ = self.moves(
            scene(f"{BASE} (circle 'e' (x disk.x)) (state 's' (= e.pos [1 2]))"), "s"
        )
        assert problem is not None and "computed" in problem
