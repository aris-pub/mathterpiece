"""Transitions and animations (docs/reference.md "Transitions and animations" and "Writes and
conditions"; docs/mtpc.md "Steps" and "Transitions")."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors


def steps(src, name="a"):
    return model(src).get(name).data["steps"]


K = "(real k 0 (>= 0) (<= 10))"


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
        error(f"{K} {src} (animation a (move k (to e) (duration 1)))", "may be none")
        model("(color|none e) (scene s (circle c))(animation a (move c.fill (to e) (duration 1)))")

    def test_eases_and_paths(self):
        m = model(
            f"{K} (func half ((real a) (real b) (real t)) (+ a (* t (- b a))))"
            "(animation a (move k (to 5) (duration 1) (ease (step 4)) (path half)))"
        )
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["ease"].value == ("step", 4)
        assert t.attrs["path"].expr.op == "func"
        error(f"{K} (animation a (move k (to 5) (duration 1) (ease 'wobbly')))", "ease")

    def test_a_negative_duration(self):
        error(f"{K} (animation a (move k (to 5) (duration -1)))", "cannot be negative")


class TestSteps:
    def test_defaults_and_nesting(self):
        s = steps(
            f"{K} (real j 0) (animation a (defaults (duration 2) (ease 'ease-in'))"
            " (move k (to 5)) (move none (duration 1))"
            " (at-once (defaults (duration 3)) (move j (to 1))"
            " (move k (to 1) (duration 4))))"
        )
        assert s[0] == "in-order"
        assert s[1][3:] == (2, "ease-in")
        assert s[2] == ("wait", 1)
        assert s[3][0] == "at-once"
        assert s[3][1][3] == 3 and s[3][2][3] == 4

    def test_a_move_takes_a_transitions_items(self):
        # reference.md "Transitions and animations": inside a step, the transition is implied.
        s = steps(f"{K} (animation a (move k (from 1) (to 5) (duration 2) (ease 'ease-in')))")
        assert s[3:] == (2, "ease-in")

    def test_a_move_takes_a_named_transition(self):
        steps(
            f"{K} (transition slide none (to 5) (duration 1)) (animation a (move k (like slide)))"
        )

    def test_an_animation_holds_only_moves_at_once_and_in_order(self):
        error(f"{K} (animation a (k (to 5) (duration 1)))", "holds moves, at-once and in-order")

    def test_a_move_with_no_target_only_waits(self):
        assert steps(f"{K} (animation a (move none (duration 2)))") == ("wait", 2)
        error(f"{K} (animation a (move none (to 1) (duration 2)))", "takes only a duration")

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
        src = f"{self.B} (animation a (defaults (ease 'ease-in')) {move})"
        assert steps(src)[4] == ("step", 1)

    @pytest.mark.parametrize("ease", ["'linear'", "(step 3)"])
    def test_an_ease_that_takes_values_other_than_0_and_1(self, ease):
        # (step 3) jumps to 1/3 and 2/3, which mean nothing for a bool.
        error(
            f"{self.B} (animation a (move on (to true) (duration 1) (ease {ease})))",
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
        move = "(move s (to 'right') (duration 1) (ease 'linear'))"
        error(
            f"{self.SIDE} (animation a {move})",
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
        assert s[2] == ("wait", 1)


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
        s = steps(f"{K} (animation a (defaults (duration 2) (ease 'linear')) (move k (to 1)))")
        assert s[3:] == (2, "linear")

    def test_on_at_once(self):
        s = steps(f"{K} (animation a (at-once (defaults (duration 3)) (move k (to 1))))")
        assert s[1][3] == 3

    def test_the_old_forms_are_gone(self):
        error(f"{K} (animation a (default-duration 2) (move k (to 1)))", "an animation holds moves")
