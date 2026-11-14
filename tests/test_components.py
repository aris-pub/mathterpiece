"""Controls, listeners and views, and who may read what (docs/reference.md "Components",
"Writes and conditions" and "Dragging"; docs/data-model.md "Two properties of every
expression"; docs/mtpc.md "Objects")."""

import pytest
from helpers import doc, error, model, typ, value
from mtpc_check import errors

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import BOOL, ComponentT, Maybe

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

    def test_a_play_rests_between_its_steps(self):
        # mtp-wfrs: (rest t) pauses t seconds between each pair of steps.
        p = model(f"{K} (play p {MOVE} (rest 1.2))").get("p")
        assert p.data["rest"] == 1.2
        d = doc(f"{K} (play p {MOVE} (rest 1.2)) (play q {MOVE})")
        p, q = [o for o in d["objects"] if o["kind"] == "play"]
        assert p["rest"] == 1.2 and "rest" not in q
        assert errors(d) == []

    def test_a_rest_is_seconds_known_when_compiling(self):
        error(f"{K} (play p {MOVE} (rest -1))", "cannot be negative")
        error(f"{K} (play p {MOVE} (rest k))", "known when compiling")
        error(f"{K} (button b {MOVE} (rest 1))", "only a play takes")

    # A stepper: a play the reader moves through one step at a time, with no clock (the author,
    # 2026-11-10).
    def test_a_stepper(self):
        m = model(f"{K} (bool on true) (stepper s {MOVE} (label 'hints') (active on))")
        s = m.get("s")
        assert (s.kind, s.type, s.access) == ("stepper", ComponentT("stepper"), "page")
        assert s.data["animation"] is not None
        assert s.attrs["label"].value == "hints"
        assert s.data["active"].deps == {(m.id("on"), None)}
        assert (s.attrs["playing"].value, s.attrs["step"].value) == (False, 0)

    def test_a_stepper_is_read_through_its_step(self):
        m = model(f"{K} (stepper s {MOVE}) (bool past (> s.step 0))")
        assert m.get("past").value.deps == {(m.id("s"), "step")}

    def test_a_stepper_needs_an_animation(self):
        error("(stepper s (label 'hints'))", r"a stepper needs an \(animation …\)")

    def test_a_stepper_has_one_stop_per_step(self):
        error(f"{K} (stepper s {MOVE} (buttons true))", r"a stepper takes no \(buttons …\)")
        error(f"{K} (stepper s {MOVE} (rest 1))", "only a play takes")

    def test_the_compiled_stepper(self):
        d = doc(f"{K} (stepper s {MOVE} (label 'hints'))")
        (s,) = [o for o in d["objects"] if o["kind"] == "stepper"]
        assert d["objects"][s["animation"]]["kind"] == "animation"
        assert s["attrs"]["label"] == {"type": "string", "free": "hints"}
        assert s["active"] is None and s["conditions"] == []
        assert "autoplay" not in s and "rest" not in s
        assert errors(d) == []

    # The author, 2026-11-11 (mtp-0lzp): a toggle always writes a bool variable or attribute, so
    # it takes no none and no (value …).
    def test_a_toggle_takes_no_none(self):
        error("(toggle t none)", r"declare one, \(bool t-on false\), and target it")

    def test_a_toggle_takes_no_value(self):
        error("(bool b) (toggle t b (value true))", r"a toggle takes no \(value …\)")

    def test_a_toggle_with_a_target(self):
        m = model("(bool b true) (toggle t b)")
        t = m.get("t")
        assert t.data["target"] == (m.id("b"), None)
        assert t.attrs["value"].deps == {(m.id("b"), None)}

    # (animation …): what a flip of the toggle plays, after it writes its bool, such as zooming a
    # canvas to what the toggle shows (the author, 2026-11-09).
    def test_a_toggle_plays_an_animation(self):
        m = model(f"{K} (bool b) (toggle t b (animation (move k (to (if b 5 0)) (duration 1))))")
        t = m.get("t")
        assert t.data["animation"] is not None

    def test_a_toggle_without_an_animation_has_none(self):
        assert model("(bool b) (toggle t b)").get("t").data["animation"] is None

    def test_a_toggle_target_is_a_bool(self):
        error(f"{K} (toggle t k)", "a toggle's target is a bool")

    def test_a_toggle_on_a_groups_attribute(self):
        src = "(motif lamp (bool on false) (circle c)) (scene s (group g (lamp a) (lamp b)))"
        m = model(f"{src} (toggle t g.on)")
        assert m.get("t").attrs["value"].expr.op == "all"

    def test_a_toggle_is_read_through_its_value(self):
        m = model("(bool shown) (toggle show shown) (bool on (= show.value true))")
        assert m.get("on").value.deps == {(m.id("show"), "value")}
        error("(bool shown) (toggle show shown) (bool on show)", "write show.value")


