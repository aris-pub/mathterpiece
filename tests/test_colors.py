import pytest
from helpers import with_scene

from mathterpiece.colors import parse_color
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Bound, Color, Free, State
from mathterpiece.parse import parse


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


class TestParse:
    @pytest.mark.parametrize(
        "text, rgba",
        [
            ("#1f2a44", "#1f2a44ff"),
            ("#1F2A44", "#1f2a44ff"),
            ("#1f2a4480", "#1f2a4480"),
            ("#f80", "#ff8800ff"),
            ("#f808", "#ff880088"),
            ("gold", "#ffd700ff"),
            ("Gold", "#ffd700ff"),
            ("transparent", "#00000000"),
        ],
    )
    def test_reads(self, text, rgba):
        assert parse_color(text) == rgba

    @pytest.mark.parametrize("text", ["", "#12", "#gggggg", "golden", "rgb(1, 2, 3)", "none"])
    def test_rejects(self, text):
        assert parse_color(text) is None


class TestFill:
    def test_known_string_is_checked_and_written_as_rgba(self):
        assert scene("(circle 'c' (fill 'gold'))")["c"].fill == Free("#ffd700ff")

    def test_none_stays(self):
        assert scene("(circle 'c' (fill 'none'))")["c"].fill == Free("none")

    def test_default(self):
        assert scene("(circle 'c')")["c"].fill == Free("#000000ff")

    def test_const(self):
        assert scene("(const 'ink' '#1f2a44') (circle 'c' (stroke ink))")["c"].stroke == Free(
            "#1f2a44ff"
        )

    def test_misspelled(self):
        error("(circle 'c' (fill 'golden'))", match="'golden' is not a color")

    def test_string_computed_while_drawing(self):
        m = scene("(real 'k') (circle 'c' (fill (if (> k 0) 'red' 'blue')))")
        assert isinstance(m["c"].fill, Bound)

    def test_not_a_string(self):
        error("(circle 'c' (fill 3))", match="color")


class TestColorTokens:
    def test_declares(self):
        m = scene("(color 'ink' '#1f2a44') (circle 'c' (fill ink))")
        assert isinstance(m["ink"], Color)
        assert m["ink"].value == Free("#1f2a44ff")
        assert isinstance(m["c"].fill, Bound)

    def test_misspelled(self):
        error("(color 'ink' 'inky')", match="'inky' is not a color")

    def test_compares_with_strings(self):
        m = scene("(color 'ink' '#1f2a44') (state 's' (= ink '#d62828'))")
        state = m["s"]
        assert isinstance(state, State) and len(state.conditions) == 1

    def test_shows_in_text(self):
        m = scene("(color 'ink' '#1f2a44') (text 't' $'ink is {ink}')")
        assert isinstance(m["t"].value, Bound)

    def test_not_a_string(self):
        error("(color 'ink' '#1f2a44') (text 't' ink)", match="expected str, got color")
        error("(color 'ink' '#1f2a44') (text 't' (if (> 1 0) ink 'a'))")

    def test_a_control_can_write_it(self):
        m = scene(
            "(color 'ink' '#1f2a44')"
            " (button 'b' (animation (ink (transition (to 'red') (duration 1)))))"
        )
        assert m["b"].animation.body.targets == ((m["ink"], "value"),)


class TestExport:
    def test_writes_colors(self):
        doc = to_json(scene("(color 'ink' '#1f2a44') (circle 'c' (fill ink) (stroke 'gold'))"))
        assert doc["colors"] == "rgba"
        ink = doc["objects"][doc["names"]["ink"]]
        assert ink["kind"] == "color"
        assert ink["attrs"] == {"value": "#1f2a44ff"}
        c = doc["objects"][doc["names"]["c"]]["attrs"]
        assert c["fill"] == ["read", doc["names"]["ink"], "value"]
        assert c["stroke"] == "#ffd700ff"


class TestComparisons:
    def test_two_strings_compare_as_strings(self):
        fill = scene("(circle 'c' (fill (if (= 'red' '#f00') 'blue' 'green')))")["c"].fill
        assert fill == Free("#008000ff")

    def test_a_token_compares_as_a_color(self):
        doc = to_json(scene("(color 'ink' '#1f2a44') (state 's' (= ink 'red'))"))
        ink = doc["names"]["ink"]
        s = doc["objects"][doc["names"]["s"]]
        assert s["conditions"] == [["color=", ["read", ink, "value"], "red"]]

    def test_fill_compares_as_a_color(self):
        doc = to_json(scene("(circle 'c') (state 's' (!= c.fill 'teal'))"))
        c = doc["names"]["c"]
        s = doc["objects"][doc["names"]["s"]]
        assert s["conditions"] == [["color!=", ["read", c, "fill"], "teal"]]

    def test_a_string_compared_with_a_color_must_be_one(self):
        error("(color 'ink' '#1f2a44') (state 's' (= ink 'inky'))", match="'inky' is not a color")


