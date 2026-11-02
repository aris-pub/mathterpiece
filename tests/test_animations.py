"""Transitions, animations and buttons (docs/reference.md "Transitions and animations",
"Components" and "Writes and conditions"; docs/mtpc.md "Steps" and "Transitions")."""

import pytest

from mathterpiece.compiler import CompileError, compile_source


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def steps(src, name="a"):
    return model(src).get(name).data["steps"]


K = "(real k 0 (>= 0) (<= 10))"


class TestTransitions:
    def test_a_named_transition(self):
        m = model(
            f"{K} (transit up none (to 5) (duration 1)) (animation a (transit _ k (like up)))"
        )
        t = m.get("up")
        assert t.kind == "transition"
        assert t.attrs["to"].value == 5
        assert "from" not in t.attrs
        # (like up) makes the step a transit of its own, with up's arguments.
        move = m.get("a").data["steps"]
        assert (move[0], move[1], move[3:]) == ("move", (m.id("k"), None), (1, "linear"))
        assert m.objects[move[2]].attrs["to"].value == 5

    def test_an_inline_transition_comes_before_its_holder(self):
        m = model(f"{K} (animation a (transit _ k (to 5) (duration 1)))")
        (tid,) = [i for i, o in enumerate(m.objects) if o.kind == "transition"]
        assert tid == m.id("a") - 1

    def test_the_end_must_fit_what_it_moves(self):
        error(f"{K} (animation a (transit _ k (to 'x') (duration 1)))", "expected real")

    def test_a_string_end_becomes_a_color(self):
        m = model("(scene s (circle c)) (animation a (transit _ c.fill (to 'red') (duration 1)))")
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["to"].value == "#ff0000ff"

    def test_an_end_that_may_be_none(self):
        src = "(real|none e) (scene s (circle c))"
        error(f"{K} {src} (animation a (transit _ k (to e) (duration 1)))", "may be none")
        model(
            "(color|none e) (scene s (circle c))"
            "(animation a (transit _ c.fill (to e) (duration 1)))"
        )

    def test_eases_and_paths(self):
        m = model(
            f"{K} (func half ((real a) (real b) (real t)) (+ a (* t (- b a))))"
            "(animation a (transit _ k (to 5) (duration 1) (ease (step 4)) (path half)))"
        )
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["ease"].value == ("step", 4)
        assert t.attrs["path"].expr.op == "func"
        error(f"{K} (animation a (transit _ k (to 5) (duration 1) (ease 'wobbly')))", "ease")

    def test_a_negative_duration(self):
        error(f"{K} (animation a (transit _ k (to 5) (duration -1)))", "cannot be negative")


