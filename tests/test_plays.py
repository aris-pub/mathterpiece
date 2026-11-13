"""Plays and steppers whose step is read from the scene, a canvas's on-rest, and a move written
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
    # A move in a play or a stepper whose to reads the value it moves: its step could not be read
    # from the scene (the author, 2026-11-13).
    def test_a_move_whose_to_reads_its_target(self):
        error(f"{K} (play p (move k (to (+ k 1)) (duration 1)))", "reads k, the value it moves")
        error(f"{K} (stepper p (move k (to (* k 2)) (duration 1)))", "reads k")

    def test_through_a_bound_variable(self):
        error(f"{K} (real twice (* k 2)) (play p (move k (to twice) (duration 1)))", "reads k")

    def test_a_to_reading_another_value_is_fine(self):
        assert errors(doc(f"{K} {J} (play p (move k (to (+ j 1)) (duration 1)))")) == []

    def test_a_button_may_read_what_it_moves(self):
        assert errors(doc(f"{K} (button b (move k (to (+ k 1)) (duration 1)))")) == []

    def test_on_view_and_on_rest_too(self):
        error(f"{S} (canvas v s (on-view (move k (to (+ k 1)) (duration 1))))", "reads k")
        error(f"{S} (canvas v s (on-rest (move k (to (+ k 1)) (duration 1))))", "reads k")


class TestOnRest:
    def test_on_rest_in_a_canvas(self):
        m = model(f"{S} (canvas v s (on-rest (animation {UP})))")
        (o,) = [o for o in m.objects if o.kind == "on-rest"]
        assert o.data["view"] == m.id("v")
        assert o.name is None and o.access == "page"

    def test_the_compiled_on_rest(self):
        d = doc(f"{S} (canvas v s (on-rest (animation (loop) {UP} {DOWN})))")
        (o,) = [o for o in d["objects"] if o["kind"] == "on-rest"]
        assert o["view"] == d["names"]["v"]
        assert errors(d) == []

    def test_on_rest_is_inside_a_canvas(self):
        error(f"{K} (readout r 'x' (on-rest {UP}))", "so it is written inside a canvas")

    def test_an_on_view_may_not_loop(self):
        error(f"{S} (canvas v s (on-view (animation (loop) {UP} {DOWN})))", "on-view may not loop")

    def test_an_on_view_may_loop_a_count_of_times(self):
        assert errors(doc(f"{S} (canvas v s (on-view (animation (loop 2) {UP} {DOWN})))")) == []

    def test_a_loop_another_writer_writes_is_an_error(self):
        loop = f"(on-rest (animation (loop) {UP} {DOWN}))"
        error(f"{S} (canvas v s {loop}) (button b (move k (to 5) (duration 1)))", "writes k")

    def test_a_loop_reading_what_another_writer_writes_is_an_error(self):
        loop = "(on-rest (animation (loop) (move k (to (+ j 1)) (duration 1)) " + DOWN + "))"
        error(f"{S} (canvas v s {loop}) (button b (move j (to 5) (duration 1)))", "writes j")

    def test_its_own_on_view_does_not_count(self):
        src = f"{S} (canvas v s (on-view {UP}) (on-rest (animation (loop) {UP} {DOWN})))"
        assert errors(doc(src)) == []

    def test_a_loop_that_ends_is_an_ordinary_writer(self):
        loop = f"(on-rest (animation (loop 2) {UP} {DOWN}))"
        src = f"{S} (canvas v s {loop}) (button b (move k (to 5) (duration 1)))"
        assert errors(doc(src)) == []
