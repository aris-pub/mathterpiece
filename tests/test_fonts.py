import pytest
from helpers import with_scene

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Bound, Font, Free, Readout, Text

LABEL = "(font 'label' (family 'Georgia, serif') (style 'italic') (weight 600) (size 0.6))"


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


class TestFontToken:
    def test_declares(self):
        f = scene(LABEL)["label"]
        assert isinstance(f, Font)
        assert (f.family, f.style, f.weight, f.size) == (
            Free("Georgia, serif"),
            Free("italic"),
            Free(600.0),
            Free(0.6),
        )

    def test_defaults(self):
        f = scene("(font 'plain')")["plain"]
        assert (f.family, f.style, f.weight, f.size) == (
            Free(""),
            Free("normal"),
            Free(400.0),
            Free(1.0),
        )

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(font 'f' (style 'slanted'))", "style is 'normal', 'italic' or 'oblique'"),
            ("(font 'f' (weight 'bold'))", "expected real"),
            ("(font 'f' (weight 1200))", "weight is between 1 and 1000"),
            ("(scene 's' (font 'f'))", "goes outside the scene"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)

    def test_a_control_can_write_a_part(self):
        m = scene(
            f"{LABEL} (slider 's' (animation (label.weight (transition (from 100) (to 900)))))"
        )
        assert m["s"].animation.body.targets[0][1] == "weight"


class TestTextWithAFont:
    def test_takes_every_part(self):
        t = scene(f"{LABEL} (text 't' 'x' (font label))")["t"]
        assert isinstance(t, Text)
        for part in (t.font_family, t.font_style, t.font_weight, t.font_size):
            assert isinstance(part, Bound)

    def test_may_set_one_part_itself(self):
        t = scene(f"{LABEL} (text 't' 'x' (font label) (font-style 'normal'))")["t"]
        assert t.font_style == Free("normal")
        assert isinstance(t.font_family, Bound)

    def test_without_a_font(self):
        t = scene("(text 't' 'x')")["t"]
        assert (t.font_family, t.font_style, t.font_weight, t.font_size) == (
            Free(""),
            Free("normal"),
            Free(400.0),
            Free(1.0),
        )

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(text 't' 'x' (font nope))", "nope"),
            ("(real 'k') (text 't' 'x' (font k))", "'k' is not a font"),
            (f"{LABEL} (text 't' 'x' (font label) (font label))", "twice"),
            (f"{LABEL} (circle 'c' (font label))", "unexpected|no attribute"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestReadoutWithAFont:
    def test_takes_family_style_and_weight(self):
        r = scene(f"{LABEL} (readout 'r' 'x' (font label))")["r"]
        assert isinstance(r, Readout)
        for part in (r.font_family, r.font_style, r.font_weight):
            assert isinstance(part, Bound)
        assert not hasattr(r, "font_size")


class TestExport:
    def test_writes_fonts(self):
        doc = to_json(scene(f"{LABEL} (text 't' 'x' (font label))"))
        f, t = doc["names"]["label"], doc["names"]["t"]
        assert doc["objects"][f]["kind"] == "font"
        assert doc["objects"][f]["attrs"] == {
            "family": "Georgia, serif",
            "style": "italic",
            "weight": 600.0,
            "size": 0.6,
        }
        attrs = doc["objects"][t]["attrs"]
        assert attrs["font-family"] == ["read", f, "family"]
        assert attrs["font-size"] == ["read", f, "size"]


class TestAlignment:
    def test_defaults(self):
        t = scene("(text 't' 'x')")["t"]
        assert (t.halign, t.valign) == (Free("start"), Free("bottom"))

    def test_given(self):
        t = scene("(text 't' 'x' (halign 'middle') (valign 'top'))")["t"]
        assert (t.halign, t.valign) == (Free("middle"), Free("top"))

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(text 't' 'x' (halign 'center'))", "halign is 'start', 'middle' or 'end'"),
            ("(text 't' 'x' (valign 'baseline'))", "valign is 'top', 'middle' or 'bottom'"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)

    def test_export(self):
        doc = to_json(scene("(text 't' 'x' (halign 'end'))"))
        attrs = doc["objects"][doc["names"]["t"]]["attrs"]
        assert (attrs["halign"], attrs["valign"]) == ("end", "bottom")
