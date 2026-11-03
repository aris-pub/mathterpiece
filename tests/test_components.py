"""Controls, listeners and views, and who may read what (docs/reference.md "Components",
"Writes and conditions" and "Dragging"; docs/data-model.md "Two properties of every
expression"; docs/mtpc.md "Objects")."""

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import BOOL, ComponentT

K = "(real k 0 (>= 0) (<= 10))"
MOVE = "(animation (move k (to 5) (duration 1)))"
SLIDE = "(move k (from 0) (to 5))"


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


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
        m = model(
            "(bool on true) (scene s (circle c) (circle d)) (canvas v (view-x -3) c (when on d))"
        )
        v = m.get("v")
        shows = v.data["shows"]
        assert shows[0] == m.id("c")
        assert shows[1][1] == [m.id("d")]
        assert v.attrs["view-x"].value == -3 and v.attrs["view-width"].value == 20

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


class TestUnnamedControls:
    # A control with no name still takes a label; its label is then empty unless it gives one.
    def test_a_control_with_no_name_takes_a_label(self):
        m = model(f"{K} (button none {MOVE} (label 'go'))")
        (b,) = [o for o in m.objects if o.kind == "button"]
        assert b.attrs["label"].value == "go"

    def test_its_label_is_empty_otherwise(self):
        m = model(f"{K} (button_ {MOVE})")
        (b,) = [o for o in m.objects if o.kind == "button"]
        assert b.attrs["label"].value == ""


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
        import json

        from mtpc_check import errors

        from mathterpiece.mtpc import write

        m = model(
            f"{self.S} (on-view v {MOVE}) (play p (autoplay) {MOVE}) (play q (autoplay v) {MOVE})"
        )
        d = json.loads(write(m))
        assert errors(d) == []
        (o,) = [o for o in d["objects"] if o["kind"] == "on-view"]
        assert o["view"] == m.id("v")
        assert d["objects"][m.id("p")]["autoplay"] == "load"
        assert d["objects"][m.id("q")]["autoplay"] == m.id("v")