class TestListeners:
    def test_dragging_a_position(self):
        m = model("(scene s (circle c)) (canvas v s (on-drag c c.pos))")
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert (d.name, d.data["shape"], d.data["target"]) == (None, m.id("c"), (m.id("c"), "pos"))

    def test_dragging_a_number_by_a_move(self):
        m = model(
            f"{K} (scene s (circle c (x k)))"
            " (canvas v s (on-drag c (move k (to pointer.x)) (<= k 8)))"
        )
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert d.data["conditions"][0]["op"] == "<="

    def test_a_target_that_is_not_the_position_needs_a_move(self):
        error(f"{K} (scene s (circle c)) (canvas v s (on-drag c k))", "is not the shape's position")

    def test_when(self):
        m = model("(bool on true) (scene s (circle c)) (canvas v s (on-drag c c.x (active on)))")
        (d,) = [o for o in m.objects if o.kind == "on-drag"]
        assert d.data["active"].deps == {(m.id("on"), None)}

    @pytest.mark.parametrize(
        "control",
        [
            f"(button b {MOVE} (active (> k 1)))",
            f"(slider b {SLIDE} (active (> k 1)))",
            f"(play b {MOVE} (active (> k 1)))",
            "(bool on) (toggle b on (active (> k 1)))",
        ],
    )
    def test_a_control_is_active_while_its_active_holds(self, control):
        # data-model.md "Writers": a writer with (active bool) can be triggered only while it holds
        # (the author, 2026-11-04: active, not when).
        m = model(f"{K} {control}")
        assert m.get("b").data["active"].deps == {(m.id("k"), None)}

    def test_a_control_without_active_is_always_active(self):
        assert model(f"{K} (button b {MOVE})").get("b").data["active"] is None

    def test_on_click(self):
        m = model(f"{K} (scene s (circle c)) (canvas v s (on-click c {MOVE}))")
        (o,) = [o for o in m.objects if o.kind == "on-click"]
        assert m.objects[o.data["animation"]].kind == "animation"

    def test_a_listener_has_no_name(self):
        error("(scene s (circle c)) (canvas v s (on-click c c))", "expected an item")


class TestViews:
    def test_a_canvas(self):
        m = model("(bool on true) (scene s (circle c) (circle d)) (canvas v (x -3) c (when on d))")
        v = m.get("v")
        shows = v.data["shows"]
        assert shows[0] == m.id("c")
        assert shows[1].bound and (m.id("on"), None) in shows[1].expr.deps
        assert v.attrs["x"].value == -3 and v.attrs["width"].value == 20

    def test_a_canvas_pans_and_zooms_unless_told_not_to(self):
        m = model("(scene s (circle c)) (canvas v s) (canvas w (pan false) (zoom false) s)")
        assert m.get("v").attrs["pan"].value is True and m.get("v").attrs["zoom"].value is True
        assert m.get("w").attrs["pan"].value is False and m.get("w").attrs["zoom"].value is False

    def test_a_canvas_keeps_the_order_its_items_are_written_in(self):
        m = model("(bool on true) (scene s (circle c) (circle d)) (canvas v (when on d) c)")
        shows = m.get("v").data["shows"]
        assert shows[0].bound and shows[1] == m.id("c")

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
        assert (
            model("(bool shown) (toggle show shown) (bool on show.value)").get("on").value.type
            == BOOL
        )


