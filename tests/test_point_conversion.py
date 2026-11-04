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
