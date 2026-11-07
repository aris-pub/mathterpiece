"""A list of two numbers is a point where a point is expected, when its length is known when
compiling (mtp-vrf9; type-system.md, section 3). The author, 2026-11-04, after (let ((p [x 2]))
(circle c (pos p))) failed with 'expected point, got list[real]'."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import _core
from mathterpiece.types import POINT

X = "(real x 1)"


def pos_of(src):
    return model(src).get("c").attrs["x"]


@pytest.mark.parametrize(
    "src",
    [
        "(scene s (let ((p [x 2])) (circle c (pos p))))",
        "(func f ((real a)) [a 2]) (scene s (circle c (pos (f x))))",
        "(list[real] q [x 2] (length 2)) (scene s (circle c (pos q)))",
        "(scene s (circle c (pos (if (> x 0) [x 2] [0 0]))))",
        "(point p [x 2]) (scene s (let ((q [p.x 3])) (circle c (pos q))))",
    ],
    ids=["let", "function", "list-variable", "if", "let-of-a-read"],
)
def test_where_a_point_is_expected(src):
    pos_of(f"{X} {src}")


def test_the_value_is_a_point():
    m = model(f"{X} (scene s (let ((p [x 2])) (circle c (pos p)))) (point v c.pos)")
    assert _core(m.get("v").value.expr.type) == POINT
    m = model("(scene s (let ((p [1 2])) (circle c (pos p))))")
    assert (m.get("c").attrs["x"].value, m.get("c").attrs["y"].value) == (1, 2)


def test_a_point_variable():
    m = model(f"{X} (func f ((real a)) [a 2]) (point v (f x))")
    assert _core(m.get("v").value.type) == POINT


def test_only_two_numbers():
    error(f"{X} (scene s (let ((p [x 2 3])) (circle c (pos p))))", "expected point")
    error("(scene s (let ((p ['a' 'b'])) (circle c (pos p))))", "expected point")


def test_only_a_length_known_when_compiling():
    # A free list variable may be written with another length while drawing; a bound one
    # always equals its expression, so its length is known.
    error("(list[real] q [1 2]) (scene s (circle c (pos q)))", "expected point")
    pos_of(f"{X} (list[real] q [x 2]) (scene s (circle c (pos q)))")
    error(f"{X} (scene s (circle c (pos (if (> x 0) [x 2] [0 0 0]))))", "a point is two numbers")


def test_the_compiled_file_passes_the_schema():
    d = doc(
        f"{X} (func f ((real a)) [a 2]) (scene s (circle c (pos (f x))) (circle d (pos [x 1])))"
    )
    assert errors(d) == []


# mtp-trp9: a list whose items all have the same known length gives each item that length, so
# an item, even at a position known only while drawing, is a point where a point is expected.
# The author chose this on 2026-11-07, after [[side 0] [0 0]] in examples/pythagoras.mtp had to
# be declared list[point].
SIDE = "(real side 3) (int j 0 (>= 0) (<= 1))"


@pytest.mark.parametrize(
    "src",
    [
        "(list corners [[side 0] [0 0]]) (scene s (circle c (pos corners[0])))",
        "(list corners [[side 0] [0 0]]) (scene s (circle c (pos corners[j])))",
        "(list[list[real]] corners [[side 0] [0 0]]) (scene s (circle c (pos corners[j])))",
        "(scene s (let ((cs [[side 0] [0 0]])) (circle c (pos cs[j]))))",
        "(scene s (let ((cs [[3 0] [0 0]])) (circle c (pos cs[j]))))",
        "(list corners [[3 0] [0 0]] (const)) (scene s (circle c (pos corners[j])))",
    ],
    ids=["fixed", "drawing", "declared", "let", "let-of-literals", "const"],
)
def test_an_item_of_a_list_of_pairs(src):
    pos_of(f"{SIDE} {src}")


def test_items_of_different_lengths_are_not_points():
    error(
        f"{SIDE} (list corners [[side 0] [0 0 0]]) (scene s (circle c (pos corners[j])))",
        "expected point",
    )


def test_a_free_list_of_pairs_is_not_converted():
    # A writer may give a free list, or one started free@, items of another length.
    error(
        f"{SIDE} (list corners [[3 0] [0 0]] (length 2)) (scene s (circle c (pos corners[j])))",
        "expected point",
    )
    error(
        f"{SIDE} (list[list[real]] corners free@[[side 0] [0 0]] (length 2))"
        " (scene s (circle c (pos corners[j])))",
        "expected point",
    )


def test_lists_of_numbers_of_different_types_meet():
    # [0 0] is a list of ints and [side 0] one of reals with side's range: both are lists of
    # reals, as examples/pythagoras.mtp first needed.
    src = "(real side 3 (>= 0)) (list corners [[0 0] [side 0]])"
    assert str(model(src).get("corners").type) == "(list[(list[real] (length 2))] (length 2))"
    pos_of(f"{src} (int j 0 (>= 0) (<= 1)) (scene s (circle c (pos corners[j])))")


def test_a_default_of_another_length_is_still_a_default():
    # Items of a known length met an empty default and broke it, as in a replica that read
    # (or? shares[i] []) before items carried their length.
    src = (
        "(real m 1) (list[list[real]] rows (map (range 3) (fn j (map (range 4) (fn k (* m k))))))"
        " (int i 0 (>= 0) (<= 5)) (real v (let ((row (or? rows[i] []))) (or? row[2] 0)))"
    )
    assert str(model(src).get("v").type) == "real"
