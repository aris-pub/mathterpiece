"""Controls, listeners and views, and who may read what (docs/reference.md "Components",
"Writes and conditions" and "Dragging"; docs/data-model.md "Two properties of every
expression"; docs/mtpc.md "Objects")."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.types import BOOL, ComponentT

K = "(real k 0 (>= 0) (<= 10))"
MOVE = "(animation (move k (to 5) (duration 1)))"
SLIDE = "(move k (from 0) (to 5))"


class TestControls:
    def test_a_slider(self):
        s = model(f"{K} (slider s {SLIDE} (step 5) (label 'size'))").get("s")
        assert (s.kind, s.type, s.access) == ("slider", ComponentT("slider"), "page")
        assert s.attrs["step"].value == 5 and s.attrs["label"].value == "size"
        assert s.attrs["position"].value == 0

    def test_a_slider_step_is_at_least_two(self):
        error(f"{K} (slider s {SLIDE} (step 1))", r"breaks \(>= 2\)")

    def test_play(self):
        p = model(f"{K} (play p {MOVE} (buttons true))").get("p")
        assert p.attrs["buttons"].value is True
        assert (p.attrs["playing"].value, p.attrs["step"].value) == (False, 0)

    def test_a_toggle_holding_its_own_value(self):
        t = model("(toggle t none (value true))").get("t")
        assert t.attrs["value"].value is True and t.data["target"] is None

    def test_a_toggle_with_a_target(self):
        m = model("(bool b true) (toggle t b)")
        t = m.get("t")
        assert t.data["target"] == (m.id("b"), None)
        assert t.attrs["value"].deps == {(m.id("b"), None)}

    def test_a_toggle_target_is_a_bool(self):
        error(f"{K} (toggle t k)", "a toggle's target is a bool")

    def test_a_toggle_on_a_groups_attribute(self):
        src = "(motif lamp (bool on false) (circle c)) (scene s (group g (lamp a) (lamp b)))"
        m = model(f"{src} (toggle t g.on)")
        assert m.get("t").attrs["value"].expr.op == "all"

    def test_a_toggle_is_read_through_its_value(self):
        m = model("(toggle show none) (bool on (= show.value true))")
        assert m.get("on").value.deps == {(m.id("show"), "value")}
        error("(toggle show none) (bool on show)", "write show.value")


class TestListeners:
    def test_dragging_a_position(self):
        m = model("(scene s (circle c)) (on-drag c c.pos)")
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert (d.name, d.data["shape"], d.data["target"]) == (None, m.id("c"), (m.id("c"), "pos"))

    def test_dragging_a_number_the_position_depends_on(self):
        m = model(f"{K} (scene s (circle c (x k))) (on-drag c k (<= k 8))")
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert d.data["conditions"][0]["op"] == "<="

    def test_a_target_the_position_does_not_depend_on(self):
        error(f"{K} (scene s (circle c)) (on-drag c k)", "position does not depend on")

    def test_when(self):
        m = model("(bool on true) (scene s (circle c)) (on-drag c c.x (when on))")
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert d.data["when"].deps == {(m.id("on"), None)}

    @pytest.mark.parametrize(
        "control",
        [
            f"(button b {MOVE} (when (> k 1)))",
            f"(slider b {SLIDE} (when (> k 1)))",
            f"(play b {MOVE} (when (> k 1)))",
            "(toggle b none (when (> k 1)))",
        ],
    )
    def test_a_control_is_active_while_its_when_holds(self, control):
        # data-model.md "Writers": a writer with (when bool) can be triggered only while it holds.
        m = model(f"{K} {control}")
        assert m.get("b").data["when"].deps == {(m.id("k"), None)}

    def test_a_control_without_when_is_always_active(self):
        assert model(f"{K} (button b {MOVE})").get("b").data["when"] is None

    def test_on_click(self):
        m = model(f"{K} (scene s (circle c)) (on-click c {MOVE})")
        (o,) = [o for o in m.objects if o.kind == "on-click"]
        assert m.objects[o.data["animation"]].kind == "animation"

    def test_a_listener_has_no_name(self):
        error("(scene s (circle c)) (on-click c c)", "expected an item")


class TestViews:
    def test_a_canvas(self):
        m = model("(bool on true) (scene s (circle c) (circle d)) (canvas v (x -3) c (when on d))")
        v = m.get("v")
        shows = v.data["shows"]
        assert shows[0] == m.id("c")
        assert shows[1][1] == [m.id("d")]
        assert v.attrs["x"].value == -3 and v.attrs["width"].value == 20

    def test_a_canvas_pans_and_zooms_unless_told_not_to(self):
        m = model("(scene s (circle c)) (canvas v s) (canvas w (pan false) (zoom false) s)")
        assert m.get("v").attrs["pan"].value is True and m.get("v").attrs["zoom"].value is True
        assert m.get("w").attrs["pan"].value is False and m.get("w").attrs["zoom"].value is False

    def test_a_canvas_keeps_the_order_its_items_are_written_in(self):
        m = model("(bool on true) (scene s (circle c) (circle d)) (canvas v (when on d) c)")
        shows = m.get("v").data["shows"]
        assert shows[0][1] == [m.id("d")] and shows[1] == m.id("c")

    def test_the_whole_scene(self):
        m = model("(scene s (circle c)) (canvas v s)")
        assert m.get("v").data["shows"] == [m.id("s")]

    def test_a_readout(self):
        m = model(f"{K} (readout r $'{{k:.2f}}')")
        assert m.get("r").attrs["value"].expr.op == "format"

    def test_a_readout_that_may_be_none(self):
        error("(real|none c) (readout r $'{c}')", "may be none")


class TestAccess:
    def test_reading_a_control_gives_page_access(self):
        m = model(f"{K} (slider s {SLIDE}) (real p s.position)")
        assert m.get("p").access == "page"
        assert m.get("k").access == "scene"

    def test_the_scene_never_reads_page_access(self):
        error(
            f"{K} (slider s {SLIDE}) (scene sc (circle c (r s.position)))", "the scene cannot read"
        )
        error(
            f"{K} (slider s {SLIDE}) (real p s.position) (scene sc (circle c (r p)))",
            "the scene cannot read",
        )

    def test_a_bool_reading_a_toggle(self):
        assert model("(toggle show none) (bool on show.value)").get("on").value.type == BOOL


class TestPositionalTargets:
    # reference.md "Components": on-drag's target and toggle's are positional; a toggle's may be
    # none, and then it holds its own bool.
    def test_on_drag_needs_its_target_after_the_shape(self):
        error("(scene s (circle c)) (on-drag c)", "on-drag is")
        error("(scene s (circle c)) (on-drag c (target c.pos))", "on-drag is")

    def test_a_toggle_names_its_target_or_none(self):
        error("(toggle t (label 'x'))", "a toggle is")
        assert model("(toggle t none)").get("t").data["target"] is None


class TestStartingWithoutTheReader:
    # mtp-9wm: (on-view view (animation …)) plays the first time the canvas comes into view, and
    # a play with (autoplay) starts when the page loads, or with (autoplay view-or-control) the
    # first time that comes into view.
    S = f"{K} (scene s (circle c)) (canvas v s)"

    def test_on_view(self):
        m = model(f"{self.S} (on-view v {MOVE})")
        (o,) = [o for o in m.objects if o.kind == "on-view"]
        assert o.data["view"] == m.id("v")
        assert m.objects[o.data["animation"]].kind == "animation"
        assert o.name is None and o.access == "page"

    def test_on_view_takes_a_canvas(self):
        error(f"{self.S} (on-view c {MOVE})", "expected the name of a canvas")
        error(f"{K} (on-view {MOVE})", "on-view takes the canvas it listens to")

    def test_autoplay_when_the_page_loads(self):
        m = model(f"{self.S} (play p (autoplay) {MOVE})")
        assert m.get("p").data["autoplay"] == "load"

    def test_autoplay_when_a_view_or_a_control_comes_into_view(self):
        m = model(
            f"{self.S} (button b {MOVE}) (play p (autoplay v) {MOVE}) (play q (autoplay b) {MOVE})"
        )
        assert m.get("p").data["autoplay"] == m.id("v")
        assert m.get("q").data["autoplay"] == m.id("b")

    def test_no_autoplay(self):
        assert model(f"{self.S} (play p {MOVE})").get("p").data["autoplay"] is None

    def test_autoplay_takes_a_view_or_a_control(self):
        error(f"{self.S} (play p (autoplay c) {MOVE})", "autoplay takes a view or a control")
        error(f"{self.S} (play p (autoplay v v) {MOVE})", "autoplay takes")

    def test_the_compiled_file(self):
        d = doc(
            f"{self.S} (on-view v {MOVE}) (play p (autoplay) {MOVE}) (play q (autoplay v) {MOVE})"
        )
        assert errors(d) == []
        names = d["names"]
        (o,) = [o for o in d["objects"] if o["kind"] == "on-view"]
        assert o["view"] == names["v"]
        assert d["objects"][names["p"]]["autoplay"] == "load"
        assert d["objects"][names["q"]]["autoplay"] == names["v"]


class TestReleaseListeners:
    # mtp-jpj: on-release runs when the pointer is released over the shape, as JS's pointerup;
    # on-dragend when a drag of the shape ends, as JS's dragend.
    S = f"{K} (scene s (circle c))"

    @pytest.mark.parametrize("kind", ["on-release", "on-dragend"])
    def test_a_listener_on_a_shape(self, kind):
        m = model(f"{self.S} ({kind} c {MOVE})")
        (o,) = [o for o in m.objects if o.kind == kind]
        assert o.data["shape"] == m.id("c")
        assert m.objects[o.data["animation"]].kind == "animation"
        assert o.name is None and "label" not in o.attrs

    @pytest.mark.parametrize("kind", ["on-release", "on-dragend"])
    def test_it_takes_a_shape(self, kind):
        error(f"{K} ({kind} {MOVE})", f"{kind} takes the shape it listens to")

    def test_the_compiled_file(self):
        d = doc(f"{self.S} (on-release c {MOVE}) (on-dragend c (when true) {MOVE})")
        assert errors(d) == []
        kinds = [o["kind"] for o in d["objects"]]
        assert "on-release" in kinds and "on-dragend" in kinds


class TestButtons:
    def test_a_button(self):
        m = model(f"{K} (button b (animation (move k (to 5) (duration 1))))")
        b = m.get("b")
        assert b.kind == "button"
        assert m.objects[b.data["animation"]].kind == "animation"
        assert b.attrs["label"].value == "b"
        assert b.access == "page"

    def test_a_named_animation(self):
        m = model(f"{K} (animation a (move k (to 5) (duration 1))) (button b (animation a))")
        assert m.get("b").data["animation"] == m.id("a")

    def test_conditions_clamp_what_is_written(self):
        m = model(
            f"{K} (real lim 3) (button b (animation (move k (to 5) (duration 1)))"
            " (<= k lim) (> 1 k))"
        )
        c = m.get("b").data["conditions"]
        assert [(x["target"], x["op"]) for x in c] == [
            ((m.id("k"), None), "<="),
            ((m.id("k"), None), "<"),
        ]
        assert (m.id("lim"), None) in c[0]["limit"].deps

    def test_a_condition_that_is_not_a_limit(self):
        src = f"{K} (real j) (button b (animation (move k (to 5) (duration 1)))"
        error(f"{src} (> j 1))", "compares an attribute this writer writes")
        error(f"{src} (> k (* 2 k)))", "compares an attribute this writer writes")


class TestListenersInAForeach:
    def test_a_foreach_gives_a_listener_for_each_shape(self):
        src = (
            "(real k 0)"
            "(scene s (foreach i 3 (circle (name $'c{i}'))))"
            "(foreach i 3 (on-click (name $'c{i}')"
            " (animation (move k (to i) (duration 0)))))"
        )
        m = model(src)
        clicks = [o for o in m.objects if o.kind == "on-click"]
        assert [o.data["shape"] for o in clicks] == [m.id(f"c{i}") for i in range(3)]


class TestCanvasToggles:
    # The author, 2026-11-04: a canvas toggles its when items, showing or hiding them, over
    # (toggle-duration t) with (toggle-ease e); it takes no move.
    S = "(scene s (circle c))"

    def test_a_duration_and_an_ease(self):
        m = model(f"{self.S} (canvas v (toggle-duration 0.4) (toggle-ease 'ease-in-out') c)")
        t = m.objects[m.get("v").data["transition"]]
        assert t.attrs["duration"].value == 0.4 and t.attrs["ease"].value == "ease-in-out"

    def test_a_duration_alone_toggles_linearly(self):
        m = model(f"{self.S} (canvas v (toggle-duration 1) c)")
        t = m.objects[m.get("v").data["transition"]]
        assert t.attrs["duration"].value == 1 and "ease" not in t.attrs

    def test_with_neither_it_toggles_at_once(self):
        assert model(f"{self.S} (canvas v c)").get("v").data["transition"] is None

    def test_an_ease_of_the_figures_own(self):
        model(
            f"(func soft ((real t 0 (>= 0) (<= 1))) (* t t)) {self.S}"
            " (canvas v (toggle-duration 1) (toggle-ease soft) c)"
        )

    def test_no_move(self):
        error(
            f"{self.S} (canvas v (move none (duration 1)) c)",
            r"a canvas toggles its items over \(toggle-duration t\)",
        )


def test_a_foreach_names_its_controls():
    # Found 2026-11-03 in examples/rows.mtp: (name $'b{v}') on a control in a top-level foreach
    # did not see v.
    m = model(
        "(real k 0) (foreach v [1 2] (button (name $'b{v}')"
        " (animation (move k (to v) (duration 0))) (label $'{v}')))"
    )
    assert m.get("b1").kind == "button" and m.get("b2").kind == "button"


def test_a_canvas_view_box_is_written_as_a_rect_is():
    # The author, 2026-11-04: (x …) (y …) (width …) (height …), with no view- prefix.
    m = model("(scene s) (canvas v (x -3) (y -2) (width 6) (height 4) s)")
    a = m.get("v").attrs
    assert [a[k].value for k in ("x", "y", "width", "height")] == [-3, -2, 6, 4]
    error("(scene s) (canvas v (view-x -3) s)", "a canvas takes no argument 'view-x'")


class TestEveryShownPartHasAName:
    # The author, 2026-11-04: a page places a view or a control by its name, so one with no name
    # could never be shown; it is a compile error.
    K = "(real k 0 (>= 0) (<= 1)) (scene s (circle c))"

    def test_controls_views_and_readouts(self):
        for src in (
            "(button_ (animation (move k (to 1) (duration 0))))",
            "(button none (animation (move k (to 1) (duration 0))))",
            "(slider_ (move k (from 0) (to 1)))",
            "(play_ (animation (move k (to 1) (duration 1))))",
            "(toggle_ none)",
            "(readout_ $'{k}')",
            "(canvas_ s)",
        ):
            error(f"{self.K} {src}", "is placed on the page by its name, so it needs one")

    def test_listeners_need_none(self):
        model(f"{self.K} (canvas v s) (on-click c (animation (move k (to 1) (duration 0))))")


class TestZoomBounds:
    # The author, 2026-11-04: the reader zooms between bounds, (zoom lo hi), from the view box (1)
    # up to hi times closer, and pans only inside the view box.
    S = "(scene s (circle c))"

    def test_a_range(self):
        a = model(f"{self.S} (canvas v (zoom 1 20) s)").get("v").attrs
        assert a["zoom"].value is True
        assert (a["zoom-min"].value, a["zoom-max"].value) == (1, 20)

    def test_the_default_range(self):
        a = model(f"{self.S} (canvas v s)").get("v").attrs
        assert (a["zoom-min"].value, a["zoom-max"].value) == (1, 10)

    def test_no_zoom(self):
        assert model(f"{self.S} (canvas v (zoom false) s)").get("v").attrs["zoom"].value is False

    def test_never_further_out_than_the_view_box(self):
        error(f"{self.S} (canvas v (zoom 0.5 4) s)", "never shows more than its view box")

    def test_the_bounds_in_order(self):
        error(f"{self.S} (canvas v (zoom 4 2) s)", "from a lower bound to a higher one")

    def test_known_when_compiling(self):
        error(f"(real k 4) {self.S} (canvas v (zoom 1 k) s)", "known when compiling")