class TestPositionalTargets:
    # reference.md "Components": on-drag's target and toggle's are positional.
    def test_on_drag_needs_its_target_after_the_shape(self):
        error("(scene s (circle c)) (canvas v s (on-drag c))", "on-drag is")
        error("(scene s (circle c)) (canvas v s (on-drag c (target c.pos)))", "on-drag is")

    def test_a_toggle_names_its_target(self):
        error("(toggle t (label 'x'))", "a toggle is")


class TestStartingWithoutTheReader:
    # mtp-9wm: (on-view (animation …)) in a canvas plays the first time it comes into view.
    S = f"{K} (scene s (circle c)) (canvas v s)"

    def test_on_view(self):
        m = model(f"{K} (scene s (circle c)) (canvas v s (on-view {MOVE}))")
        (o,) = [o for o in m.objects if o.kind == "on-view"]
        assert o.data["view"] == m.id("v")
        assert m.objects[o.data["animation"]].kind == "animation"
        assert o.name is None and o.access == "page"

    def test_on_view_is_inside_a_canvas(self):
        error(f"{self.S} (on-view v {MOVE})", "on-view is written inside the body of the view")
        error(f"{K} (readout r 'x' (on-view {MOVE}))", "so it is written inside a canvas")

    def test_the_compiled_file(self):
        d = doc(f"{K} (scene s (circle c)) (canvas v s (on-view {MOVE}))")
        assert errors(d) == []
        (o,) = [o for o in d["objects"] if o["kind"] == "on-view"]
        assert o["view"] == d["names"]["v"]


class TestReleaseListeners:
    # mtp-jpj: on-release runs when the pointer is released over the shape, as JS's pointerup;
    # on-dragend when a drag of the shape ends, as JS's dragend; on-dragstart (mtp-5opl) when
    # one starts, as JS's dragstart.
    S = f"{K} (scene s (circle c))"

    @pytest.mark.parametrize("kind", ["on-release", "on-dragstart", "on-dragend"])
    def test_a_listener_on_a_shape(self, kind):
        m = model(f"{self.S} (canvas v s ({kind} c {MOVE}))")
        (o,) = [o for o in m.objects if o.kind == kind]
        assert o.data["shape"] == m.id("c")
        assert m.objects[o.data["animation"]].kind == "animation"
        assert o.name is None and "label" not in o.attrs

    @pytest.mark.parametrize("kind", ["on-release", "on-dragstart", "on-dragend"])
    def test_it_takes_a_shape(self, kind):
        error(
            f"{K} (scene s) (canvas v s ({kind} {MOVE}))", f"{kind} takes the shape it listens to"
        )

    def test_the_compiled_file(self):
        d = doc(
            f"{self.S} (canvas v s (on-release c {MOVE}) (on-dragend c (active true) {MOVE})"
            f" (on-dragstart c (active true) (stop-propagation true) {MOVE}))"
        )
        assert errors(d) == []
        kinds = [o["kind"] for o in d["objects"]]
        assert {"on-release", "on-dragstart", "on-dragend"} <= set(kinds)
        (o,) = [o for o in d["objects"] if o["kind"] == "on-dragstart"]
        assert o["shape"] == d["names"]["c"]
        assert d["objects"][o["animation"]]["kind"] == "animation"


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

    # (selected bool): a button that also says which state is the current one shows it, as
    # the K3 to K6 buttons that choose the clique forbidden (the author, 2026-11-08).
    def test_selected_follows_what_it_reads(self):
        m = model(f"{K} (button b (animation (move k (to 5) (duration 1))) (selected (= k 5)))")
        selected = m.get("b").attrs["selected"]
        assert selected.bound and (m.id("k"), None) in selected.deps

    def test_a_button_without_selected_has_none(self):
        m = model(f"{K} (button b (animation (move k (to 5) (duration 1))))")
        assert "selected" not in m.get("b").attrs

    def test_selected_is_a_bool(self):
        error(
            f"{K} (button b (animation (move k (to 5) (duration 1))) (selected k))", "expected bool"
        )

    def test_only_a_button_takes_selected(self):
        error(
            f"{K} (slider s (move k (from 0) (to 5)) (selected true))",
            r"only a button takes \(selected …\), not a slider",
        )