class TestMix:
    @pytest.mark.parametrize(
        "expr, color",
        [
            ("(mix 'black' 'white' 0.5)", "#808080ff"),
            ("(mix 'red' 'blue' 0)", "#ff0000ff"),
            ("(mix 'red' 'blue' 1)", "#0000ffff"),
            ("(lighten 'black' 0.25)", "#404040ff"),
            ("(darken 'white' 0.25)", "#bfbfbfff"),
            ("(mix 'none' 'red' 0.5)", "#ff000080"),
            ("(mix '#ff000000' '#0000ffff' 0.5)", "#0000ff80"),
        ],
    )
    def test_known_colors_are_mixed_now(self, expr, color):
        assert scene(f"(circle 'c' (fill {expr}))")["c"].fill == Free(color)

    def test_a_token_is_mixed_when_drawn(self):
        doc = to_json(scene("(color 'ink' '#1f2a44') (circle 'c' (fill (lighten ink 0.3)))"))
        c = doc["objects"][doc["names"]["c"]]["attrs"]
        assert c["fill"] == ["call", "lighten", ["read", doc["names"]["ink"], "value"], 0.3]

    def test_known_strings_are_written_as_rgba(self):
        doc = to_json(scene("(color 'ink' '#1f2a44') (circle 'c' (fill (mix ink 'white' 0.5)))"))
        c = doc["objects"][doc["names"]["c"]]["attrs"]
        assert c["fill"][3] == "#ffffffff"

    def test_compares_as_a_color(self):
        m = scene("(color 'ink' '#1f2a44') (state 's' (= (lighten ink 0.1) 'red'))")
        assert m["s"] is not None

    @pytest.mark.parametrize(
        "expr, match",
        [
            ("(mix 'red' 'blue' 1.5)", "between 0 and 1"),
            ("(lighten 'red' -0.1)", "between 0 and 1"),
            ("(mix 'red' 'bleu' 0.5)", "'bleu' is not a color"),
            ("(mix 'red' 3 0.5)", "no form of mix"),
            ("(lighten 'red')", "no form of lighten"),
        ],
    )
    def test_invalid(self, expr, match):
        error(f"(circle 'c' (fill {expr}))", match=match)


class TestBackground:
    def compile(self, src):
        return compile_model(parse(src))

    def test_default_is_none(self):
        assert self.compile("(scene 'w' (circle 'c'))")["w"].background == Free("none")

    def test_known_color(self):
        assert self.compile("(scene 'w' (background 'linen') (circle 'c'))")[
            "w"
        ].background == Free("#faf0e6ff")

    def test_checked_and_written_as_rgba(self):
        m = self.compile("(scene 'w' (background 'ivory') (circle 'c'))")
        assert m["w"].background == Free("#fffff0ff")

    def test_token(self):
        m = self.compile("(color 'paper' '#f7f3ea') (scene 'w' (background paper) (circle 'c'))")
        assert isinstance(m["w"].background, Bound)

    def test_cannot_read_its_members(self):
        with pytest.raises(CompileError, match="undefined name 'c'"):
            self.compile("(scene 'w' (background (if (> c.r 1) 'black' 'white')) (circle 'c'))")

    def test_reads_values_defined_before(self):
        m = self.compile("(real 'k' 1) (scene 'w' (background (if (> k 0) 'black' 'white')))")
        assert isinstance(m["w"].background, Bound)

    def test_a_state_can_move_it(self):
        m = self.compile(
            "(scene 'w' (background 'white') (circle 'c'))"
            " (button 'b' (animation (w.background (transition (to 'black') (duration 1)))))"
        )
        assert m["b"].animation.body.targets[0][1] == "background"

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(scene 'w' (background 'paperish') (circle 'c'))", "not a color"),
            ("(scene 'w' (circle 'c') (background 'white'))", "before the members"),
            ("(scene 'w' (background 'white') (background 'black'))", "twice"),
        ],
    )
    def test_invalid(self, src, match):
        with pytest.raises(CompileError, match=match):
            self.compile(src)

    def test_export(self):
        doc = to_json(self.compile("(scene 'w' (background 'white') (circle 'c'))"))
        assert doc["objects"][doc["names"]["w"]]["attrs"]["background"] == "#ffffffff"


def test_a_bound_background_cannot_be_written():
    src = "(color 'paper' '#f7f3ea') (scene 'plane' (background paper) (circle 'c'))"
    with pytest.raises(CompileError, match="'plane.background' is computed"):
        compile_model(
            parse(
                f"{src} (button 'b'"
                " (animation (plane.background (transition (to 'black') (duration 1)))))"
            )
        )
