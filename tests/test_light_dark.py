"""Colors for light and dark pages (mtp-m34w.1; docs/reference.md, "Colors"). The author,
2026-11-08: (light-dark light dark) is a color, usable wherever one is, as CSS names it. A color
with no dark value is the same in both modes. A color computed from light-dark colors, by mix,
lighten, darken or a colormap, is worked out for each mode on its own. The value is written
as the CSS that picks between the two, light-dark(#rrggbbaa, #rrggbbaa)."""

import json

from helpers import doc, error, model, typ, value
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.mtpc import write
from mathterpiece.types import COLOR

NAVY_CREAM = "light-dark(#1f2a44ff, #e8e4d8ff)"


class TestTheFunction:
    def test_it_is_a_color(self):
        assert typ("(bool b true) (color v (light-dark (if b 'red' 'blue') 'white'))") == COLOR

    def test_known_values_fold_to_the_css_that_picks_one(self):
        assert value("(color v (light-dark '#1f2a44' '#e8e4d8'))") == NAVY_CREAM

    def test_names_and_short_forms_are_read_as_any_color(self):
        assert value("(color v (light-dark 'white' '#000'))") == "light-dark(#ffffffff, #000000ff)"

    def test_the_same_color_twice_is_that_color(self):
        assert value("(color v (light-dark 'red' '#ff0000'))") == "#ff0000ff"

    def test_a_light_dark_inside_one_gives_its_own_mode(self):
        inner = "(light-dark '#111111' '#222222')"
        got = value(f"(color v (light-dark {inner} (light-dark '#333333' '#444444')))")
        assert got == "light-dark(#111111ff, #444444ff)"

    def test_it_takes_colors_only(self):
        error("(color v (light-dark 1 '#fff'))", "expected color")
        error("(string s 'red') (color v (light-dark s '#fff'))", "only a literal string")

    def test_where_a_color_goes(self):
        m = model(
            "(palette p (ink (light-dark '#1f2a44' '#e8e4d8')))"
            "(colormap heat [(light-dark '#000000' '#ffffff') '#ff0000'])"
            "(scene s (group g (defaults (stroke (light-dark '#999999' '#5a5f6b')))"
            " (circle c (fill (light-dark '#999999' '#5a5f6b'))) (circle d)))"
        )
        assert m.get("p.ink").value.value == NAVY_CREAM
        assert m.get("c").attrs["fill"].value == "light-dark(#999999ff, #5a5f6bff)"
        assert m.get("d").attrs["stroke"].value == "light-dark(#999999ff, #5a5f6bff)"

    def test_read_while_drawing(self):
        m = model(
            "(bool b true) (scene s (circle c (fill (light-dark (if b 'red' 'blue') '#ffffff'))))"
        )
        assert m.get("c").attrs["fill"].bound


class TestColorsComputedFromThem:
    def test_mix_of_two_works_out_each_mode(self):
        got = value(
            "(color v (mix (light-dark '#000000' '#ffffff') (light-dark '#ffffff' '#000000') 0.25))"
        )
        light = value("(color v (mix '#000000' '#ffffff' 0.25))")
        dark = value("(color v (mix '#ffffff' '#000000' 0.25))")
        assert got == f"light-dark({light}, {dark})"

    def test_mix_with_a_plain_color_mixes_it_into_both(self):
        got = value("(color v (mix (light-dark '#000000' '#ffffff') '#ff0000' 0.5))")
        light = value("(color v (mix '#000000' '#ff0000' 0.5))")
        dark = value("(color v (mix '#ffffff' '#ff0000' 0.5))")
        assert got == f"light-dark({light}, {dark})"

    def test_lighten_and_darken(self):
        ld = "(light-dark '#000000' '#808080')"
        assert value(f"(color v (lighten {ld} 0.5))") == "light-dark(#808080ff, #c0c0c0ff)"
        assert value(f"(color v (darken {ld} 0.5))") == "light-dark(#000000ff, #404040ff)"

    def test_a_mix_that_ends_the_same_in_both_is_one_color(self):
        got = value("(color v (mix (light-dark '#000000' '#ffffff') '#ff0000' 1))")
        assert got == "#ff0000ff"

    def test_a_colormap(self):
        src = "(colormap heat [(light-dark '#000000' '#ffffff') '#ff0000'])"
        got = value(f"{src} (color v (heat 0.5))")
        light = value("(color v (mix '#000000' '#ff0000' 0.5))")
        dark = value("(color v (mix '#ffffff' '#ff0000' 0.5))")
        assert got == f"light-dark({light}, {dark})"


class TestReadingOne:
    def test_equal_when_both_modes_are(self):
        ld = "(light-dark '#000000' '#ffffff')"
        assert value(f"(bool v (= {ld} (light-dark 'black' 'white')))") is True
        assert value(f"(bool v (= {ld} 'black'))") is False
        assert value("(bool v (= (light-dark 'red' 'red') 'red'))") is True

    def test_as_text_it_is_its_css(self):
        got = value("(string v (let ((c (light-dark '#1f2a44' '#e8e4d8'))) $'{c}'))")
        assert got == NAVY_CREAM

    def test_its_channels_are_the_light_colors(self):
        assert value("(real v (let ((c (light-dark '#ff0000' '#0000ff'))) c.r))") == 1
        assert value("(real v (let ((c (light-dark '#ff0000' '#0000ff'))) c.b))") == 0


class TestTheCompiledModel:
    SRC = (
        "(color ink (light-dark '#1f2a44' '#e8e4d8'))"
        "(bool b true)"
        "(scene s (circle c (fill (light-dark (if b 'red' 'blue') '#ffffff'))))"
    )

    def test_a_token_holds_the_css_as_its_value(self):
        d = doc(self.SRC)
        ink = d["objects"][d["names"]["ink"]]
        assert ink["value"]["free"] == NAVY_CREAM

    def test_a_call_while_drawing_is_a_builtin(self):
        d = doc(self.SRC)
        fill = d["objects"][d["names"]["c"]]["attrs"]["fill"]
        assert fill["bound"][0:3] == ["builtin", "color", "light-dark"]

    def test_it_meets_the_schema(self):
        assert errors(json.loads(write(compile_source(self.SRC)))) == []