class TestItemsAWriterDoesNotTake:
    """An item that is neither an argument of the writer nor a condition is reported as an
    argument that the writer does not take, at that item (mtp-843h). Before, it was read as a
    condition, and the error was about conditions."""

    HEAD = f"{K} (bool on false) (color teal '#2a9d8f') (scene s (circle c))\n"

    def where(self, src: str, message: str) -> str:
        with pytest.raises(CompileError) as exc:
            compile_source(self.HEAD + src)
        assert exc.value.msg == message
        return f"{exc.value.pos.line}:{exc.value.pos.col}"

    @pytest.mark.parametrize(
        "src, message",
        [
            ("(toggle t on (label 'a circle') (color teal))", "a toggle takes no (color …)"),
            ("(toggle t on (color teal) (label 'a circle'))", "a toggle takes no (color …)"),
            (f"(button t {MOVE} (color teal))", "a button takes no (color …)"),
            (f"(button t (color teal) {MOVE})", "a button takes no (color …)"),
            (f"(slider t {SLIDE} (color teal))", "a slider takes no (color …)"),
            (f"(play t {MOVE} (color teal))", "a play takes no (color …)"),
            (f"(stepper t {MOVE} (color teal))", "a stepper takes no (color …)"),
            (f"(canvas t s (on-click c {MOVE} (color teal)))", "on-click takes no (color …)"),
            (f"(button t {MOVE} (> k 1) (color teal))", "a button takes no (color …)"),
            # An argument of another control.
            (f"(button t {MOVE} (step 2))", "a button takes no (step …)"),
        ],
    )
    def test_the_error_is_at_the_item(self, src, message):
        col = src.index("(color") if "(color" in src else src.index("(step")
        assert self.where(src, message) == f"2:{col + 1}"

    def test_a_word_that_names_nothing_may_be_a_misspelled_choreo(self):
        message = "a button takes no (fade …), and 'fade' is not a choreo"
        src = f"(button t {MOVE} (fade c))"
        assert self.where(src, message) == f"2:{src.index('(fade') + 1}"

    def test_a_condition_that_is_not_a_limit_still_says_so(self):
        with pytest.raises(CompileError, match="compares an attribute this writer writes"):
            compile_source(f"{self.HEAD}(real j) (button t {MOVE} (and (> j 1) (< j 2)))")


class TestListenersInAForeach:
    def test_a_foreach_gives_a_listener_for_each_shape(self):
        src = (
            "(real k 0)"
            "(scene s (foreach i 3 (circle (name $'c{i}'))))"
            "(canvas v s (foreach i 3 (on-click (name $'c{i}')"
            " (animation (move k (to i) (duration 0))))))"
        )
        m = model(src)
        clicks = [o for o in m.objects if o.kind == "on-click"]
        assert [o.data["shape"] for o in clicks] == [m.id(f"c{i}") for i in range(3)]


