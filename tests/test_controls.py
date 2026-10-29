import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import Evaluator, controls, press, render
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Bound, Button, Free, Motif, Slider, local_names


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


DOT = "(motif 'dot' (params (r 1.0) (n 3)) (circle 'c' (r r)))"


class TestSlider:
    def test_targets_an_attribute(self):
        m = scene("(circle 'c') (slider 's' c.r (min 0) (max 5))")
        s = get(m, "s", Slider)
        assert (s.target, s.attr) == (m["c"], "r")
        assert (s.min, s.max, s.step) == (Free(0.0), Free(5.0), Free(None))
        assert s.label == Free("c.r")
        assert m.controls == [s]

    def test_label_and_step(self):
        s = get(scene("(circle 'c') (slider 's' c.r (step 0.5) (label 'size'))"), "s", Slider)
        assert (s.step, s.label) == (Free(0.5), Free("size"))

    def test_explicit_continuous(self):
        assert get(scene("(circle 'c') (slider 's' c.r (step 'none'))"), "s", Slider).step == Free(
            None
        )

    def test_targets_a_real(self):
        m = scene("(real 'k' 2) (slider 's' k (min 0) (max 10))")
        s = get(m, "s", Slider)
        assert (s.target, s.attr, s.kind) == (m["k"], "value", "real")

    def test_targets_a_motif_parameter_of_its_type(self):
        m = scene(f"{DOT} (dot 'd') (slider 's' d.n (min 1) (max 10))")
        s = get(m, "s", Slider)
        assert (s.target, s.attr, s.kind) == (m["d"], "n", "int")

    def test_written_parameter_is_not_folded(self):
        m = scene(f"{DOT} (dot 'd') (dot 'e') (slider 's' d.r)")
        d, e = get(m, "d", Motif), get(m, "e", Motif)
        assert isinstance(local_names(d)["c"].r, Bound)  # ty: ignore[unresolved-attribute]
        assert local_names(e)["c"].r == Free(1.0)  # ty: ignore[unresolved-attribute]

    def test_parameter_of_an_unreadable_target_is_reactive_everywhere(self):
        m = scene(f"{DOT} (dot 'd') (dot 'e') (slider 's' (ref 'e.r'))")
        for name in ("d", "e"):
            assert isinstance(local_names(get(m, name, Motif))["c"].r, Bound)  # ty: ignore[unresolved-attribute]

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(circle 'a') (circle 'c' (r a.r)) (slider 's' c.r)", "computed"),
            ("(circle 'c') (slider 's' c.nope)", "nope"),
            ("(circle 'c') (slider 's' 3)", None),
            ("(const 'g' 2) (slider 's' g)", None),
            ("(circle 'c') (slider 's' c.fill)", "number"),
            ("(slider 's' c.r) (circle 'c')", "'c'"),
            ("(scene _ (slider 's' c.r))", None),
            ("(circle 'c') (slider 's' c.r (min 'a'))", None),
            ("(circle 'c') (slider 's' c.r (step 'tiny'))", None),
            ("(circle 'c') (slider 's')", None),
            (
                "(motif 'm' (params (n 3)) (group 'g' (repeat i n (circle _))))"
                " (m 'd') (slider 's' d.n)",
                "compile time",
            ),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestButton:
    def test_writes_a_value(self):
        m = scene("(circle 'c') (button 'b' c.fill 'red')")
        b = get(m, "b", Button)
        assert b.state is not None
        assert [(obj, attr) for obj, attr, _ in b.state.moves] == [(m["c"], "fill")]
        assert b.label == Free("c.fill")

    def test_value_can_read_the_scene(self):
        b = get(scene("(circle 'c') (button 'b' c.r (* 2 c.r) (label 'grow'))"), "b", Button)
        assert b.state is not None and b.label == Free("grow")

    @pytest.mark.parametrize(
        "src", ["(circle 'c') (button 'b' c.r 'red')", "(circle 'c') (button 'b' c.fill)"]
    )
    def test_invalid(self, src):
        error(src)


class TestWriting:
    def test_dependents_follow(self):
        m = scene("(circle 'a' (r 1)) (circle 'b' (r (* 2 a.r)))")
        ev = Evaluator(m, random.Random(0))
        assert ev.value(m["b"], "r") == 2
        ev.write(m["a"], "r", 3.0)
        assert ev.value(m["b"], "r") == 6

    def test_motif_parameter(self):
        m = scene(f"{DOT} (dot 'd') (slider 's' d.r)")
        ev = Evaluator(m, random.Random(0))
        d = get(m, "d", Motif)
        ev.write(d, "r", 4.0)
        assert ev.value(local_names(d)["c"], "r") == 4


def figure(src):
    ((fig, ax),) = render(scene(src), random.Random(0))
    return fig, ax


def radius(ax):
    (circle,) = ax.patches
    box = circle.get_path().transformed(circle.get_transform() - ax.transData).get_extents()
    return box.width / 2


class TestMatplotlib:
    def test_slider_starts_at_the_target(self):
        fig, _ = figure("(circle 'c' (r 2)) (canvas 'cnv' c) (slider 's' c.r (min 0) (max 5))")
        assert controls(fig)["s"].val == 2

    def test_slider_redraws(self):
        fig, ax = figure("(circle 'c' (r 2)) (canvas 'cnv' c) (slider 's' c.r (min 0) (max 5))")
        controls(fig)["s"].set_val(3)
        assert radius(fig.axes[0]) == pytest.approx(3)

    def test_slider_on_an_int_writes_whole_numbers(self):
        src = "(motif 'm' (params (n 3)) (circle 'c' (r n))) (m 'd') (canvas 'cnv' d)"
        fig, _ = figure(f"{src} (slider 's' d.n (min 1) (max 9))")
        slider = controls(fig)["s"]
        assert slider.valstep == 1
        slider.set_val(4.6)
        assert radius(fig.axes[0]) == pytest.approx(5)

    def test_no_number_by_default(self):
        fig, _ = figure("(circle 'c') (canvas 'cnv' c) (slider 's' c.r)")
        assert not controls(fig)["s"].valtext.get_visible()

    def test_label(self):
        fig, _ = figure("(circle 'c') (canvas 'cnv' c) (slider 's' c.r (label 'size'))")
        assert controls(fig)["s"].label.get_text() == "size"

    def test_button_writes_on_press(self):
        src = "(circle 'c' (r 1)) (canvas 'cnv' c) (button 'b' c.r (* 2 c.r))"
        fig, _ = figure(src)
        press(fig, "b")
        press(fig, "b")
        assert radius(fig.axes[0]) == pytest.approx(4)

    def test_controls_without_a_canvas(self):
        figures = render(scene("(circle 'c') (slider 's' c.r)"), random.Random(0))
        assert len(figures) == 1
