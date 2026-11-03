"""Attributes by type (docs/type-system.md, section 8), and the stroke attributes: dash,
dash-offset, line-cap and line-join (docs/reference.md "The scene and shapes")."""

from helpers import bound, error, model, value

from mathterpiece.types import FONT, INT, REAL, ListT, Refine

UNIT = Refine(REAL, ((">=", 0), ("<=", 1)))


class TestNames:
    def test_a_named_object_has_its_name(self):
        assert value("(scene s (circle c)) (string n c.name)", "n") == "c"

    def test_an_anonymous_ones_name_is_none(self):
        assert value("(scene s (group g (circle_))) (string|none n g[0].name)", "n") is None


class TestValues:
    def test_complex_parts(self):
        assert value("(real r (. (+ 3 2i) re))", "r") == 3
        assert bound("(complex z) (real i z.im)", "i").type == REAL

    def test_color_channels(self):
        e = bound("(color ink '#ff000080') (real a ink.a)", "a")
        assert e.type == UNIT

    def test_lengths(self):
        assert value("(int n (. 'abc' length))", "n") == 3
        assert value("(list xs [1 2 3] (const)) (int n xs.length)", "n") == 3
        assert value("(list[real] xs [1 2] (length 2)) (int n xs.length)", "n") == 2
        assert bound("(list[real] xs [1 2]) (int n xs.length)", "n").type == INT


class TestTransitionsAndAnimations:
    def test_a_transitions_parts(self):
        src = "(real k) (transition t none (to 5) (duration 2))"
        src += " (animation a (move k (like t)) (move none (duration 1)))"
        assert value(f"{src} (real d t.duration)", "d") == 2
        assert value(f"{src} (real d a.duration)", "d") == 3

    def test_at_once_takes_the_longest(self):
        move = "(move k (to 1) (duration 2))"
        src = f"(real k) (animation a (at-once {move} (move none (duration 3))))"
        assert value(f"{src} (real d a.duration)", "d") == 3


class TestFonts:
    def test_a_font_variable(self):
        m = model("(font f (family 'Inter') (size 20))")
        f = m.get("f")
        assert f.value.type == FONT
        assert f.value.value == {"family": "Inter", "style": "normal", "weight": 400, "size": 20}

    def test_its_parts_are_read_while_drawing(self):
        # A font is a token: the page may restyle it, so it is never folded.
        assert bound("(font f (size 20)) (real s f.size)", "s").type == REAL

    def test_style_and_weight(self):
        error("(font f (style 'bold'))", "'bold' is not one of 'normal', 'italic', 'oblique'")
        error("(font f (weight 2000))", r"2000 breaks \(<= 1000\)")

    def test_text_and_readouts_take_a_font_variable(self):
        m = model("(font f (size 20)) (scene s (text t 'hi' (font f))) (readout r 'x' (font f))")
        assert (m.id("f"), None) in m.get("t").attrs["font"].deps
        error("(scene s (text t 'hi' (font 3)))", "a declared font variable")


def test_a_fonts_parts_are_known_when_compiling():
    # The .mtpc writes a font as a plain value (docs/mtpc.md, "Values").
    error("(real k 1) (font f (size k))", "a font's parts must be known when compiling")


class TestDash:
    # mtp-5of, the author 2026-11-03: (dash [lengths…] offset), the lengths in screen pixels like
    # stroke-width, the offset optional.
    def test_solid_by_default(self):
        a = model("(scene s (circle c))").get("c").attrs
        assert a["dash"].value == [] and a["dash-offset"].value == 0

    def test_lengths_and_offset(self):
        a = model("(scene s (line l (dash [4 2 1 2] 3)))").get("l").attrs
        assert a["dash"].value == [4, 2, 1, 2] and a["dash-offset"].value == 3

    def test_the_offset_is_optional(self):
        a = model("(scene s (line l (dash [4 2])))").get("l").attrs
        assert a["dash"].value == [4, 2] and a["dash-offset"].value == 0

    def test_the_offset_may_follow_a_variable(self):
        m = model("(real phase 0) (scene s (line l (dash [4 2] phase)))")
        assert m.get("l").attrs["dash-offset"].bound

    def test_lengths_are_not_negative(self):
        error("(scene s (line l (dash [4 -2])))", "breaks")

    def test_lengths_come_in_a_list(self):
        error("(scene s (line l (dash 4 2)))", "expected list")
        error("(scene s (line l (dash [4 2] 1 2)))", "a list of lengths and an offset")
        error("(scene s (line l (dash-offset 1)))", "the offset is dash's second argument")

    def test_a_container_gives_it_to_its_members(self):
        m = model("(scene s (group g (defaults (dash [4 2] 1)) (line a) (line b (dash [1 1]))))")
        a, b = m.get("a").attrs, m.get("b").attrs
        assert a["dash"].value == [4, 2] and a["dash-offset"].value == 1
        assert b["dash"].value == [1, 1] and b["dash-offset"].value == 0

    def test_a_text_takes_none_from_a_container(self):
        m = model("(scene s (group g (defaults (dash [4 2])) (text t 'hi')))")
        assert m.get("t").attrs["dash"].value == []

    def test_given_twice(self):
        error("(scene s (line l (dash [4 2]) (dash [1 1])))", "given twice")


class TestLineEnds:
    # mtp-9d5, the author 2026-11-03: line-cap and line-join, with SVG's values.
    def test_defaults_are_svgs(self):
        a = model("(scene s (line l))").get("l").attrs
        assert a["line-cap"].value == "butt" and a["line-join"].value == "miter"

    def test_given(self):
        a = model("(scene s (triangle t (line-cap 'round') (line-join 'bevel')))").get("t").attrs
        assert a["line-cap"].value == "round" and a["line-join"].value == "bevel"

    def test_only_svgs_values(self):
        error("(scene s (line l (line-cap 'pointy')))", "not one of")
        error("(scene s (line l (line-join 'square')))", "not one of")

    def test_a_container_gives_them_to_its_members(self):
        m = model("(scene s (group g (defaults (line-cap 'round')) (line a)))")
        assert m.get("a").attrs["line-cap"].value == "round"


class TestDashOffset:
    # The author, 2026-11-03: the offset is an attribute of its own, dash-offset, which a figure
    # may read and an animation may move.
    def test_read(self):
        m = model("(scene s (line l (dash [4 2] 3)) (real v l.dash-offset))")
        e = m.get("v").value.expr
        assert e.op == "read" and e.type == REAL

    def test_moved_by_an_animation(self):
        m = model(
            "(scene s (line l (dash [4 2]))) (animation a (move l.dash-offset (to 6) (duration 1)))"
        )
        assert m.get("a").data["steps"][1] == (m.id("l"), "dash-offset")

    def test_a_containers_offset_is_every_members(self):
        m = model(
            "(scene s (group g (defaults (dash [4 2] 1)) (line a) (line b)) (list v g.dash-offset))"
        )
        assert m.get("v").value.expr.type.base == ListT(REAL)
