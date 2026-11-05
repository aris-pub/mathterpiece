"""A font's part may read the same part of another font (the author, 2026-11-05): house.mtp
builds its role fonts from the standard library's families, (font variable (family
fonts.serif.family) (style 'italic') (size 18)). The part takes the other font's value, and the
page's CSS for it falls back to the other font's CSS variable, so restyling the family restyles
the role too."""

from helpers import doc, error, model
from mtpc_check import errors

SERIF = "(font serif (family 'Georgia, serif'))"


def test_a_part_read_from_another_font():
    m = model(f"{SERIF} (font variable (family serif.family) (style 'italic') (size 18))")
    v = m.get("variable").value.value
    assert (v["family"], v["style"], v["size"]) == ("Georgia, serif", "italic", 18)
    assert m.get("variable").data["links"] == {"family": m.names["serif"]}


def test_any_part():
    m = model(
        "(font heavy (family 'Arial') (weight 700)) (font label (family heavy.family)"
        " (weight heavy.weight) (size 12))"
    )
    v = m.get("label").value.value
    assert (v["family"], v["weight"]) == ("Arial", 700)
    assert set(m.get("label").data["links"]) == {"family", "weight"}


def test_only_the_same_part():
    error(f"{SERIF} (font f (style serif.family))", "may be none|expected")


def test_anything_else_still_must_be_known():
    error("(bool b true) (font f (family (if b 'Arial' 'Georgia')))", "must be known when")


def test_the_compiled_file():
    d = doc(f"{SERIF} (font variable (family serif.family) (style 'italic'))")
    assert errors(d) == []
    assert d["objects"][d["names"]["variable"]]["links"] == {"family": d["names"]["serif"]}
