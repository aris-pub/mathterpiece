"""Plays and steppers whose step is read from the scene, a canvas's on-ready, and a move written
where an animation is (mtp-wjtd; docs/reference.md "Controls", docs/canvas-lifecycle.md)."""

from helpers import doc, error, model
from mtpc_check import errors

K = "(real k 0 (>= 0) (<= 10))"
J = "(real j 0)"
UP = "(move k (to 2) (duration 1))"
DOWN = "(move k (to 0) (duration 1))"
S = f"{K} {J} (scene s (circle c (r k)))"


class TestPlayAttributes:
    def test_a_play_has_a_step_and_playing_only(self):
        p = model(f"{K} (play p (animation {UP}))").get("p")
        assert (p.attrs["playing"].value, p.attrs["step"].value) == (False, 0)
        assert "time" not in p.attrs

    def test_a_play_has_no_time(self):
        error(f"{K} (play p (animation {UP})) (real later (+ p.time 1))", "time")

    def test_a_stepper_starts_at_step_0(self):
        s = model(f"{K} (stepper s (animation {UP}))").get("s")
        assert s.attrs["step"].value == 0


class TestAutoplayIsGone:
    def test_autoplay_is_a_compile_error(self):
        error(f"{S} (play p (autoplay) (animation {UP}))", r"\(autoplay\) is gone")
        error(f"{S} (canvas v s) (play p (autoplay v) (animation {UP}))", r"\(autoplay\) is gone")
        error(f"{K} (stepper s (autoplay) (animation {UP}))", r"\(autoplay\) is gone")

    def test_the_compiled_play_has_no_autoplay(self):
        d = doc(f"{K} (play p (animation {UP}))")
        (p,) = [o for o in d["objects"] if o["kind"] == "play"]
        assert "autoplay" not in p
        assert errors(d) == []


class TestLabels:
    def test_the_step_form_is_gone(self):
        error(f"{K} (play p (animation (step 'Up' {UP}) {DOWN}))", r"\(step …\) is gone")

    def test_a_play_takes_one_label_per_step(self):
        d = doc(f"{K} (play p (labels 'Up' 'Down') (animation {UP} {DOWN}))")
        (p,) = [o for o in d["objects"] if o["kind"] == "play"]
        assert p["labels"] == ["Up", "Down"]
        assert errors(d) == []

    def test_one_step_takes_one_label(self):
        both = "(at-once (move k (to 2) (duration 1)) (move j (to 1) (duration 1)))"
        p = model(f"{K} {J} (play p (labels 'All') (animation {both}))").get("p")
        assert p.data["labels"] == ["All"]

    def test_the_count_of_labels_is_the_count_of_steps(self):
        error(f"{K} (play p (labels 'Up') (animation {UP} {DOWN}))", "2 steps, but 1 label")
        error(f"{K} (play p (labels 'a' 'b' 'c') (animation {UP} {DOWN}))", "2 steps, but 3")

    def test_labels_count_the_steps_of_a_loop(self):
        p = model(f"{K} (play p (labels 'a' 'b') (animation (loop) {UP} {DOWN}))").get("p")
        assert p.data["labels"] == ["a", "b"]

    def test_a_label_is_a_string_known_when_compiling(self):
        error(f"{K} (play p (labels (+ k 1)) (animation {UP}))", "a label is a string")
        error(f"(string t 'x') {K} (play p (labels t) (animation {UP}))", "known when compiling")

    def test_without_labels_none_are_written(self):
        d = doc(f"{K} (play p (animation {UP} {DOWN}))")
        (p,) = [o for o in d["objects"] if o["kind"] == "play"]
        assert "labels" not in p

    def test_only_a_play_takes_labels(self):
        error(f"{K} (stepper s (labels 'a') (animation {UP}))", r"only a play takes \(labels")
        error(f"{K} (button b (labels 'a') (animation {UP}))", r"only a play takes \(labels")


class TestAMoveIsAnAnimation:
    def test_a_button_takes_a_move(self):
        a = doc(f"{K} (button b (move k (to 2) (duration 0.4)))")
        b = doc(f"{K} (button b (animation (move k (to 2) (duration 0.4))))")
        assert a == b

    def test_a_play_a_toggle_and_a_listener_take_a_move(self):
        for src in (
            f"{K} (play p {UP})",
            f"{K} (stepper p {UP})",
            f"{K} (bool on) (toggle t on {UP})",
            f"{S} (canvas v s (on-click c {UP}))",
            f"{S} (canvas v s (on-view {UP}))",
        ):
            assert errors(doc(src)) == []

    def test_a_move_and_an_animation_are_the_animation_twice(self):
        error(f"{K} (button b {UP} (animation {DOWN}))", "'animation' is given twice")


