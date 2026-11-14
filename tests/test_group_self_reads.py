"""A group's members may read the group itself: by a position known only while drawing, as
g[j].part, or whole, as (map g …), g.r or (count g). Such a read sees every member, those declared
after the reader too, so the reader is recomputed when any of them changes (mtp-mnvd). A member
never reads itself through the group in its own declaration, as verts[i] inside v-i
(mtp-gvrf.10): the values that place the members are variables declared outside the group."""

import pytest
from helpers import error, model

VERTEX = "(motif vertex ((int part 0)) (circle_ (r 10)))\n"

PARTS = (
    VERTEX + "(int p-0 0) (int p-1 0) (int p-2 0)\n"
    "(scene s (group verts (foreach i 3 (let ((p (name $'p-{i}')))"
    " (vertex #'v-{i}' (part p) (pos [0 (count [p-0 p-1 p-2] (fn q (= q p)))]))))))"
)

NEIGHBOURS = (
    VERTEX + "(int shift 1 (>= 1) (<= 2))\n"
    "(scene s (group verts (foreach i 3 (vertex #'v-{i}' (part free@0)"
    " (pos [0 (or? verts[(mod (+ i shift) 3)].part 0)])))))"
)


def test_each_member_reads_the_variables_of_the_members_after_it():
    m = model(PARTS)
    for i in range(3):
        deps = m.get(f"v-{i}").attrs["y"].deps
        assert {(m.id(f"p-{j}"), None) for j in range(3)} <= deps
        assert m.get(f"v-{i}").attrs["part"].deps == {(m.id(f"p-{i}"), None)}


def test_a_position_known_only_while_drawing_reads_the_members_after_it():
    # shift is 1 or 2, so each vertex reads another one, never itself.
    m = model(NEIGHBOURS)
    for i in range(3):
        deps = m.get(f"v-{i}").attrs["y"].deps
        assert {(m.id(f"v-{j}"), "part") for j in range(3)} <= deps


@pytest.mark.parametrize(
    "src",
    [
        VERTEX + "(scene s (group verts (foreach i 3 (vertex #'v-{i}' (part free@0)"
        " (pos [0 (or? verts[i].part 0)])))))",
        VERTEX + "(scene s (group verts (foreach i 3 (vertex #'v-{i}' (part free@0)"
        " (pos [0 (count (range 3) (fn j (= (or? verts[j].part 0) 1)))])))))",
        "(scene s (group verts (foreach i 3 (circle #'v-{i}' (r 1) (y verts[i].r)))))",
    ],
)
def test_a_member_reading_itself_through_the_group(src):
    error(
        src,
        r"v-0 cannot read its own attributes in its own declaration: give the value a name"
        r" with \(let \(\(name value\)\) …\) around v-0, and read that name instead",
    )


def test_a_map_over_the_group_reads_the_members_after_it():
    m = model(
        "(scene s (group g (circle a (x free@1) (stroke-width (abs (sum (map g (fn c c.x))))))"
        " (circle b (x free@2))))"
    )
    assert (m.id("b"), "x") in m.get("a").attrs["stroke-width"].deps


def test_an_attribute_of_every_member_reads_the_members_after_it():
    m = model(
        "(scene s (group g (circle a (x free@1) (stroke-width (abs (sum g.x))))"
        " (circle b (x free@2))))"
    )
    assert (m.id("b"), "x") in m.get("a").attrs["stroke-width"].deps


def test_the_count_of_the_group_is_every_member():
    m = model(
        "(scene s (group g (circle a (r 1) (x (count g))) (circle b (r 2)) (circle c (r 3))))"
    )
    assert m.get("a").attrs["x"].value == 3


def test_a_group_inside_reads_the_group_around_it_whole():
    m = model(
        "(scene s (group outer (group inner (circle a (r 1) (x (count outer))))"
        " (circle b (r 2)) (circle c (r 3))))"
    )
    assert m.get("a").attrs["x"].value == 3


def test_a_group_whose_members_depend_on_how_many_it_has():
    error(
        "(scene s (group g (circle a (r 1)) (foreach i (count g) (circle #'c-{i}' (r 1)))))",
        r"the members of g depend on g itself",
    )
