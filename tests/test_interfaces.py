"""Interfaces an author declares (mtp-ateh; type-system.md, section 6). The author, 2026-11-04:
(interface inky (color ink) (color paper)) is a constraint on attributes and their types; any
object with those attributes, of fitting types, satisfies it, shapes and namespaces alike. It may
list constraints, (interface spaced (real gap (>= 0))): an object fits only if its attribute is
guaranteed to meet them. A namespace is passed as an argument only through a parameter typed with
an interface it fits."""

import re

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import compile_source

PALETTE = "(interface inky (color ink) (color paper))"
DAY = "(namespace day (color ink '#1f2a44') (color paper '#f6f1e7') (real gap 0.4))"
NIGHT = "(namespace night (color ink '#e8e4d8') (color paper '#14161c'))"


class TestNamespaces:
    def test_a_function_takes_one(self):
        model(f"{PALETTE} {DAY} (func f ((inky p)) p.ink) (color v (f day))")

    def test_extra_members_are_allowed(self):
        model(f"(interface inky (color ink)) {DAY} (func f ((inky p)) p.ink) (color v (f day))")

    def test_a_missing_member(self):
        error(
            f"{PALETTE} (namespace n (color ink 'red')) (func f ((inky p)) p.ink) (color v (f n))",
            "n does not fit inky: it has no 'paper'",
        )

    def test_a_member_of_another_type(self):
        error(
            f"{PALETTE} (namespace n (real ink 1) (color paper 'red')) (func f ((inky p)) p.ink)"
            " (color v (f n))",
            "n does not fit inky: its ink is a real, not a color",
        )

    def test_a_nested_namespace(self):
        model(
            f"{PALETTE} (interface themed (inky colors))"
            " (namespace t (namespace colors (color ink 'red') (color paper 'white')))"
            " (func f ((themed x)) x.colors.ink) (color v (f t))"
        )

    def test_only_what_the_interface_lists_is_read(self):
        error(f"{PALETTE} {DAY} (func f ((inky p)) p.gap)", "an inky has no attribute 'gap'")

    def test_a_variable_holds_one(self):
        model(f"{PALETTE} {DAY} {NIGHT} (inky look day) (color v look.ink)")

    def test_an_if_picks_one(self):
        model(
            f"{PALETTE} {DAY} {NIGHT} (bool dark false) (inky look (if dark night day))"
            " (scene s (circle c (fill look.ink)))"
        )


class TestShapes:
    ROUND = "(interface round (real r (>= 0)))"

    def test_any_shape_with_the_attributes(self):
        model(
            f"{self.ROUND} (func area ((round o)) (* pi o.r o.r))"
            " (scene s (circle c (r 2)) (ring g (r 3)))"
            " (real a (area c)) (real b (area g))"
        )

    def test_a_shape_without_them(self):
        error(
            f"{self.ROUND} (func area ((round o)) (* pi o.r o.r)) (scene s (rect q))"
            " (real a (area q))",
            "does not fit round: it has no 'r'",
        )

    def test_a_namespace_and_a_shape_both_fit(self):
        model(
            f"{self.ROUND} (func area ((round o)) (* pi o.r o.r))"
            " (namespace n (real r 1 (>= 0))) (scene s (circle c))"
            " (real a (area n)) (real b (area c))"
        )


class TestConstraints:
    SPACED = "(interface spaced (real gap (>= 0)))"
    F = "(func f ((spaced x)) x.gap)"

    def test_a_member_that_meets_it(self):
        model(f"{self.SPACED} {self.F} (namespace n (real gap 0.4 (>= 0))) (real v (f n))")
        model(f"{self.SPACED} {self.F} (namespace n (real gap 2 (>= 1))) (real v (f n))")

    def test_a_member_not_guaranteed_to(self):
        error(
            f"{self.SPACED} {self.F} (namespace n (real gap 0.4)) (real v (f n))",
            re.escape("n does not fit spaced: its gap may break (>= 0)"),
        )

    def test_reading_one_through_the_interface_knows_the_range(self):
        # The interface promises gap >= 0, so it may be a circle's radius.
        model(
            f"{self.SPACED} (namespace n (real gap 1 (>= 0))) (spaced sp n)"
            " (scene s (circle c (r sp.gap)))"
        )


class TestDeclaring:
    def test_a_name_already_declared(self):
        error(f"{PALETTE} (real inky 1)", "'inky' is already declared")

    def test_members_need_a_type_and_a_name(self):
        lists = re.escape("an interface lists (T name constraint…)")
        error("(interface i (ink))", lists)
        error("(interface i (color ink 'red'))", lists)

    def test_two_members_of_the_same_name(self):
        error("(interface i (color ink) (real ink))", "'ink' is already declared")

    def test_imported(self, tmp_path):
        (tmp_path / "house.mtp").write_text(PALETTE + " " + DAY)
        src = "(import house inky day) (func f ((inky p)) p.ink) (color v (f day))"
        path = tmp_path / "fig.mtp"
        path.write_text(src)
        compile_source(src, path=path)


class TestMotifs:
    CARD = "(motif card ((inky look)) (rect r (fill look.paper) (stroke look.ink)))"

    def test_a_motif_takes_one(self):
        m = model(
            f"{PALETTE} {DAY} {NIGHT} {self.CARD}"
            " (scene s (card a (look day)) (card b (look night)))"
        )
        assert m.get("a.r").attrs["fill"].bound and m.get("b.r").attrs["fill"].bound

    def test_picked_by_an_if(self):
        model(
            f"{PALETTE} {DAY} {NIGHT} {self.CARD} (bool dark false)"
            " (scene s (card a (look (if dark night day))))"
        )

    def test_an_instance_must_be_given_one(self):
        error(f"{PALETTE} {DAY} {self.CARD} (scene s (card a))", "look needs a value")

    def test_one_that_does_not_fit(self):
        error(
            f"{PALETTE} {self.CARD} (namespace n (color ink 'red')) (scene s (card a (look n)))",
            "n does not fit inky: it has no 'paper'",
        )

    def test_only_what_the_interface_lists_is_read(self):
        error(
            f"{PALETTE} (motif card ((inky look)) (circle c (r look.gap)))",
            "an inky has no attribute 'gap'",
        )

    def test_a_built_in_interface_too(self):
        # Found while adding interfaces: no motif parameter typed with an interface worked, as
        # the motif's trial compile needed a default for it.
        model(
            "(motif tag ((positioned o)) (circle c (pos o.pos) (r 0.1)))"
            " (scene s (circle k (pos [1 2])) (tag t (o k)))"
        )


@pytest.mark.parametrize(
    "src",
    [
        f"{PALETTE} {DAY} {NIGHT} (bool dark false) (inky look (if dark night day))"
        " (scene s (circle c (fill look.ink)))",
        f"{PALETTE} {DAY} {NIGHT} (bool dark false)"
        " (motif card ((inky look)) (rect r (fill look.paper)))"
        " (scene s (card a (look day)) (card b (look (if dark night day))))",
        "(interface round (real r (>= 0))) (func area ((round o)) (* pi o.r o.r))"
        " (scene s (circle k)) (real a (area k))",
    ],
)
def test_the_compiled_file_passes_the_schema(src):
    assert errors(doc(src)) == []
