"""A member of a group never reads the group whole, since the group includes the member itself:
an attribute of every member, as g.x, (map g …) or another collection function over g, and g[k]
with k known only while drawing, are compile errors inside g (mtp-gvrf.16), as a read of itself is
(mtp-gvrf.10). (count g) reads no attribute, so it is allowed. The values go in a list variable
outside the group, each member bound to its own item, so any member may read the whole list, and a
member is recomputed when an item of another member changes, one declared after it too (mtp-mnvd).
A container never reads itself in its own clip or defaults either (mtp-gvrf.16)."""

import pytest
from helpers import error, model

VERTEX = "(motif vertex ((int part 0)) (circle_ (r 10)))\n"
DIAL = "(motif dial ((real t 0.5 (>= 0) (<= 1)) (color tint 'red')) (circle face (r 1)))\n"
K = "(int k 0 (>= 0) (<= 1))\n"

PARTS = (
    VERTEX + "(list[int] parts [0 0 0] (length 3))\n"
    "(scene s (group verts (foreach i 3"
    " (vertex #'v-{i}' (part parts[i]) (pos [0 (count parts (fn q (= q parts[i])))])))))"
)


def test_each_member_reads_the_list_of_every_member():
    m = model(PARTS)
    for i in range(3):
        assert (m.id("parts"), None) in m.get(f"v-{i}").attrs["y"].deps
        assert m.get(f"v-{i}").attrs["part"].deps == {(m.id("parts"), None)}


def test_a_member_reads_other_members_by_a_position_known_when_compiling():
    m = model(
        VERTEX + "(scene s (group verts (foreach i 3 (vertex #'v-{i}' (part free@0)"
        " (pos [0 (if (> i 0) verts[(- i 1)].part 0)])))))"
    )
    for i in (1, 2):
        assert (m.id(f"v-{i - 1}"), "part") in m.get(f"v-{i}").attrs["y"].deps
    m = model("(scene s (group g (circle a (r free@1)) (circle b (r 1) (x g[0].r))))")
    assert (m.id("a"), "r") in m.get("b").attrs["x"].deps


def test_a_shape_outside_the_group_reads_it_whole():
    m = model(
        K + "(scene s (group g (circle a (x free@1)) (circle b (x free@2)))"
        " (circle c (r (abs (sum g.x))) (x (sum (map g (fn m m.x)))) (y (or? g[k].x 0))))"
    )
    for attr in ("r", "x", "y"):
        deps = m.get("c").attrs[attr].deps
        assert {(m.id("a"), "x"), (m.id("b"), "x")} <= deps


def test_the_count_of_the_group_is_every_member():
    m = model(
        "(scene s (group g (circle a (r 1) (x (count g)) (y g.length)) (circle b (r 2))"
        " (circle c (r 3))))"
    )
    assert m.get("a").attrs["x"].value == 3
    assert m.get("a").attrs["y"].value == 3
    m = model(DIAL + "(scene s (group g (dial a (x (count g))) (dial b)))")
    assert m.get("a").attrs["x"].value == 2


def test_a_group_inside_counts_the_group_around_it():
    m = model(
        "(scene s (group outer (group inner (circle a (r 1) (x (count outer))))"
        " (circle b (r 2)) (circle c (r 3))))"
    )
    assert m.get("a").attrs["x"].value == 3


def test_a_group_counts_itself_in_its_defaults():
    m = model(
        "(scene s (group g (defaults (stroke-width (count g))) (circle a (r 1)) (circle b (r 2))))"
    )
    assert m.get("a").attrs["stroke-width"].value == 2


def test_a_container_reads_other_shapes_in_its_clip_and_defaults():
    m = model(
        DIAL + "(scene s (circle c (r free@2))"
        " (dial d (clip (rect_ (width c.r) (height 1))) (defaults (stroke-width c.r))))"
    )
    assert (m.id("c"), "r") in m.get("d.face").attrs["stroke-width"].deps


def test_a_group_whose_members_depend_on_how_many_it_has():
    error(
        "(scene s (group g (circle a (r 1)) (foreach i (count g) (circle #'c-{i}' (r 1)))))",
        r"the members of g depend on g itself",
    )


def self_read(name: str) -> str:
    return (
        rf"{name} cannot read its own attributes in its own declaration: give the value a name"
        rf" with \(let \(\(name value\)\) …\) around {name}, and read that name instead"
    )


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
    error(src, self_read("v-0"))


SHAPE = "(scene s (group g (circle a (x free@1) (stroke-width {})) (circle b (x free@2))))"
INSTANCE = DIAL + "(scene s (group g (dial a (t free@0.1) (x {})) (dial b (t free@0.2))))"


@pytest.mark.parametrize(
    "src",
    [
        SHAPE.format("(abs (sum g.x))"),
        SHAPE.format("(abs (sum (map g (fn c c.x))))"),
        SHAPE.format("(count (where g (fn c (> c.x 0))))"),
        SHAPE.format("(abs (reduce g 0 (fn ((real t) (circle c)) (+ t c.x))))"),
        SHAPE.format("(count g (fn c (> c.x 0)))"),
        SHAPE.format("(count g.members)"),
        K + SHAPE.format("(abs (or? g[k].x 0))"),
        "(func total ((sequence[circle] xs)) (sum (map xs (fn c c.x))))\n"
        + SHAPE.format("(abs (total g))"),
        INSTANCE.format("(sum g.t)"),
        INSTANCE.format("(sum (map g (fn c c.t)))"),
        INSTANCE.format("(count (where g (fn c (> c.t 0.5))))"),
        INSTANCE.format("(reduce g 0 (fn ((real t) (dial c)) (+ t c.t)))"),
        K + INSTANCE.format("(or? g[k].t 0)"),
        "(scene s (group g (group a (translate [(sum (map g (fn m m.x))) 0]) (circle c (x 1)))"
        " (circle b (x free@2))))",
        "(scene s (group g (group inner (circle a (x free@1) (r (abs (sum (map g (fn m m.x)))))))"
        " (circle b (x free@2))))",
        DIAL + "(scene s (group g (group inner (dial a (t free@0.1) (x (sum (map g (fn m m.x))))))"
        " (dial b (t free@0.2))))",
    ],
)
def test_a_member_reading_the_whole_group(src):
    error(src, self_read("a"))


@pytest.mark.parametrize(
    "src",
    [
        "(scene s (group g (clip (rect window (width (abs (sum g.x))) (height 1)))"
        " (circle a (x free@1))))",
        "(scene s (group g (clip (rect window (width (count (map g (fn m m.x)))) (height 1)))"
        " (circle a (x free@1))))",
        "(scene s (group g (translate [1 0]) (clip (rect window (width g.translate.x) (height 1)))"
        " (circle a (x free@1))))",
        "(scene s (group g (defaults (stroke-width (abs (sum g.x)))) (circle a (x free@1))))",
        "(scene s (group g (defaults (stroke-width g[0].r)) (circle a (r 1)) (circle b (r 2))))",
    ],
)
def test_a_group_reading_itself_in_its_clip_or_defaults(src):
    error(src, self_read("g"))