class TestCanvasToggles:
    # The author, 2026-11-04: a canvas toggles its when items, showing or hiding them, over
    # (toggle-duration t) with (toggle-ease e); it takes no move.
    S = "(scene s (circle c))"

    def test_a_duration_and_an_ease(self):
        src = "(func cube ((real t (>= 0) (<= 1))) (* t t t))"
        m = model(f"{src} {self.S} (canvas v (toggle-duration 0.4) (toggle-ease cube) c)")
        t = m.objects[m.get("v").data["transition"]]
        assert t.attrs["duration"].value == 0.4 and t.attrs["ease"].bound

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
        model(f"{self.K} (canvas v s (on-click c (animation (move k (to 1) (duration 0)))))")


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

    # The author, 2026-11-08: a canvas may also zoom out past its view box, to a bound below 1.
    def test_out_past_the_view_box(self):
        a = model(f"{self.S} (canvas v (zoom 0.5 4) s)").get("v").attrs
        assert (a["zoom-min"].value, a["zoom-max"].value) == (0.5, 4)

    def test_the_lower_bound_above_zero(self):
        error(f"{self.S} (canvas v (zoom 0 4) s)", "a canvas's zoom bounds are above 0")

    def test_the_bounds_in_order(self):
        error(f"{self.S} (canvas v (zoom 4 2) s)", "from a lower bound to a higher one")

    def test_known_when_compiling(self):
        error(f"(real k 4) {self.S} (canvas v (zoom 1 k) s)", "known when compiling")


def test_a_control_takes_no_when():
    error(
        "(real k 0 (>= 0) (<= 1)) (button b (animation (move k (to 1) (duration 0))) (when true))",
        "active",
    )


class TestWhen:
    # The author, 2026-11-04: (when c x) gives x while c holds and none otherwise, anywhere an
    # expression may be; a canvas shows what an item gives, a shape, none or a list of them.
    S = "(bool show true) (scene s (circle a) (circle b))"

    def test_a_general_expression(self):
        assert isinstance(typ("(bool on true) (real|none v (when on 1))"), Maybe)
        error("(bool on true) (real v (when on 1))", "may be none")
        assert value("(bool on false (const)) (real|none v (when on 1))") is None

    def test_one_value(self):
        error(
            f"{self.S} (canvas v (when show a b))",
            r"give several in a list: \(when c \[a b\]\)",
        )

    def test_a_canvas_shows_what_an_item_gives(self):
        for item in ("(when show a)", "(when show [a b])", "(if show a b)", "[a b]"):
            model(f"{self.S} (canvas v {item})")

    @pytest.mark.parametrize(
        "items, ops",
        [
            ("(when show a) (if show a b) b", ["if", "if", "b"]),
            ("(if show a b) (when show a) b", ["if", "if", "b"]),
            ("(when show a) b (if show a b)", ["if", "b", "if"]),
            ("(when show a) [a b] b", ["if", "list", "b"]),
            ("[a b] (when show a) b", ["list", "if", "b"]),
        ],
    )
    def test_items_that_give_shapes_in_any_order(self, items, ops):
        # mtp-1l12: an (if …) item after a (when …) item was taken for an optional argument.
        m = model(f"{self.S} (canvas v (pan false) {items})")
        shows = m.get("v").data["shows"]
        assert [s if isinstance(s, int) else s.expr.op for s in shows] == [
            m.id(op) if op == "b" else op for op in ops
        ]

    def test_only_shapes(self):
        error(f"{self.S} (canvas v (when show 3))", "a canvas shows shapes")
        error(f"{self.S} (canvas v show)", "a canvas shows shapes")

    def test_the_compiled_file(self):
        d = doc(f"{self.S} (canvas v a (when show [a b]))")
        assert errors(d) == []
        shows = d["objects"][d["names"]["v"]]["shows"]
        assert shows[0] == d["names"]["a"] and "bound" in shows[1]