class TestSteps:
    def test_defaults_and_nesting(self):
        s = steps(
            f"{K} (real j 0) (animation a (default-duration 2) (default-ease 'ease-in')"
            " (transit _ k (to 5)) (transit _ none (duration 1))"
            " (at-once (default-duration 3) (transit _ j (to 1))"
            " (transit _ k (to 1) (duration 4))))"
        )
        assert s[0] == "in-order"
        assert s[1][3:] == (2, "ease-in")
        assert s[2] == ("wait", 1)
        assert s[3][0] == "at-once"
        assert s[3][1][3] == 3 and s[3][2][3] == 4

    def test_a_step_takes_a_transitions_items_directly(self):
        # reference.md "Transitions and animations": inside a step, the transition is implied.
        s = steps(f"{K} (animation a (transit _ k (from 1) (to 5) (duration 2) (ease 'ease-in')))")
        assert s[3:] == (2, "ease-in")

    def test_a_step_takes_a_named_transition(self):
        steps(
            f"{K} (transit slide none (to 5) (duration 1)) (animation a (transit _ k (like slide)))"
        )

    def test_an_animation_holds_only_transits_at_once_and_in_order(self):
        error(f"{K} (animation a (k (to 5) (duration 1)))", "holds transits, at-once and in-order")

    def test_a_transit_with_no_target_only_waits(self):
        assert steps(f"{K} (animation a (transit _ none (duration 2)))") == ("wait", 2)
        error(f"{K} (animation a (transit _ none (to 1) (duration 2)))", "takes only a duration")

    def test_a_named_transit_with_a_target_is_a_move(self):
        s = steps(f"{K} (transit grow k (to 5) (duration 1)) (animation a grow)")
        assert s[0] == "move" and s[3] == 1

    def test_like_copies_a_named_transit_under_its_own_arguments(self):
        src = f"{K} (transit slide none (to 5) (duration 1))"
        src += " (animation a (transit _ k (like slide) (duration 3)))"
        assert steps(src)[3] == 3

    def test_a_transition_needs_a_duration(self):
        error(f"{K} (animation a (transit _ k (to 5)))", "needs a duration")

    def test_what_can_be_moved(self):
        m = model(
            "(motif dot (real k 0) (circle c)) (scene s (dot d) (group g (circle a) (circle b)))"
            "(animation an (transit _ d.k (to 1) (duration 1))"
            " (transit _ g[1].r (to 2) (duration 1))"
            " (transit _ g.r (to 3) (duration 1))"
            " (transit _ d.c.pos (to [1 1]) (duration 1)))"
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
        error(f"{src} (animation a (transit _ k (to 1) (duration 1)))", message)

    def test_a_fixed_attribute(self):
        src = "(variant bar () (rect _ (width 1))) (scene s (bar b))"
        error(f"{src} (animation a (transit _ b.width (to 2) (duration 1)))", "fixed")


class TestButtons:
    def test_a_button(self):
        m = model(f"{K} (button b (animation (transit _ k (to 5) (duration 1))))")
        b = m.get("b")
        assert b.kind == "button"
        assert m.objects[b.data["animation"]].kind == "animation"
        assert b.attrs["label"].value == "b"
        assert b.access == "page"

    def test_a_named_animation(self):
        m = model(f"{K} (animation a (transit _ k (to 5) (duration 1))) (button b (animation a))")
        assert m.get("b").data["animation"] == m.id("a")

    def test_conditions_clamp_what_is_written(self):
        m = model(
            f"{K} (real lim 3) (button b (animation (transit _ k (to 5) (duration 1)))"
            " (<= k lim) (> 1 k))"
        )
        c = m.get("b").data["conditions"]
        assert [(x["target"], x["op"]) for x in c] == [
            ((m.id("k"), None), "<="),
            ((m.id("k"), None), "<"),
        ]
        assert (m.id("lim"), None) in c[0]["limit"].deps

    def test_a_condition_that_is_not_a_limit(self):
        src = f"{K} (real j) (button b (animation (transit _ k (to 5) (duration 1)))"
        error(f"{src} (> j 1))", "compares an attribute this writer writes")
        error(f"{src} (> k (* 2 k)))", "compares an attribute this writer writes")


class TestBoolMoves:
    # reference.md "Transitions and animations": a bool changes at the start of its move and
    # holds, unless its own ease is a step ease.
    B = "(bool on false)"

    def test_the_default_is_one_jump_at_the_start(self):
        s = steps(f"{self.B} (animation a (transit _ on (to true) (duration 1)))")
        assert s[4] == ("step", 1)

    def test_an_enclosing_default_ease_that_is_not_a_step_does_not_apply(self):
        move = "(transit _ on (to true) (duration 1))"
        src = f"{self.B} (animation a (default-ease 'ease-in') {move})"
        assert steps(src)[4] == ("step", 1)

    @pytest.mark.parametrize("ease", ["'linear'", "(step 3)"])
    def test_an_ease_that_takes_values_other_than_0_and_1(self, ease):
        # (step 3) jumps to 1/3 and 2/3, which mean nothing for a bool.
        error(
            f"{self.B} (animation a (transit _ on (to true) (duration 1) (ease {ease})))",
            "an ease for a bool takes only the values 0 and 1",
        )


class TestChoiceMoves:
    # A choice string moves like a bool: it changes at the start unless a discrete ease says
    # otherwise.
    SIDE = "(type side string (one-of 'left' 'right')) (side s 'left')"

    def test_the_default(self):
        assert steps(f"{self.SIDE} (animation a (transit _ s (to 'right') (duration 1)))")[4] == (
            "step",
            1,
        )

    def test_a_continuous_ease_is_an_error(self):
        move = "(transit _ s (to 'right') (duration 1) (ease 'linear'))"
        error(
            f"{self.SIDE} (animation a {move})",
            "an ease for a choice takes only the values 0 and 1",
        )


class TestStepEase:
    # reference.md: (step-ease p) is 0 before progress p and 1 from p on.
    B = "(bool on false)"

    def test_a_bool_may_take_it(self):
        move = "(transit _ on (to true) (duration 1) (ease (step-ease 0.5)))"
        assert steps(f"{self.B} (animation a {move})")[4] == ("step-ease", 0.5)

    def test_its_point_is_from_0_to_1_known_when_compiling(self):
        move = "(transit _ on (to true) (duration 1) (ease (step-ease 2)))"
        error(f"{self.B} (animation a {move})", r"2 breaks \(<= 1\)")


class TestStringMoves:
    # A string, like a bool or a choice, changes at the start of its move by default.
    def test_the_default(self):
        src = "(string s 'a') (animation a (transit _ s (to 'b') (duration 1)))"
        assert steps(src)[4] == ("step", 1)


class TestNamedAnimationsAsSteps:
    def test_a_named_animation_runs_its_steps_in_place(self):
        src = (
            f"{K} (real j 0) (animation one (transit _ k (to 5) (duration 1)))"
            "(animation a one (transit _ none (duration 1)) (transit _ j (to 2) (duration 1)))"
        )
        m = model(src)
        s = m.get("a").data["steps"]
        assert s[0] == "in-order"
        assert s[1] == m.get("one").data["steps"]
        assert s[2] == ("wait", 1)


class TestRepeatedListeners:
    def test_repeat_produces_listeners(self):
        src = (
            "(real k 0)"
            "(scene s (repeat 3 i (circle (name $'c{i}'))))"
            "(repeat 3 i (on-click (name $'c{i}')"
            " (animation (transit _ k (to i) (duration 0)))))"
        )
        m = model(src)
        clicks = [o for o in m.objects if o.kind == "on-click"]
        assert [o.data["shape"] for o in clicks] == [m.id(f"c{i}") for i in range(3)]


class TestFadePath:
    def test_fade_is_written_bare(self):
        m = model("(scene s (circle c)) (canvas v (transit _ none (duration 1) (path fade)) c)")
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["path"].value == "fade"
