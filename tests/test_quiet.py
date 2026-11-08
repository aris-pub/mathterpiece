"""Quiet mode (mtp-16z): a view with an on-live starts quiet, and the reader makes it live. Its
on-live plays when it goes live, and its on-quiet when it goes back."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

SCENE = "(real k 0) (scene s (circle c)) (canvas a s) (canvas b s)"
GO = "(animation (move k (to 1) (duration 1)))"
BACK = "(animation (move k (to 0) (duration 1)))"
FORMULA = r"(formula f tex'\term{t}{x}') (display d f)"


def of(m, kind):
    return [o for o in m.objects if o.kind == kind]


class TestListeners:
    @pytest.mark.parametrize("kind", ["on-live", "on-quiet"])
    def test_names_a_canvas_and_an_animation(self, kind):
        m = model(f"{SCENE} (on-live a {GO}) ({kind} a {BACK})")
        o = of(m, kind)[0]
        assert o.data["view"] == m.id("a")
        assert m.objects[o.data["animation"]].kind == "animation"
        assert o.name is None and o.access == "page"

    def test_any_view(self):
        m = model(f"{SCENE} {FORMULA} (readout ro 'x') (on-live ro {GO}) (on-live d {GO})")
        assert [o.data["view"] for o in of(m, "on-live")] == [m.id("ro"), m.id("d")]

    def test_no_animation(self):
        # Going live may change no value: it unfolds the view's controls.
        m = model(f"{SCENE} (on-live a)")
        assert of(m, "on-live")[0].data["animation"] is None

    def test_active_and_conditions(self):
        m = model(f"{SCENE} (bool on) (on-live a (active on) {GO} (<= k 5))")
        o = of(m, "on-live")[0]
        assert o.data["active"] is not None and len(o.data["conditions"]) == 1

    def test_two_views_each_their_own(self):
        m = model(f"{SCENE} (on-live a {GO}) (on-live b {BACK})")
        assert [o.data["view"] for o in of(m, "on-live")] == [m.id("a"), m.id("b")]

    def test_on_quiet_before_its_on_live(self):
        m = model(f"{SCENE} (on-quiet a {BACK}) (on-live a {GO})")
        assert of(m, "on-quiet")[0].data["view"] == m.id("a")


class TestErrors:
    @pytest.mark.parametrize("kind", ["on-live", "on-quiet"])
    def test_takes_a_view(self, kind):
        error(f"{SCENE} (button bt) ({kind} bt {GO})", "expected the name of a view")
        error(f"{SCENE} ({kind} c {GO})", "expected the name of a view")
        error(f"{SCENE} ({kind} {GO})", f"{kind} takes the view it listens to")

    def test_on_quiet_needs_an_on_live(self):
        error(
            f"{SCENE} (on-live b {GO}) (on-quiet a {BACK})",
            "a has no on-live, so it is never live: on-quiet needs one",
        )

    @pytest.mark.parametrize("kind", ["on-live", "on-quiet"])
    def test_names_its_view_so_takes_no_in(self, kind):
        error(
            f"{SCENE} (on-live a) ({kind} a (in b))",
            rf"{kind} listens to its view, so it takes no \(in …\)",
        )


class TestCompiled:
    def test_written(self):
        d = doc(f"{SCENE} (on-live a {GO}) (on-quiet a {BACK}) (button bt (in a) {GO})")
        assert errors(d) == []
        live = next(o for o in d["objects"] if o["kind"] == "on-live")
        quiet = next(o for o in d["objects"] if o["kind"] == "on-quiet")
        for o in (live, quiet):
            assert o["view"] == d["names"]["a"]
            assert d["objects"][o["animation"]]["kind"] == "animation"
            assert o["active"] is None and o["conditions"] == []

    def test_written_without_an_animation(self):
        d = doc(f"{SCENE} (on-live a)")
        assert errors(d) == []
        assert next(o for o in d["objects"] if o["kind"] == "on-live")["animation"] is None
