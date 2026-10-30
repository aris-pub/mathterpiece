import random

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Free
from mathterpiece.parse import parse

POINTS = (
    "(scene 's' (circle 'x' (pos [0 0]))"
    " (group 'points' (circle _ (pos [3 4]) (r 1)) (circle _ (pos [6 8]) (r 2))"
    " (circle _ (pos [1 0]) (r 3))))"
)


def model(src):
    return compile_model(parse(f"(real 'k' 2) (real 'n' 0) {POINTS} {src}"))


def value(src, name="v"):
    m = model(src)
    return Evaluator(m, random.Random(0)).value(m[name], "value")


def folded(src):
    return compile_model(parse(f"{src} (scene _)"))["v"].value  # ty: ignore[unresolved-attribute]


class TestLists:
    def test_a_literal(self):
        assert folded("(bool 'v' (let ((bs [true false])) bs[1]))") == Free(False)

    def test_a_const(self):
        assert folded("(const 'bs' [false true]) (bool 'v' bs[1])") == Free(True)

    def test_a_map_with_a_condition(self):
        assert value("(bool 'v' (let ((big (map points p (> p.r 1)))) big[2]))") is True

    def test_reverse(self):
        assert folded("(bool 'v' (let ((bs (reverse [true false]))) bs[0]))") == Free(False)

    def test_count_over_a_list_of_bools(self):
        assert value("(real 'v' (let ((big (map points p (> p.r 1)))) (count big b b)))") == 2

    def test_while_drawing_bools_stay_bools(self):
        m = model("(bool 'v' (let ((big (map points p (> p.r k)))) big[2]))")
        assert Evaluator(m, random.Random(0)).value(m["v"], "value") is True


class TestAnyAndAll:
    @pytest.mark.parametrize(
        "expr, expected",
        [
            ("(any (map points p (> p.r 2)))", True),
            ("(any (map points p (> p.r 3)))", False),
            ("(all (map points p (> p.r 0)))", True),
            ("(all (map points p (> p.r 1)))", False),
        ],
    )
    def test_over_a_map(self, expr, expected):
        assert value(f"(bool 'v' {expr})") is expected

    def test_over_a_lets_list(self):
        assert value("(bool 'v' (let ((big (map points p (> p.r k)))) (any big)))") is True

    def test_over_a_known_list(self):
        assert folded("(bool 'v' (all [true true false]))") == Free(False)
        assert folded("(bool 'v' (any [false true]))") == Free(True)

    def test_a_list_written_in_place_unrolls_into_or(self):
        doc = to_json(model("(bool 'v' (any (map points p (> p.r k))))"))
        assert doc["objects"][doc["names"]["v"]]["attrs"]["value"][0] == "or"

    def test_a_list_written_in_place_stops_early(self):
        assert value("(bool 'v' (any [(= n 0) (> (/ 1 n) 2)]))") is True

    def test_follows_the_scene(self):
        m = model("(bool 'v' (all (map points p (> p.r 0))))")
        ev = Evaluator(m, random.Random(0))
        ev.write(m["points"].members[1], "r", 0.0)
        assert ev.value(m["v"], "value") is False

    def test_an_authors_own_any_hides_the_librarys(self):
        m = compile_model(
            parse("(func 'any' (params (a 0.0)) (* a 2)) (real 'v' (any 4)) (scene _)")
        )
        assert m["v"].value == Free(8.0)  # ty: ignore[unresolved-attribute]


class TestErrors:
    @pytest.mark.parametrize(
        "expr, match",
        [
            ("(any [1 2])", "any takes a list of bools"),
            ("(all (> k 1))", "all takes a list of bools"),
            ("(any [true] [false])", "any takes one list"),
            ("(let ((bs [true 1])) bs[0])", "a list holds numbers or bools, not both"),
            ("(let ((bs (sort [true false]))) bs[0])", "sorts a list of numbers"),
            ("(let ((bs [true false])) bs.x)", "a list of bools is indexed by number"),
            ("(+ [true false] [1 2])", "expected"),
        ],
    )
    def test_invalid(self, expr, match):
        with pytest.raises(CompileError, match=match):
            model(f"(bool 'v' {expr})")
