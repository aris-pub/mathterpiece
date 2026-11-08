"""Listeners and controls name the views they belong to with (in view…) (mtp-2juu.1): a listener
hears the pointer only in those views, every view showing its shape without one; a control belongs
to those views, to none without one, which quiet mode (mtp-16z) reads."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

SCENE = "(real k 0) (scene s (circle c) (rect r)) (canvas a s) (canvas b s)"
GO = "(animation (move k (to 1) (duration 1)))"
FORMULA = r"(formula f tex'\term{t}{x} + \term{all}{\term{top}{a}}') (display d f)"


def one(m, kind):
    (o,) = [o for o in m.objects if o.kind == kind]
    return o


LISTENERS = [
    ("on-drag", "(on-drag c c.pos (in a))"),
    ("on-click", f"(on-click c (in a) {GO})"),
    ("on-release", f"(on-release c (in a) {GO})"),
    ("on-dragstart", f"(on-dragstart c (in a) {GO})"),
    ("on-dragend", f"(on-dragend c (in a) {GO})"),
    ("on-enter", f"(on-enter c (in a) {GO})"),
    ("on-leave", f"(on-leave c (in a) {GO})"),
    ("on-pointermove", "(point p) (on-pointermove c p (in a))"),
]


class TestListeners:
    @pytest.mark.parametrize("kind,src", LISTENERS)
    def test_each_listener_on_a_shape_takes_its_views(self, kind, src):
        m = model(f"{SCENE} {src}")
        assert one(m, kind).data["in"] == [m.id("a")]

    def test_more_than_one_view(self):
        m = model(f"{SCENE} (on-click c (in a b))")
        assert one(m, "on-click").data["in"] == [m.id("a"), m.id("b")]

    def test_without_it_every_view(self):
        assert one(model(f"{SCENE} (on-click c)"), "on-click").data["in"] is None

    def test_it_comes_with_the_other_options_and_conditions(self):
        m = model(f"{SCENE} (on-drag c c.pos (active true) (in b) (<= c.x 5))")
        d = one(m, "on-drag")
        assert d.data["in"] == [m.id("b")] and len(d.data["conditions"]) == 1

    def test_a_term_in_its_display(self):
        m = model(f"{FORMULA} (on-click f.t (in d))")
        assert one(m, "on-click").data["in"] == [m.id("d")]

    def test_a_nested_term_in_its_display(self):
        m = model(f"{FORMULA} (on-enter f.top (in d))")
        assert one(m, "on-enter").data["in"] == [m.id("d")]

    @pytest.mark.parametrize("kind,src", LISTENERS)
    def test_it_is_written(self, kind, src):
        d = doc(f"{SCENE} {src}")
        o = next(o for o in d["objects"] if o["kind"] == kind)
        assert o["in"] == [d["names"]["a"]]
        assert errors(d) == []

    def test_without_it_nothing_is_written(self):
        d = doc(f"{SCENE} (on-click c)")
        assert "in" not in next(o for o in d["objects"] if o["kind"] == "on-click")


CONTROLS = [
    ("slider", "(slider sl (move k (from 0) (to 1)) (in a))"),
    ("button", f"(button bt (in a) {GO})"),
    ("play", f"(play pl (in a) {GO})"),
    ("toggle", "(toggle tg none (in a))"),
]


class TestControls:
    @pytest.mark.parametrize("kind,src", CONTROLS)
    def test_each_control_takes_its_views(self, kind, src):
        m = model(f"{SCENE} {src}")
        assert one(m, kind).data["in"] == [m.id("a")]

    def test_any_view(self):
        m = model(f"{SCENE} {FORMULA} (readout ro 'x') (button bt (in a ro d))")
        assert one(m, "button").data["in"] == [m.id("a"), m.id("ro"), m.id("d")]

    def test_without_it_no_view(self):
        assert one(model(f"{SCENE} (button bt)"), "button").data["in"] is None

    @pytest.mark.parametrize("kind,src", CONTROLS)
    def test_it_is_written(self, kind, src):
        d = doc(f"{SCENE} {src}")
        o = next(o for o in d["objects"] if o["kind"] == kind)
        assert o["in"] == [d["names"]["a"]]
        assert errors(d) == []


class TestErrors:
    def test_not_a_view(self):
        error(f"{SCENE} (button bt) (on-click c (in bt))", "bt is a button, not a view")

    def test_a_variable_is_not_a_view(self):
        error(f"{SCENE} (on-click c (in k))", "k is a variable, not a view")

    def test_an_unknown_name(self):
        error(f"{SCENE} (on-click c (in nowhere))", "unknown view 'nowhere'")

    def test_a_view_declared_later(self):
        error(
            f"(scene s (circle c)) (on-click c (in a) {GO}) (canvas a s)",
            "unknown view 'a': a listener or control names views declared before it",
        )

    def test_not_a_name(self):
        error(f"{SCENE} (on-click c (in 1))", r"\(in …\) names views, such as \(in a b\)")

    def test_at_least_one(self):
        error(f"{SCENE} (on-click c (in))", r"\(in …\) names at least one view")

    def test_twice_in_one(self):
        error(f"{SCENE} (on-click c (in a a))", "a is named twice")

    def test_given_twice(self):
        error(f"{SCENE} (on-click c (in a) (in b))", "'in' is given twice")

    def test_a_canvas_that_never_shows_the_shape(self):
        error(
            f"(scene s (circle c) (group g (rect r))) (canvas a g) (on-click c (in a) {GO})",
            "the canvas a never shows c",
        )

    def test_a_canvas_showing_a_container_of_it(self):
        m = model(
            f"(real k 0) (scene s (group g (circle c))) (canvas a g) (on-click c (in a) {GO})"
        )
        assert one(m, "on-click").data["in"] == [m.id("a")]

    def test_a_canvas_showing_it_by_an_expression_may(self):
        m = model(
            "(real k 0) (bool on) (scene s (circle c) (rect r)) (canvas a r (when on c))"
            f" (on-click c (in a) {GO})"
        )
        assert one(m, "on-click").data["in"] == [m.id("a")]

    def test_a_readout_shows_no_shape(self):
        error(
            f"{SCENE} (readout ro 'x') (on-click c (in ro))",
            "a readout shows no shapes, so c is never in ro",
        )

    def test_a_display_shows_no_shape(self):
        error(
            f"{SCENE} {FORMULA} (on-click c (in d))",
            "a display shows no shapes, so c is never in d",
        )

    def test_a_canvas_shows_no_term(self):
        error(
            f"{SCENE} {FORMULA} (on-click f.t (in a))",
            "a canvas shows no terms, so f.t is never in a",
        )

    def test_a_display_of_another_formula(self):
        error(
            rf"{FORMULA} (formula g tex'\term{{u}}{{y}}') (display e g) (on-click f.t (in e))",
            "the display e shows g, not f, so f.t is never in it",
        )

    def test_on_view_names_its_canvas(self):
        error(
            f"{SCENE} (on-view a (in b))", r"on-view listens to its canvas, so it takes no \(in …\)"
        )

    def test_on_pointermove_on_a_canvas(self):
        error(
            f"{SCENE} (point p) (on-pointermove a p (in b))",
            r"this on-pointermove listens to its canvas, so it takes no \(in …\)",
        )

    @pytest.mark.parametrize(
        "view", ["(canvas v (in a) s)", "(readout v 'x' (in a))", "(display v f (in a))"]
    )
    def test_a_view_takes_none(self, view):
        error(f"{SCENE} {FORMULA} {view}", r"a view takes no \(in …\)")
