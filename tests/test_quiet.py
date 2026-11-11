"""Quiet mode (mtp-16z): a view with an on-live starts quiet, and the reader makes it live. Its
on-live plays when it goes live, and its on-quiet when it goes back."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

SCENE = "(real k 0) (scene s (circle c))"
GO = "(animation (move k (to 1) (duration 1)))"
BACK = "(animation (move k (to 0) (duration 1)))"
FORMULA = r"(formula f tex'\term{t}{x}')"


def views(a="", b=""):
    """Two canvases, a and b, with what their bodies hold besides the scene."""
    return f"{SCENE} (canvas a s {a}) (canvas b s {b})"


def of(m, kind):
    return [o for o in m.objects if o.kind == kind]


class TestListeners:
    @pytest.mark.parametrize("kind", ["on-live", "on-quiet"])
    def test_inside_a_canvas_with_an_animation(self, kind):
        m = model(views(f"(on-live {GO}) ({kind} {BACK})"))
        o = of(m, kind)[0]
        assert o.data["view"] == m.id("a")
        assert m.objects[o.data["animation"]].kind == "animation"
        assert o.name is None and o.access == "page"

    def test_any_view(self):
        m = model(
            f"{views()} {FORMULA} (readout ro 'x' (on-live {GO})) (display d f (on-live {GO}))"
        )
        assert [o.data["view"] for o in of(m, "on-live")] == [m.id("ro"), m.id("d")]

    def test_no_animation(self):
        # Going live may change no value: it unfolds the view's controls.
        m = model(views("(on-live)"))
        assert of(m, "on-live")[0].data["animation"] is None

    def test_active_and_conditions(self):
        m = model(f"(bool on) {views(f'(on-live (active on) {GO} (<= k 5))')}")
        o = of(m, "on-live")[0]
        assert o.data["active"] is not None and len(o.data["conditions"]) == 1

    def test_two_views_each_their_own(self):
        m = model(views(f"(on-live {GO})", f"(on-live {BACK})"))
        assert [o.data["view"] for o in of(m, "on-live")] == [m.id("a"), m.id("b")]

    def test_on_quiet_before_its_on_live(self):
        m = model(views(f"(on-quiet {BACK}) (on-live {GO})"))
        assert of(m, "on-quiet")[0].data["view"] == m.id("a")


class TestErrors:
    @pytest.mark.parametrize("kind", ["on-live", "on-quiet"])
    def test_at_the_top_level(self, kind):
        error(
            f"{views()} ({kind} a {GO})",
            rf"{kind} is written inside the body of the view it acts in: \(canvas a …"
            rf" \({kind} …\)\)",
        )

    def test_on_quiet_needs_an_on_live(self):
        error(
            views(f"(on-quiet {BACK})", f"(on-live {GO})"),
            "a has no on-live, so it is never live: on-quiet needs one",
        )

    @pytest.mark.parametrize("kind", ["on-live", "on-quiet"])
    def test_takes_no_in(self, kind):
        error(
            views(f"(on-live) ({kind} (in b))"),
            r"a listener takes no \(in …\): it hears only in the view it is written in",
        )


class TestCompiled:
    def test_written(self):
        d = doc(f"{views(f'(on-live {GO}) (on-quiet {BACK})')} (button bt (in a) {GO})")
        assert errors(d) == []
        live = next(o for o in d["objects"] if o["kind"] == "on-live")
        quiet = next(o for o in d["objects"] if o["kind"] == "on-quiet")
        for o in (live, quiet):
            assert o["view"] == d["names"]["a"]
            assert d["objects"][o["animation"]]["kind"] == "animation"
            assert o["active"] is None and o["conditions"] == []

    def test_written_without_an_animation(self):
        d = doc(views("(on-live)"))
        assert errors(d) == []
        assert next(o for o in d["objects"] if o["kind"] == "on-live")["animation"] is None