def test_a_let_in_a_group_reads_the_members_before_it():
    # Found 2026-11-05 writing examples/arrowheads.mtp: a let inside a group was worked out
    # before the group's members were declared, so it could not read them.
    from helpers import model

    m = model(
        "(scene s (group p (circle t (pos [1 1]))"
        " (let ((q t.pos)) (circle c (pos q)))"
        " (foreach k 2 (circle_ (x (+ t.x k))))))"
    )
    assert m.get("c").attrs["x"].bound or m.get("c").attrs["x"].value == 1


class TestPointerListeners:
    # mtp-izob: on-enter and on-leave follow JS's pointerenter and pointerleave, and
    # on-pointermove its pointermove (the author, 2026-11-06).
    S = f"{K} (point p [0 0]) (scene s (circle c (r 1)) (circle d (r 1))) (canvas v s"

    @pytest.mark.parametrize("kind", ["on-enter", "on-leave"])
    def test_a_hover_listener_on_a_shape(self, kind):
        m = model(f"{self.S} ({kind} c {MOVE}))")
        (o,) = [o for o in m.objects if o.kind == kind]
        assert o.data["shape"] == m.id("c")
        assert m.objects[o.data["animation"]].kind == "animation"
        assert o.name is None and "label" not in o.attrs

    @pytest.mark.parametrize("kind", ["on-enter", "on-leave"])
    def test_it_takes_what_it_listens_to(self, kind):
        error(f"{K} (scene s) (canvas v s ({kind} {MOVE}))", f"{kind} takes the shape")

    def test_a_pointer_move_on_a_shape_writes_a_point(self):
        m = model(f"{self.S} (on-pointermove c p))")
        (o,) = [o for o in m.objects if o.kind == "on-pointermove"]
        assert (o.data["shape"], o.data["view"]) == (m.id("c"), None)
        assert o.data["target"] == (m.id("p"), None)

    def test_a_pointer_move_on_a_canvas(self):
        m = model(f"{self.S} (on-pointermove p))")
        (o,) = [o for o in m.objects if o.kind == "on-pointermove"]
        assert (o.data["shape"], o.data["view"]) == (None, m.id("v"))

    def test_it_can_move_a_shape(self):
        m = model(f"{self.S} (on-pointermove d.pos (<= d.x 3) (>= d.y -1)))")
        (o,) = [o for o in m.objects if o.kind == "on-pointermove"]
        assert o.data["target"] == (m.id("d"), "pos")
        assert [c["target"] for c in o.data["conditions"]] == [(m.id("d"), "x"), (m.id("d"), "y")]

    def test_its_target_is_a_point(self):
        error(f"{self.S} (on-pointermove k))", "on-pointermove writes the pointer's position")

    def test_it_needs_a_target(self):
        error(f"{self.S} (on-pointermove))", r"on-pointermove is \(on-pointermove shape target")

    def test_its_target_is_free(self):
        error(
            f"{K} (point q [1 1] (const)) (scene s (circle c (r 1)))"
            " (canvas v s (on-pointermove q))",
            "q is const",
        )

    def test_a_group_is_moved_by_its_translate(self):
        src = "(scene s (group g (circle c (r 1)))) (canvas v s"
        error(f"{src} (on-pointermove g.pos))", "write its translate")
        model(f"{src} (on-pointermove g.translate))")

    def test_a_shape_inside_a_fixed_size_group_is_an_error(self):
        error(
            "(scene s (group g (fixed-size true) (circle c (r 3))))"
            " (canvas v s (on-pointermove c.pos))",
            "inside a fixed-size group",
        )

    def test_the_compiled_file(self):
        import json

        from mtpc_check import errors

        from mathterpiece.mtpc import write

        m = model(
            f"{self.S} (on-enter c {MOVE}) (on-leave c (active true) {MOVE})"
            " (on-pointermove c p) (on-pointermove d.pos (<= d.x 3)))"
        )
        d = json.loads(write(m))
        assert errors(d) == []
        kinds = [o["kind"] for o in d["objects"]]
        assert {"on-enter", "on-leave", "on-pointermove"} <= set(kinds)


