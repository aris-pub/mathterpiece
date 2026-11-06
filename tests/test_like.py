"""(like x) on declarations (mtp-61g). The author, 2026-11-06: (like x) copies the arguments x
was written with, compiled again in the new declaration, as on transitions: the copy follows
what x reads and has its own free values. Same kind only, one (like …) at most; shapes, motif
and variant instances and fonts take it, containers do not."""

import pytest
from helpers import error, model


def attrs(src, name):
    return model(src).get(name).attrs


class TestShapes:
    def test_the_arguments_x_was_written_with(self):
        a = attrs("(scene s (circle c1 (r 2) (fill 'blue')) (circle c2 (like c1)))", "c2")
        assert (a["r"].value, a["fill"].value) == (2, "#0000ffff")

    def test_its_own_arguments_win(self):
        a = attrs(
            "(scene s (circle c1 (r 2) (fill 'blue')) (circle c2 (like c1) (fill 'red')))", "c2"
        )
        assert (a["r"].value, a["fill"].value) == (2, "#ff0000ff")

    def test_it_follows_what_x_reads(self):
        m = model("(real k 2 (>= 0)) (scene s (circle c1 (r k)) (circle c2 (like c1)))")
        assert m.get("c2").attrs["r"].deps == {(m.id("k"), None)}

    def test_it_has_its_own_free_values(self):
        # A drag on c1 does not reach c2: c2's position is its own.
        m = model("(scene s (circle c1 (pos [1 2])) (circle c2 (like c1)))")
        assert not m.get("c2").attrs["x"].bound and m.get("c2").attrs["x"].value == 1

    def test_a_coordinate_beside_a_copied_position(self):
        a = attrs("(scene s (circle c1 (pos [1 2])) (circle c2 (like c1) (x 5)))", "c2")
        assert (a["x"].value, a["y"].value) == (5, 2)

    def test_a_text_takes_its_value_unless_it_gives_one(self):
        src = (
            "(scene s (text t1 'hi' (halign 'middle')) (text t2 (like t1))"
            " (text t3 'yo' (like t1)))"
        )
        assert attrs(src, "t2")["value"].value == "hi"
        assert attrs(src, "t3")["value"].value == "yo"
        assert attrs(src, "t3")["halign"].value == "middle"


class TestInstancesAndFonts:
    def test_a_motif_instance(self):
        m = model(
            "(motif dot ((real r 1 (>= 0))) (circle c (r r))) (scene s (dot d1 (r 3) (pos [1 1])"
            " (defaults (fill 'red'))) (dot d2 (like d1) (pos [0 0])))"
        )
        d2 = m.get("d2")
        assert (d2.attrs["r"].value, d2.attrs["x"].value) == (3, 0)
        assert m.objects[d2.members[0]].attrs["fill"].value == "#ff0000ff"

    def test_a_variant_instance(self):
        a = attrs(
            "(variant big ((real k 2 (>= 0))) (circle c (r (* k 2))))"
            " (scene s (big b1 (k 3) (fill 'red')) (big b2 (like b1) (k 4)))",
            "b2",
        )
        assert (a["k"].value, a["fill"].value) == (4, "#ff0000ff")

    def test_a_font(self):
        m = model("(font heading (size 20) (weight 600)) (font small (like heading) (size 12))")
        assert m.get("small").value.value == {
            "family": None,
            "style": "normal",
            "weight": 600,
            "size": 12,
        }


@pytest.mark.parametrize(
    "src, msg",
    [
        ("(scene s (circle c1) (rect r2 (like c1)))", "like takes the name of a rect"),
        ("(scene s (circle c1) (circle c2 (like c1) (like c1)))", "'like' is given twice"),
        ("(scene s (group g (circle a)) (group h (like g)))", "a container takes no"),
        ("(scene s (circle c2 (like c1)) (circle c1))", "unknown name 'c1'"),
        ("(font f (size 9)) (font g (like nope))", "unknown name"),
    ],
)
def test_errors(src, msg):
    error(src, msg)


@pytest.mark.parametrize(
    "src",
    [
        "(scene s (circle c1 (r 1)) (circle c2 (fill 'red') (like c1)))",
        "(motif dot ((real r 1 (>= 0))) (circle c (r r)))"
        " (scene s (dot d1) (dot d2 (pos [0 0]) (like d1)))",
        "(variant big ((real k 2 (>= 0))) (circle c (r (* k 2))))"
        " (scene s (big b1) (big b2 (k 4) (like b1)))",
        "(font h (size 20)) (font f (size 12) (like h))",
        "(real k 0) (transition up none (to 5) (duration 1))"
        " (animation a (move k (duration 2) (like up)))",
    ],
)
def test_like_comes_before_the_other_arguments(src):
    # The author, 2026-11-06; a positional argument, such as a text's string, still comes first.
    error(src, r"\(like …\) comes first, before the other arguments")
    model("(scene s (text t1 'hi') (text t2 'yo' (like t1)))")
