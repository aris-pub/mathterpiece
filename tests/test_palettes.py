"""Palettes (mtp-nua): (palette name (member color) …) declares named colors, read as
name.member. The author, 2026-11-05: a palette is a refinement of namespace, so every palette is a
namespace and is accepted where one is, and every member is a color; its members are written as a
name and a value only, and it holds colors only, never another palette."""

import re

from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.types import NAMESPACE, PALETTE, fits

BRAND = "(palette brand (ink '#1f2a44') (paper '#f6f1e7') (soft (mix ink paper 0.5)))"


def test_members_are_read_through_it():
    m = model(f"{BRAND} (scene s (circle c (fill brand.ink)))")
    e = m.get("c").attrs["fill"].expr
    assert m.objects[e.args[0]].name == "brand.ink"


def test_members_read_each_other_by_bare_name():
    m = model(f"{BRAND} (scene s (circle c (fill brand.soft)))")
    assert m.objects[m.names["brand.soft"]].value.bound


def test_its_type_is_palette_a_refinement_of_namespace():
    m = model(BRAND)
    assert m.get("brand").type == PALETTE
    assert fits(PALETTE, NAMESPACE) and not fits(NAMESPACE, PALETTE)


def test_it_fits_an_interface_as_a_namespace_does():
    model(f"(interface inky (color ink)) {BRAND} (func f ((inky p)) p.ink) (color v (f brand))")


def test_members_are_colors_only():
    error("(palette p (gap 0.4))", "expected color")
    error("(palette p (palette q (ink 'red')))", "a palette holds colors, not another palette")


def test_members_are_a_name_and_a_value():
    member = re.escape("a palette's member is (name color)")
    error("(palette p (color ink 'red'))", member)
    error("(palette p (ink))", member)


def test_two_members_of_the_same_name():
    error("(palette p (ink 'red') (ink 'blue'))", "'ink' is already declared")


def test_a_token_named_by_the_palette():
    d = doc(f"{BRAND} (scene s (circle c (fill brand.ink)))")
    assert errors(d) == []
    ink = d["objects"][d["names"]["brand.ink"]]
    assert ink["token"] is True


def test_imported(tmp_path):
    (tmp_path / "house.mtp").write_text(BRAND)
    src = "(import house brand) (scene s (circle c (fill brand.ink)))"
    path = tmp_path / "fig.mtp"
    path.write_text(src)
    compile_source(src, path=path)