class TestBubbling:
    # The author, 2026-11-06: as in the DOM, a click, a release, the start or end of a drag and a
    # pointer move go up the scene tree to every listener of their kind, unless one stops them.
    S = f"{K} (point p [0 0]) (scene s (group g (circle c (r 1)))) (canvas v s"

    @pytest.mark.parametrize("kind", ["on-click", "on-release", "on-dragstart", "on-dragend"])
    def test_a_listener_may_stop_the_event(self, kind):
        m = model(f"{self.S} ({kind} c (stop-propagation true) {MOVE}))")
        (o,) = [o for o in m.objects if o.kind == kind]
        assert o.data["stop-propagation"].value is True

    def test_by_default_it_goes_on(self):
        m = model(f"{self.S} (on-click c {MOVE}))")
        (o,) = [o for o in m.objects if o.kind == "on-click"]
        assert o.data["stop-propagation"] is None

    def test_a_pointer_move_may_stop_it(self):
        m = model(f"{self.S} (on-pointermove c p (stop-propagation true)))")
        (o,) = [o for o in m.objects if o.kind == "on-pointermove"]
        assert o.data["stop-propagation"].value is True

    @pytest.mark.parametrize(
        "decl, kind",
        [
            (f"(on-enter c (stop-propagation true) {MOVE}))", "on-enter"),
            (f"(on-leave c (stop-propagation true) {MOVE}))", "on-leave"),
            ("(on-drag c c.pos (stop-propagation true)))", "on-drag"),
            (f") (button b (stop-propagation true) {MOVE})", "button"),
        ],
    )
    def test_only_what_bubbles_takes_it(self, decl, kind):
        error(f"{self.S} {decl}", f"{kind} takes no stop-propagation")

    def test_the_compiled_file(self):
        import json

        from mtpc_check import errors

        from mathterpiece.mtpc import write

        m = model(
            f"{self.S} (on-click c (stop-propagation true) {MOVE}) (on-release g {MOVE})"
            " (on-pointermove c p (stop-propagation (> k 1))))"
        )
        d = json.loads(write(m))
        assert errors(d) == []
        stops = {o["kind"]: o["stop-propagation"] for o in d["objects"] if "stop-propagation" in o}
        assert stops["on-release"] is None and stops["on-click"] is not None


class TestMathLabels:
    # The author, 2026-11-09: a control's label may be LaTeX, (label (tex …)), the form a term of a
    # formula takes, for every control with a label.
    @pytest.mark.parametrize(
        "control",
        [
            f"(button b {MOVE} (label (tex 'C_3')))",
            f"(slider b {SLIDE} (label (tex 'C_3')))",
            f"(play b {MOVE} (label (tex 'C_3')))",
            f"(stepper b {MOVE} (label (tex 'C_3')))",
            "(bool on) (toggle b on (label (tex 'C_3')))",
        ],
    )
    def test_a_label_in_latex(self, control):
        d = doc(f"{K} {control}")
        (b,) = [o for o in d["objects"] if o.get("name") == "b"]
        assert b["attrs"]["label"] == {"type": "string", "free": "C_3"}
        assert b["label-tex"] is True
        assert errors(d) == []

    def test_a_latex_label_reads_the_model(self):
        b = model(f"{K} (foreach j 3 (button #'b-{{j}}' {MOVE} (label (tex $'C_{{j}}'))))").get(
            "b-2"
        )
        assert b.attrs["label"].value == "C_2" and b.data["label-tex"] is True

    def test_a_plain_label_is_not_latex(self):
        d = doc(f"{K} (button b {MOVE} (label 'go'))")
        (b,) = [o for o in d["objects"] if o.get("name") == "b"]
        assert "label-tex" not in b

    def test_tex_takes_one_string(self):
        error(f"{K} (button b {MOVE} (label (tex)))", r"\(tex …\) takes one string")
        error(f"{K} (button b {MOVE} (label (tex 'a' 'b')))", r"\(tex …\) takes one string")


