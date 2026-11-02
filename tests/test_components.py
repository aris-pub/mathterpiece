"""Controls, listeners and views, and who may read what (docs/reference.md "Components",
"Writes and conditions" and "Dragging"; docs/data-model.md "Two properties of every
expression"; docs/mtpc.md "Objects")."""

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import BOOL, ComponentT

K = "(real k 0 (>= 0) (<= 10))"
MOVE = "(animation (k (transition (to 5) (duration 1))))"


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


class TestControls:
    def test_a_slider(self):
        s = model(f"{K} (slider s {MOVE} (step 5) (label 'size'))").get("s")
        assert (s.kind, s.type, s.access) == ("slider", ComponentT("slider"), "page")
        assert s.attrs["step"].value == 5 and s.attrs["label"].value == "size"
        assert s.attrs["position"].value == 0

    def test_a_slider_step_is_at_least_two(self):
        error(f"{K} (slider s {MOVE} (step 1))", r"breaks \(>= 2\)")

    def test_play(self):
        p = model(f"{K} (play p {MOVE} (buttons true))").get("p")
        assert p.attrs["buttons"].value is True
        assert (p.attrs["playing"].value, p.attrs["step"].value) == (False, 0)

    def test_a_toggle_holding_its_own_value(self):
        t = model("(toggle t (value true))").get("t")
        assert t.attrs["value"].value is True and t.data["target"] is None

    def test_a_toggle_with_a_target(self):
        m = model("(bool b true) (toggle t (target b))")
        t = m.get("t")
        assert t.data["target"] == (m.id("b"), None)
        assert t.attrs["value"].deps == {(m.id("b"), None)}

    def test_a_toggle_target_is_a_bool(self):
        error(f"{K} (toggle t (target k))", "a toggle's target is a bool")

    def test_a_toggle_on_a_groups_attribute(self):
        src = "(motif lamp (bool on false) (circle c)) (scene s (group g (lamp a) (lamp b)))"
        m = model(f"{src} (toggle t (target g.on))")
        assert m.get("t").attrs["value"].expr.op == "all"

    def test_a_toggle_reads_as_its_value(self):
        m = model("(toggle show) (bool on (= show true))")
        assert m.get("on").value.deps == {(m.id("show"), "value")}


class TestListeners:
    def test_dragging_a_position(self):
        m = model("(scene s (circle c)) (on-drag c (target c.pos))")
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert (d.name, d.data["shape"], d.data["target"]) == (None, m.id("c"), (m.id("c"), "pos"))

    def test_dragging_a_number_the_position_depends_on(self):
        m = model(f"{K} (scene s (circle c (x k))) (on-drag c (target k) (<= k 8))")
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert d.data["conditions"][0]["op"] == "<="

    def test_a_target_the_position_does_not_depend_on(self):
        error(f"{K} (scene s (circle c)) (on-drag c (target k))", "position does not depend on")

    def test_when(self):
        m = model("(bool on true) (scene s (circle c)) (on-drag c (target c.x) (when on))")
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert d.data["when"].deps == {(m.id("on"), None)}

    def test_on_click(self):
        m = model(f"{K} (scene s (circle c)) (on-click c {MOVE})")
        (o,) = [o for o in m.objects if o.kind == "on-click"]
        assert m.objects[o.data["animation"]].kind == "animation"

    def test_a_listener_has_no_name(self):
        error("(scene s (circle c)) (on-click c c)", "expected an item")


class TestViews:
    def test_a_canvas(self):
        m = model(
            "(bool on true) (scene s (circle c) (circle d)) (canvas v c (when on d) (view-x -3))"
        )
        v = m.get("v")
        assert v.data["members"] == [m.id("c")]
        assert v.data["when"][0][1] == [m.id("d")]
        assert v.attrs["view-x"].value == -3 and v.attrs["view-width"].value == 20

    def test_the_whole_scene(self):
        m = model("(scene s (circle c)) (canvas v s)")
        assert m.get("v").data["members"] == [m.id("s")]

    def test_a_readout(self):
        m = model(f"{K} (readout r $'{{k:.2f}}')")
        assert m.get("r").attrs["value"].expr.op == "format"

    def test_a_readout_that_may_be_none(self):
        error("(real|none c) (readout r $'{c}')", "may be none")


class TestAccess:
    def test_reading_a_control_gives_page_access(self):
        m = model(f"{K} (slider s {MOVE}) (real p s.position)")
        assert m.get("p").access == "page"
        assert m.get("k").access == "scene"

    def test_the_scene_never_reads_page_access(self):
        error(
            f"{K} (slider s {MOVE}) (scene sc (circle c (r s.position)))", "the scene cannot read"
        )
        error(
            f"{K} (slider s {MOVE}) (real p s.position) (scene sc (circle c (r p)))",
            "the scene cannot read",
        )

    def test_a_bool_reading_a_toggle(self):
        assert model("(toggle show) (bool on show)").get("on").value.type == BOOL
