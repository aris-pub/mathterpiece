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
        m = model(f"{K} (transition up (to 5) (duration 1)) (animation a (k up))")
        t = m.get("up")
        assert t.kind == "transition"
        assert t.attrs["to"].value == 5
        assert "from" not in t.attrs
        assert m.get("a").data["steps"] == ("move", (m.id("k"), None), m.id("up"), 1, "linear")

    def test_an_inline_transition_comes_before_its_holder(self):
        m = model(f"{K} (animation a (k (transition (to 5) (duration 1))))")
        (tid,) = [i for i, o in enumerate(m.objects) if o.kind == "transition"]
        assert tid == m.id("a") - 1

    def test_the_end_must_fit_the_place(self):
        error(f"{K} (animation a (k (transition (to 'x') (duration 1))))", "expected real")

    def test_a_string_end_becomes_a_color(self):
        m = model(
            "(scene s (circle c)) (animation a (c.fill (transition (to 'red') (duration 1))))"
        )
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["to"].value == "#ff0000ff"

    def test_an_end_that_may_be_none(self):
        src = "(real|none e) (scene s (circle c))"
        error(f"{K} {src} (animation a (k (transition (to e) (duration 1))))", "may be none")
        model(
            "(color|none e) (scene s (circle c))"
            "(animation a (c.fill (transition (to e) (duration 1))))"
        )

    def test_eases_and_paths(self):
        m = model(
            f"{K} (func half ((real a) (real b) (real t)) (+ a (* t (- b a))))"
            "(animation a (k (transition (to 5) (duration 1) (ease (step 4)) (path half))))"
        )
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["ease"].value == ("step", 4)
        assert t.attrs["path"].expr.op == "func"
        error(f"{K} (animation a (k (transition (to 5) (duration 1) (ease 'wobbly'))))", "ease")

    def test_a_negative_duration(self):
        error(f"{K} (animation a (k (transition (to 5) (duration -1))))", "cannot be negative")


class TestSteps:
    def test_defaults_and_nesting(self):
        s = steps(
            f"{K} (real j 0) (animation a (default-duration 2) (default-ease 'ease-in')"
            " (k (transition (to 5))) (wait 1)"
            " (at-once (default-duration 3) (j (transition (to 1)))"
            " (k (transition (to 1) (duration 4)))))"
        )
        assert s[0] == "in-order"
        assert s[1][3:] == (2, "ease-in")
        assert s[2] == ("wait", 1)
        assert s[3][0] == "at-once"
        assert s[3][1][3] == 3 and s[3][2][3] == 4

    def test_a_transition_needs_a_duration(self):
        error(f"{K} (animation a (k (transition (to 5))))", "needs a duration")

    def test_places_that_can_be_moved(self):
        m = model(
            "(motif dot (real k 0) (circle c)) (scene s (dot d) (group g (circle a) (circle b)))"
            "(animation an (d.k (transition (to 1) (duration 1)))"
            " (g[1].r (transition (to 2) (duration 1)))"
            " (g.r (transition (to 3) (duration 1)))"
            " (d.c.pos (transition (to [1 1]) (duration 1))))"
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
    def test_places_that_cannot(self, src, message):
        error(f"{src} (animation a (k (transition (to 1) (duration 1))))", message)

    def test_a_fixed_attribute(self):
        src = "(variant bar () (rect _ (width 1))) (scene s (bar b))"
        error(f"{src} (animation a (b.width (transition (to 2) (duration 1))))", "fixed")


class TestButtons:
    def test_a_button(self):
        m = model(f"{K} (button b (animation (k (transition (to 5) (duration 1)))))")
        b = m.get("b")
        assert b.kind == "button"
        assert m.objects[b.data["animation"]].kind == "animation"
        assert b.attrs["label"].value == "b"
        assert b.access == "page"

    def test_a_named_animation(self):
        m = model(
            f"{K} (animation a (k (transition (to 5) (duration 1)))) (button b (animation a))"
        )
        assert m.get("b").data["animation"] == m.id("a")

    def test_conditions_clamp_the_written_place(self):
        m = model(
            f"{K} (real lim 3) (button b (animation (k (transition (to 5) (duration 1))))"
            " (<= k lim) (> 1 k))"
        )
        c = m.get("b").data["conditions"]
        assert [(x["place"], x["op"]) for x in c] == [
            ((m.id("k"), None), "<="),
            ((m.id("k"), None), "<"),
        ]
        assert (m.id("lim"), None) in c[0]["limit"].deps

    def test_a_condition_that_is_not_a_limit(self):
        src = f"{K} (real j) (button b (animation (k (transition (to 5) (duration 1))))"
        error(f"{src} (> j 1))", "compares a place this writer writes")
        error(f"{src} (> k (* 2 k)))", "compares a place this writer writes")