# The author, 2026-11-13 (docs/concurrency-model.md): any writer, listener or control, may take
# (priority n), n an int from 1 to 1000. One without it has its kind's priority, which the runtime
# knows: 300 for on-view, 500 for what the reader triggers, 700 for a gesture. (exclusive) is gone.
SCENE = "(scene s (circle c (r 1)))"
PRIORITY = [
    ("slider", f"(slider w {SLIDE} (priority 900))"),
    ("button", f"(button w {MOVE} (priority 900))"),
    ("play", f"(play w {MOVE} (priority 900))"),
    ("stepper", f"(stepper w {MOVE} (priority 900))"),
    ("toggle", "(bool on) (toggle w on (priority 900))"),
    ("on-drag", "(canvas v s (on-drag c c.pos (priority 900)))"),
    ("on-click", f"(canvas v s (on-click c {MOVE} (priority 900)))"),
    ("on-release", f"(canvas v s (on-release c {MOVE} (priority 900)))"),
    ("on-dragstart", f"(canvas v s (on-dragstart c {MOVE} (priority 900)))"),
    ("on-dragend", f"(canvas v s (on-dragend c {MOVE} (priority 900)))"),
    ("on-enter", f"(canvas v s (on-enter c {MOVE} (priority 900)))"),
    ("on-leave", f"(canvas v s (on-leave c {MOVE} (priority 900)))"),
    ("on-view", f"(canvas v s (on-view {MOVE} (priority 900)))"),
    ("on-live", f"(canvas v s (on-live {MOVE} (priority 900)))"),
    ("on-quiet", f"(canvas v s (on-live {MOVE}) (on-quiet {MOVE} (priority 900)))"),
    ("on-pointermove", "(point p) (canvas v s (on-pointermove c p (priority 900)))"),
]


class TestPriority:
    @pytest.mark.parametrize("kind,src", PRIORITY)
    def test_every_writer_takes_it_and_the_file_says_so(self, kind, src):
        d = doc(f"{K} {SCENE} {src}")
        (w,) = [o for o in d["objects"] if o["kind"] == kind]
        assert w["priority"] == 900
        assert errors(d) == []

    @pytest.mark.parametrize("kind,src", PRIORITY)
    def test_a_writer_without_it_leaves_it_out(self, kind, src):
        d = doc(f"{K} {SCENE} {src.replace(' (priority 900)', '')}")
        (w,) = [o for o in d["objects"] if o["kind"] == kind]
        assert "priority" not in w

    @pytest.mark.parametrize("n", ["1", "1000"])
    def test_it_takes_an_int_from_1_to_1000(self, n):
        d = doc(f"{K} (button w {MOVE} (priority {n}))")
        (w,) = [o for o in d["objects"] if o["kind"] == "button"]
        assert w["priority"] == int(n)

    @pytest.mark.parametrize("n", ["0", "1001", "2.5", "k", "'high'"])
    def test_it_takes_nothing_else(self, n):
        error(
            f"{K} (button w {MOVE} (priority {n}))", r"\(priority n\) takes an int from 1 to 1000"
        )

    def test_it_takes_one_number(self):
        error(f"{K} (button w {MOVE} (priority))", r"\(priority n\) takes an int from 1 to 1000")
        error(
            f"{K} (button w {MOVE} (priority 1 2))", r"\(priority n\) takes an int from 1 to 1000"
        )

    def test_it_is_given_once(self):
        error(f"{K} (button w {MOVE} (priority 1) (priority 2))", "'priority' is given twice")

    def test_exclusive_is_gone(self):
        error(
            f"{K} (button w {MOVE} (exclusive))",
            r"\(exclusive\) is gone: give the writer a \(priority n\)",
        )