class TestStepsCanBeWorkedOut:
    # A move in a play or a stepper whose to expression depends on the value its move writes: its
    # step could not be read
    # from the scene (the author, 2026-11-13).
    def test_a_move_whose_to_depends_on_its_target(self):
        src = f"{K} (play p (move k (to (+ k 1)) (duration 1)))"
        error(src, "to expression depends on k, the value its move writes")
        error(f"{K} (stepper p (move k (to (* k 2)) (duration 1)))", "depends on k")

    def test_through_a_bound_variable(self):
        error(f"{K} (real twice (* k 2)) (play p (move k (to twice) (duration 1)))", "depends on k")

    def test_a_to_reading_another_value_is_fine(self):
        assert errors(doc(f"{K} {J} (play p (move k (to (+ j 1)) (duration 1)))")) == []

    def test_a_button_may_read_what_it_moves(self):
        assert errors(doc(f"{K} (button b (move k (to (+ k 1)) (duration 1)))")) == []

    def test_on_view_too(self):
        error(f"{S} (canvas v s (on-view (move k (to (+ k 1)) (duration 1))))", "depends on k")

    def test_on_ready_may_read_what_it_moves(self):
        src = f"{S} (canvas v s (on-ready (animation (loop) (move k (to (+ k 1)) (duration 1)))))"
        assert errors(doc(src)) == []


class TestOnReady:
    def test_on_ready_in_a_canvas(self):
        m = model(f"{S} (canvas v s (on-ready (animation {UP})))")
        (o,) = [o for o in m.objects if o.kind == "on-ready"]
        assert o.data["view"] == m.id("v")
        assert o.name is None and o.access == "page"

    def test_the_compiled_on_ready(self):
        d = doc(f"{S} (canvas v s (on-ready (animation (loop) {UP} {DOWN})))")
        (o,) = [o for o in d["objects"] if o["kind"] == "on-ready"]
        assert o["view"] == d["names"]["v"]
        assert errors(d) == []

    def test_on_ready_is_inside_a_canvas(self):
        error(f"{K} (readout r 'x' (on-ready {UP}))", "so it is written inside a canvas")

    def test_an_on_view_may_not_loop(self):
        error(f"{S} (canvas v s (on-view (animation (loop) {UP} {DOWN})))", "on-view may not loop")

    def test_an_on_view_may_loop_a_count_of_times(self):
        assert errors(doc(f"{S} (canvas v s (on-view (animation (loop 2) {UP} {DOWN})))")) == []

    # The author, 2026-11-13: on-ready may play any animation, loop or not, whatever other
    # writers write.
    def test_a_loop_another_writer_writes_is_fine(self):
        loop = f"(on-ready (animation (loop) {UP} {DOWN}))"
        src = f"{S} (canvas v s {loop}) (button b (move k (to 5) (duration 1)))"
        assert errors(doc(src)) == []


class TestCanvasesOfAControl:
    # The author, 2026-11-13: until a canvas is ready, every input that belongs to it is disabled.
    # A control belongs to a canvas when it writes a value some shape the canvas shows depends on.
    SRC = (
        f"{K} {J} (real far 1 (>= 0)) (bool on false)"
        " (scene s (group g (circle c (r k)) (circle d (x j))) (circle e (r far)))"
        " (canvas v g (on-view (move k (to 2) (duration 1))))"
        " (canvas w e)"
        " (canvas some (when on d))"
    )

    def canvases(self, src, name):
        d = doc(src)
        assert errors(d) == []
        return sorted(d["objects"][d["names"][name]].get("canvases", []))

    def test_a_control_writing_what_a_shown_shape_depends_on(self):
        src = self.SRC + " (button b (move k (to 5) (duration 1)))"
        d = doc(src)
        assert self.canvases(src, "b") == [d["names"]["v"]]

    def test_a_control_writing_a_shapes_own_attribute(self):
        # d is in g, which v shows, and some may show d.
        src = self.SRC + " (slider sl (move d.r (from 0) (to 3)))"
        d = doc(src)
        assert self.canvases(src, "sl") == sorted([d["names"]["v"], d["names"]["some"]])

    def test_a_control_writing_what_decides_what_a_canvas_shows(self):
        src = self.SRC + " (toggle tg on)"
        d = doc(src)
        assert self.canvases(src, "tg") == [d["names"]["some"]]

    def test_a_control_writing_a_value_of_two_canvases(self):
        src = (
            self.SRC
            + " (play p (animation (move j (to 1) (duration 1)) (move far (to 2) (duration 1))))"
        )
        d = doc(src)
        assert self.canvases(src, "p") == sorted([d["names"][n] for n in ("v", "w", "some")])

    def test_a_control_writing_nothing_shown_belongs_to_none(self):
        src = self.SRC + " (real other 0) (button b (move other (to 5) (duration 1)))"
        d = doc(src)
        assert "canvases" not in d["objects"][d["names"]["b"]]
