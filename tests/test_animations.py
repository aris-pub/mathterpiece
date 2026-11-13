"""Transitions and animations (docs/reference.md "Transitions and animations" and "Writes and
conditions"; docs/mtpc.md "Steps" and "Transitions")."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors


def steps(src, name="a"):
    return model(src).get(name).data["steps"]


K = "(real k 0 (>= 0) (<= 10))"


# An ease of the author's own, as the tests compile sources with no file to import from.
CUBE = "(func cube ((real t (>= 0) (<= 1))) (* t t t))"


class TestTransitions:
    def test_a_named_transition(self):
        m = model(f"{K} (transition up none (to 5) (duration 1)) (animation a (move k (like up)))")
        t = m.get("up")
        assert t.kind == "transition"
        assert t.attrs["to"].value == 5
        assert "from" not in t.attrs
        # (like up) makes the move a transition of its own, with up's arguments.
        move = m.get("a").data["steps"]
        assert (move[0], move[1], move[3:]) == ("move", (m.id("k"), None), (1, "linear"))
        assert m.objects[move[2]].attrs["to"].value == 5

    def test_an_inline_transition_comes_before_its_holder(self):
        m = model(f"{K} (animation a (move k (to 5) (duration 1)))")
        (tid,) = [i for i, o in enumerate(m.objects) if o.kind == "transition"]
        assert tid == m.id("a") - 1

    def test_the_end_must_fit_what_it_moves(self):
        error(f"{K} (animation a (move k (to 'x') (duration 1)))", "expected real")

    def test_a_string_end_becomes_a_color(self):
        m = model("(scene s (circle c)) (animation a (move c.fill (to 'red') (duration 1)))")
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["to"].value == "#ff0000ff"

    def test_an_end_that_may_be_none(self):
        src = "(real|none e) (scene s (circle c))"
        error(
            f"{K} {src} (animation a (move k (to e) (duration 1)))", "declare what it moves T|none"
        )
        model("(color|none e) (scene s (circle c))(animation a (move c.fill (to e) (duration 1)))")

    def test_a_target_declared_t_or_none_may_be_moved_to_none(self):
        # The author, 2026-11-06: declaring T|none says the target may hold none, so a move may
        # take it there or back; web/test/none-moves.test.ts has how it jumps.
        for src in (
            "(real|none m 2) (animation a (move m (to none) (duration 1)))",
            "(real|none m none) (animation a (move m (from none) (to 3) (duration 1)))",
            "(type piece string (one-of 'gap' 'b2')) (piece|none shown 'gap')"
            " (animation a (move shown (to (if (= shown 'gap') none 'gap')) (duration 0.25)))",
        ):
            model(src)

    def test_a_sliders_ends_are_never_none(self):
        error(
            "(real|none m 2) (slider s (move m (from 0) (to none)))",
            "a slider's ends may not be none",
        )

    def test_eases_and_paths(self):
        m = model(
            f"{K} (func half ((real a) (real b) (real t)) (+ a (* t (- b a))))"
            "(animation a (move k (to 5) (duration 1) (ease (step 4)) (path half)))"
        )
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["ease"].value == ("step", 4)
        assert t.attrs["path"].expr.op == "func"
        error(f"{K} (animation a (move k (to 5) (duration 1) (ease 'wobbly')))", "ease")

    def test_an_ease_is_not_a_quoted_name(self):
        # The author, 2026-11-05: the named eases are functions in the ease file, such as
        # cubic-in-out; only (step n) is built in.
        error(
            f"{K} (animation a (move k (to 5) (duration 1) (ease 'ease-in-out')))",
            "an ease is a function",
        )

    def test_a_negative_duration(self):
        error(f"{K} (animation a (move k (to 5) (duration -1)))", "cannot be negative")


class TestSteps:
    def test_defaults_and_nesting(self):
        s = steps(
            f"{K} {CUBE} (real j 0) (animation a (defaults (duration 2) (ease cube))"
            " (move k (to 5)) (move none (duration 1))"
            " (at-once (defaults (duration 3)) (move j (to 1))"
            " (move k (to 1) (duration 4))))"
        )
        assert s[0] == "in-order"
        assert s[1][3] == 2 and s[1][4][0] == "func"
        # A wait keeps its transition, for a.steps; the .mtpc writes only its duration.
        assert s[2][:2] == ("wait", 1)
        assert s[3][0] == "at-once"
        assert s[3][1][3] == 3 and s[3][2][3] == 4

    def test_a_move_takes_a_transitions_items(self):
        # reference.md "Transitions and animations": inside a step, the transition is implied.
        s = steps(f"{K} {CUBE} (animation a (move k (from 1) (to 5) (duration 2) (ease cube)))")
        assert s[3] == 2 and s[4][0] == "func"

    def test_a_move_takes_a_named_transition(self):
        m = model(
            f"{K} (transition slide none (to 5) (duration 1)) (animation a (move k (like slide)))"
        )
        move = m.get("a").data["steps"]
        assert move[:2] == ("move", (m.id("k"), None))
        t = m.objects[move[2]]
        assert t.kind == "transition" and t.attrs["to"].value == 5

    def test_an_animation_holds_only_moves_at_once_and_in_order(self):
        error(f"{K} (animation a (k (to 5) (duration 1)))", "holds moves, waits, at-once, in-order")

    def test_a_move_with_no_target_only_waits(self):
        # A wait keeps its transition, for a.steps; the .mtpc writes only its duration.
        assert steps(f"{K} (animation a (move none (duration 2)))")[:2] == ("wait", 2)
        error(f"{K} (animation a (move none (to 1) (duration 2)))", "takes only a duration")

    def test_wait_is_a_move_with_no_target(self):
        # The author, 2026-11-03: (wait t) stands for (move none (duration t)).
        assert steps(f"{K} (animation a (wait 2))") == ("wait", 2)
        assert steps(f"{K} (animation a (defaults (duration 3)) (wait))") == ("wait", 3)

        def written(src):
            return next(o for o in doc(src)["objects"] if o.get("name") == "a")["steps"]

        assert written(f"{K} (animation a (move k (to 5) (duration 1)) (wait 0.5))") == (
            written(f"{K} (animation a (move k (to 5) (duration 1)) (move none (duration 0.5)))")
        )
        error(f"{K} (animation a (wait))", "this wait needs a duration")
        error(f"{K} (animation a (wait 1 2))", r"wait is \(wait seconds\)")

    def test_a_named_transition_with_a_target_is_a_move(self):
        s = steps(f"{K} (transition grow k (to 5) (duration 1)) (animation a grow)")
        assert s[0] == "move" and s[3] == 1

    def test_like_copies_a_named_transition_under_its_own_arguments(self):
        src = f"{K} (transition slide none (to 5) (duration 1))"
        src += " (animation a (move k (like slide) (duration 3)))"
        assert steps(src)[3] == 3

    def test_a_transition_needs_a_duration(self):
        error(f"{K} (animation a (move k (to 5)))", "needs a duration")

    def test_what_can_be_moved(self):
        m = model(
            "(motif dot (real k 0) (circle c)) (scene s (dot d) (group g (circle a) (circle b)))"
            "(animation an (move d.k (to 1) (duration 1))"
            " (move g[1].r (to 2) (duration 1))"
            " (move g.r (to 3) (duration 1))"
            " (move d.c.pos (to [1 1]) (duration 1)))"
        )
        s = m.get("an").data["steps"]
        assert [x[1] for x in s[1:]] == [
            (m.id("d"), "k"),
            (m.id("b"), "r"),
            (m.id("g"), "r"),
            (m.id("d.c"), "pos"),
        ]

    @pytest.mark.parametrize(
        "src, message",
        [
            ("(real j 1) (real k (* 2 j))", "k is bound"),
            ("(real k 1 (const))", "k is const"),
            ("(color k 'red')", "k is a token"),
        ],
    )
    def test_what_cannot_be_moved(self, src, message):
        error(f"{src} (animation a (move k (to 1) (duration 1)))", message)

    def test_a_fixed_attribute(self):
        src = "(variant bar () (rect_ (width 1))) (scene s (bar b))"
        error(f"{src} (animation a (move b.width (to 2) (duration 1)))", "fixed")


class TestBoolMoves:
    # reference.md "Transitions and animations": a bool changes at the start of its move and
    # holds, unless its own ease is a step ease.
    B = "(bool on false)"

    def test_the_default_is_one_jump_at_the_start(self):
        s = steps(f"{self.B} (animation a (move on (to true) (duration 1)))")
        assert s[4] == ("step", 1)

    def test_an_enclosing_default_ease_that_is_not_a_step_does_not_apply(self):
        move = "(move on (to true) (duration 1))"
        src = f"{self.B} {CUBE} (animation a (defaults (ease cube)) {move})"
        assert steps(src)[4] == ("step", 1)

    @pytest.mark.parametrize("ease", ["cube", "(step 3)"])
    def test_an_ease_that_takes_values_other_than_0_and_1(self, ease):
        # (step 3) jumps to 1/3 and 2/3, which mean nothing for a bool.
        error(
            f"{self.B} {CUBE} (animation a (move on (to true) (duration 1) (ease {ease})))",
            "an ease for a bool takes only the values 0 and 1",
        )


class TestChoiceMoves:
    # A choice string moves like a bool: it changes at the start unless a discrete ease says
    # otherwise.
    SIDE = "(type side string (one-of 'left' 'right')) (side s 'left')"

    def test_the_default(self):
        assert steps(f"{self.SIDE} (animation a (move s (to 'right') (duration 1)))")[4] == (
            "step",
            1,
        )

    def test_a_continuous_ease_is_an_error(self):
        move = "(move s (to 'right') (duration 1) (ease cube))"
        error(
            f"{self.SIDE} {CUBE} (animation a {move})",
            "an ease for a choice takes only the values 0 and 1",
        )


class TestStepEase:
    # reference.md: (step-ease p) is 0 before progress p and 1 from p on.
    B = "(bool on false)"

    def test_a_bool_may_take_it(self):
        move = "(move on (to true) (duration 1) (ease (step-ease 0.5)))"
        assert steps(f"{self.B} (animation a {move})")[4] == ("step-ease", 0.5)

    def test_its_point_is_from_0_to_1_known_when_compiling(self):
        move = "(move on (to true) (duration 1) (ease (step-ease 2)))"
        error(f"{self.B} (animation a {move})", r"2 breaks \(<= 1\)")


class TestStringMoves:
    # A string, like a bool or a choice, changes at the start of its move by default.
    def test_the_default(self):
        src = "(string s 'a') (animation a (move s (to 'b') (duration 1)))"
        assert steps(src)[4] == ("step", 1)


class TestNamedAnimationsAsSteps:
    def test_a_named_animation_runs_its_steps_in_place(self):
        src = (
            f"{K} (real j 0) (animation one (move k (to 5) (duration 1)))"
            "(animation a one (move none (duration 1)) (move j (to 2) (duration 1)))"
        )
        m = model(src)
        s = m.get("a").data["steps"]
        assert s[0] == "in-order"
        assert s[1] == m.get("one").data["steps"]
        # A wait keeps its transition, for a.steps; the .mtpc writes only its duration.
        assert s[2][:2] == ("wait", 1)


class TestLoops:
    # mtp-aql: (loop n) repeats an animation n times, (loop) forever; a round that ends somewhere
    # other than where the next starts just jumps (docs/reference.md, "Transitions and
    # animations"; docs/mtpc.md, "Steps").
    def test_loop_n_repeats_the_body(self):
        m = model(f"{K} (animation a (loop 3) (move k (from 0) (to 1) (duration 2)))")
        loop = m.get("a").data["steps"]
        assert (loop[0], loop[1], loop[2][0]) == ("loop", 3, "move")
        assert m.get("a").attrs["duration"].value == 6

    def test_loop_without_a_count_repeats_forever(self):
        m = model(f"{K} (animation a (loop) (move k (to 1) (duration 2)) (move none (duration 1)))")
        loop = m.get("a").data["steps"]
        assert (loop[0], loop[1], loop[2][0]) == ("loop", None, "in-order")

    def test_a_loop_takes_a_positive_int_known_when_compiling(self):
        error(f"{K} (animation a (loop 0) (move k (to 1) (duration 1)))", "at least 1")
        error(f"{K} (animation a (loop 1.5) (move k (to 1) (duration 1)))", "int")
        error(f"{K} (real n 2) (animation a (loop n) (move k (to 1) (duration 1)))", "known")

    def test_a_round_takes_time(self):
        error(f"{K} (animation a (loop) (move k (to 1) (duration 0)))", "takes no time")

    def test_only_an_animation_loops(self):
        error(
            f"{K} (animation a (in-order (loop) (move k (to 1) (duration 1))))",
            "an animation holds moves",
        )

    def test_loop_comes_before_the_body(self):
        error(f"{K} (animation a (move k (to 1) (duration 1)) (loop))", "before")

    def test_an_inline_animation_loops(self):
        m = model(f"{K} (button b (animation (loop 2) (move k (to 1) (duration 1))))")
        a = m.objects[m.get("b").data["animation"]]
        assert a.data["steps"][0] == "loop"

    def test_a_looping_animation_named_in_another_keeps_its_loop(self):
        m = model(
            f"{K} (animation spin (loop 2) (move k (to 1) (duration 1)))"
            " (animation a spin (move none (duration 1)))"
        )
        assert m.get("a").data["steps"][1][0] == "loop"
        assert m.get("a").attrs["duration"].value == 3

    def test_the_compiled_file_writes_the_loop(self):
        d = doc(f"{K} (animation a (loop) (move k (to 1) (duration 1)))")
        assert d["objects"][d["names"]["a"]]["steps"][:2] == ["loop", None]
        assert errors(d) == []


class TestForeverDuration:
    # The author, 2026-11-03: an animation that loops forever lasts ∞.
    def test_it_lasts_infinity(self):
        m = model(
            f"{K} (animation a (loop) (move k (to 1) (duration 2))) (real d a.duration (const))"
        )
        assert m.get("d").value.value == float("inf")


class TestAnimationDefaults:
    # mtp-xj5b: (defaults (duration t) (ease e)) on an animation, at-once or in-order.
    def test_on_an_animation(self):
        s = steps(f"{K} {CUBE} (animation a (defaults (duration 2) (ease cube)) (move k (to 1)))")
        assert s[3] == 2 and s[4][0] == "func"

    def test_on_at_once(self):
        s = steps(f"{K} (animation a (at-once (defaults (duration 3)) (move k (to 1))))")
        assert s[1][3] == 3

    def test_the_old_forms_are_gone(self):
        error(f"{K} (animation a (default-duration 2) (move k (to 1)))", "an animation holds moves")


class TestTheTypeOfAnEase:
    # The author, 2026-11-03: an ease is a function of a real from 0 to 1, so one defined only
    # there is accepted, as is one defined on every real.
    def test_one_defined_from_0_to_1(self):
        model(
            f"{K} (func spring ((real t 0 (>= 0) (<= 1))) (- 1 (^ (- 1 t) 3)))"
            " (animation a (move k (to 5) (duration 1) (ease spring)))"
        )

    def test_one_defined_on_every_real(self):
        model(
            f"{K} (func half (real t) (* t t))"
            " (animation a (move k (to 5) (duration 1) (ease half)))"
        )

    def test_its_value_may_go_past_1(self):
        model(
            f"{K} (func over ((real t 0 (>= 0) (<= 1))) (* 1.3 t))"
            " (animation a (move k (to 5) (duration 1) (ease over)))"
        )

    def test_one_that_needs_more_than_0_to_1_is_refused(self):
        error(
            f"{K} (func picky ((real t 0.5 (>= 0.5) (<= 1))) t)"
            " (animation a (move k (to 5) (duration 1) (ease picky)))",
            "expected func",
        )


class TestForeachInAnAnimation:
    # mtp-6jt0, the author 2026-11-03: a foreach in an animation's body puts its moves where it
    # is written: together inside at-once, one after another inside in-order or in a row.
    G = "(scene s (group g (circle a) (circle b) (circle c)))"

    def test_over_a_group_at_once(self):
        body = "(at-once (defaults (duration 1)) (foreach d g (move d.r (to 2))))"
        s = steps(f"{self.G} (animation an {body})", "an")
        assert s[0] == "at-once" and len(s) == 4 and all(x[0] == "move" for x in s[1:])

    def test_one_after_another(self):
        m = model(f"{K} (animation an (foreach v [1 2 3] (move k (to v) (duration 1))))")
        assert m.get("an").attrs["duration"].value == 3

    def test_with_waits_and_a_count(self):
        m = model(f"{K} (animation an (foreach i 2 (move k (to i) (duration 1)) (wait 0.5)))")
        assert m.get("an").attrs["duration"].value == 3

    def test_the_count_must_be_known_when_compiling(self):
        error(
            f"{K} (int n 2) (animation an (foreach i n (move k (to i) (duration 1))))",
            "known when compiling",
        )

    def test_let_is_still_not_an_animation_item(self):
        error(
            f"{K} (animation an (let ((v 1)) (move k (to v) (duration 1))))",
            "holds moves, waits, at-once, in-order",
        )


class TestReadingSteps:
    # mtp-76h. The author, 2026-11-06: a.steps is every transition the animation plays, in the
    # order it plays them, through at-once, in-order and the animations it names, waits
    # included; one round of a loop; no start times.
    K = "(real k 0) (real j 0)"

    def durations(self, body):
        m = model(f"{self.K} {body} (int n a.steps.length)")
        n = m.get("n").value.value
        reads = " ".join(f"(real d{k} a.steps[{k}].duration)" for k in range(n))
        m = model(f"{self.K} {body} {reads}")
        return [m.get(f"d{k}").value.value for k in range(n)]

    def test_in_the_order_they_play(self):
        body = (
            "(animation b (move j (to 2) (duration 0.5)))"
            " (animation a (move k (to 1) (duration 2)) (wait 1)"
            " (at-once (move j (to 1) (duration 3)) (move k (to 0) (duration 4)))"
            " b (move none (duration 0.25)))"
        )
        assert self.durations(body) == [2, 1, 3, 4, 0.5, 0.25]

    def test_one_round_of_a_loop(self):
        assert self.durations("(animation a (loop 3) (move k (to 1) (duration 2)))") == [2]

    def test_its_length_is_known_when_compiling(self):
        m = model(
            f"{self.K} (animation a (move k (to 1) (duration 2)) (wait 1))"
            " (scene s (foreach t a.steps (circle_ (r t.duration))))"
        )
        assert [o.attrs["r"].value for o in m.objects if o.kind == "circle"] == [2, 1]

    def test_a_step_is_read_like_a_transition(self):
        m = model(f"{self.K} (animation a (move k (to 1) (duration 2))) (real v a.steps[0].to)")
        assert m.get("v").value.value == 1

    def test_a_wait_gets_a_transition_only_when_the_steps_are_read(self):
        def transitions(src):
            return sum(o.kind == "transition" for o in model(src).objects)

        src = f"{self.K} (animation a (move k (to 1) (duration 2)) (wait 1))"
        assert transitions(src) == 1
        assert transitions(src + " (int v a.steps.length)") == 2


class TestTogether:
    # mtp-lm24: moves that run together read the same values when they start, so two of them
    # writing the same variable or attribute describe no one state; in-order may.
    def test_the_same_variable_twice(self):
        error(
            f"{K} (animation a (at-once (move k (to 1) (duration 1))"
            " (move k (to 2) (duration 1))))",
            "k is moved twice at the same time in this at-once",
        )

    def test_a_position_and_its_x(self):
        error(
            "(scene s (circle c (r 1)))"
            " (animation a (at-once (move c.pos (to [1 1]) (duration 1))"
            " (move c.x (to 3) (duration 1))))",
            "c.x is moved twice at the same time in this at-once",
        )

    def test_inside_an_in_order_and_a_named_animation(self):
        src = (
            f"{K} (animation up (move k (to 3) (duration 1)))"
            " (animation a (at-once (in-order (wait 0.5) (move k (to 1) (duration 1))) up))"
        )
        error(src, "k is moved twice at the same time in this at-once")

    def test_at_different_times_is_fine(self):
        # As examples/bourgain-densities.mtp does: once at the start, and again much later.
        steps(
            f"{K} (animation a (at-once (move k (to 1) (duration 0))"
            " (in-order (wait 2) (move k (to 2) (duration 1)))))"
        )

    def test_a_loop_runs_until_it_is_stopped(self):
        error(
            f"{K} (animation up (loop) (move k (to 3) (duration 1)))"
            " (animation a (at-once up (in-order (wait 5) (move k (to 1) (duration 1)))))",
            "k is moved twice at the same time in this at-once",
        )

    def test_different_targets_and_in_order_are_fine(self):
        steps(
            f"{K} (real j 0) (animation a (at-once (move k (to 1) (duration 1))"
            " (move j (to 2) (duration 1))))"
        )
        steps(
            f"{K} (animation a (in-order (move k (to 1) (duration 1))"
            " (move k (to 2) (duration 1))))"
        )
