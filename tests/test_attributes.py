"""Attributes by type (docs/type-system.md, section 8)."""

from helpers import bound, error, model, value

from mathterpiece.types import FONT, INT, REAL, Refine

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
