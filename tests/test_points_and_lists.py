"""Points and lists (mtp-diqi): [X Y] is a point, sugar for (point-of X Y), and {X…} a list, sugar
for (list-of X…) (docs/spec/core.md, rule sugar-rewrites; grammar.md, rule lists). A point is a
primitive of its own, and no value is converted from one type to another unless a form asks for it
(types.md, rule conversions), so a list is never read as a point, or a point as a list. Until
mtp-diqi a list of two numbers was a point where a point was expected (mtp-vrf9, mtp-trp9)."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import _core
from mathterpiece.types import INT, POINT, ListT

X = "(real x 1)"
SIDE = "(real side 3) (int j 0 (>= 0) (<= 1))"
PS = "(list[point] ps {[0 0] [1 1]}) (real x 1)"


def type_of(src, name="v"):
    return _core(model(src).get(name).value.type)


@pytest.mark.parametrize(
    "src",
    [
        "(point v [1 2])",
        "(point v (let ((p [1 2])) p))",
        "(func f ((real a)) [a 2]) (point v (f 1))",
        f"{X} (point v (if (> x 0) [x 2] [0 0]))",
        "(point p [1 2]) (point v (let ((q [p.x 3])) q))",
        "(point v (+ [1 2] [3 4]))",
        "(point v (* 2 [1 2]))",
        "(point v (lerp [0 0] [2 4] 0.5))",
    ],
    ids=["literal", "let", "function", "if", "let-of-a-read", "sum", "scaled", "lerp"],
)
def test_brackets_make_a_point(src):
    model(src)


def test_the_value_of_brackets_is_a_point():
    assert type_of("(real v 0) (point p (let ((q [1 2])) q))", "p") == POINT
    m = model("(scene s (let ((p [1 2])) (circle c (pos p))))")
    assert (m.get("c").attrs["x"].value, m.get("c").attrs["y"].value) == (1, 2)


@pytest.mark.parametrize(
    "src",
    [
        f"{X} (scene s (let ((p [x 2])) (circle c (pos p))))",
        f"{SIDE} (list corners {{[side 0] [0 0]}}) (scene s (circle c (pos corners[j])))",
        f"{SIDE} (scene s (let ((cs {{[3 0] [0 0]}})) (circle c (pos cs[j]))))",
        f"{PS} (scene s (polyline_ (points (map ps (fn p [(+ p.x x) p.y])))))",
        f"{PS} (list pts (map ps (fn p [(+ p.x x) p.y]))) (scene s (polyline_ (points pts)))",
        f"{PS} (func f ((point p)) [(+ p.x x) 0]) (scene s (polyline_ (points (map ps f))))",
    ],
    ids=["let", "item", "item-of-a-let", "map", "map-variable", "map-function"],
)
def test_a_point_where_a_point_is_expected(src):
    model(src)


def test_a_map_to_points_is_a_list_of_points():
    assert type_of(f"{PS} (list v (map ps (fn p [(+ p.x x) p.y])))") == ListT(POINT)


def test_braces_make_a_list():
    assert type_of("(list v {1 2})") == ListT(INT)
    assert type_of("(list v {[0 0] [1 2]})") == ListT(POINT)


@pytest.mark.parametrize(
    "src",
    [
        "(point v {1 2})",
        "(point v (let ((p {1 2})) p))",
        "(func f ((real a)) {a 2}) (point v (f 1))",
        f"{X} (list[real] q {{x 2}} (length 2)) (point v q)",
        "(scene s (circle c (pos {1 2})))",
        f"{X} (scene s (let ((p {{x 2}})) (circle c (pos p))))",
        f"{SIDE} (list corners {{{{side 0}} {{0 0}}}}) (scene s (circle c (pos corners[j])))",
        "(list[point] v {{0 0} {1 1}})",
        f"{PS} (scene s (polyline_ (points (map ps (fn p {{(+ p.x x) p.y}})))))",
        "(func f ((real k)) {k 0}) (list[point] v (map {1 2} f))",
    ],
    ids=[
        "literal",
        "let",
        "function",
        "list-variable",
        "pos",
        "pos-of-a-let",
        "item",
        "items",
        "map",
        "map-function",
    ],
)
def test_a_list_where_a_point_is_expected_is_an_error(src):
    error(src, r"expected (list\[|func\[.* )?point")


@pytest.mark.parametrize(
    "src, match",
    [
        ("(list[real] v [1 2])", r"expected list\[real\], got point"),
        ("(list v [1 2])", "expected a list, got point"),
        ("(list[list[real]] v {[1 2]})", r"expected list\[real\], got point"),
        ("(scene s (line l (dash [4 2])))", "expected list"),
        ("(colormap m [#'red' #'blue'])", r"\(colormap name \{color…\} keyword…\)"),
        (
            "(colormap m {#'red' #'blue'} (positions [0 1]))",
            r"positions are a list: \{start end\}",
        ),
    ],
    ids=["typed", "list", "item", "dash", "colormap", "positions"],
)
def test_a_point_where_a_list_is_expected_is_an_error(src, match):
    error(src, match)


def test_a_point_and_a_list_are_not_equal_values():
    error(
        "(point p [1 2] (const)) (list[int] xs {1 2} (const)) (bool v (= p xs))",
        "compares two of one type",
    )
    error("(list[int] xs {1 2} (const)) (bool v (= xs [1 2]))", "compares two of one type")


@pytest.mark.parametrize(
    "src",
    [
        "(point v [1 2 3])",
        "(point v [1])",
        "(point v [])",
        "(point v (let ((p [1 2 3])) p))",
        "(list v {[1 2 3]})",
        f"{X} (point v (if (> x 0) [x 2] [0 0 0]))",
    ],
    ids=["three", "one", "none", "let", "in-a-list", "if"],
)
def test_a_point_has_two_items(src):
    error(src, r"a point is two numbers, \[x y\]")


def test_a_point_holds_numbers():
    error("(point v ['a' 'b'])", "expected real")
    error("(scene s (circle a) (circle b) (let ((p [a b])) (circle c (pos p))))", "expected real")


def test_the_compiled_file_passes_the_schema():
    d = doc(
        f"{X} (func f ((real a)) [a 2]) (scene s (circle c (pos (f x))) (circle d (pos [x 1])))"
    )
    assert errors(d) == []
