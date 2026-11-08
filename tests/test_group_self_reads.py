"""A group's members may read the group itself: by a position known only while drawing, as
g[j].part, or whole, as (map g …), g.r or (count g). Such a read sees every member, those declared
after the reader too, so the reader is recomputed when any of them changes (mtp-mnvd)."""

from helpers import error, model

PARTS = (
    "(motif vertex ((int part 0)) (circle_ (r 10)))\n"
    "(scene s (group verts (foreach i 3 (vertex #'v-{i}' (part free@0)"
    " (pos [0 (count (range 3) (fn j (= (or? verts[j].part 0) 1)))])))))"
)


def test_a_position_known_only_while_drawing_reads_the_members_after_it():
    m = model(PARTS)
    for i in range(3):
        deps = m.get(f"v-{i}").attrs["y"].deps
        assert {(m.id(f"v-{j}"), "part") for j in range(3)} <= deps


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
