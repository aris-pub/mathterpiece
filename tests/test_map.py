import random

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Bound, Free
from mathterpiece.parse import parse

POINTS = (
    "(scene 's' (circle 'x' (pos [0 0]))"
    " (group 'points' (circle _ (pos [3 4])) (circle _ (pos [6 8])) (circle _ (pos [1 0]) (r 2))))"
)


def compile(src, scene=POINTS):
    return compile_model(parse(f"{src} {scene}" if "(scene" not in src else src))


def value(src, name="v"):
    m = compile_model(parse(src))
    return Evaluator(m, random.Random(0)).value(m[name], "value")


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_model(parse(src))


class TestOverAGroup:
    def test_one_value_per_member(self):
        src = f"{POINTS} (real 'v' (let ((ds (map points p (dist x p)))) ds[1]))"
        assert value(src) == pytest.approx(10)

    @pytest.mark.parametrize("k, expected", [(0, 3.0), (1, 6.0), (2, 1.0)])
    def test_reads_each_members_attributes(self, k, expected):
        assert value(f"{POINTS} (real 'v' (let ((xs (map points p p.x))) xs[{k}]))") == expected

    def test_uses_values_from_outside(self):
        src = f"(real 'k' 10) {POINTS} (real 'v' (let ((ys (map points p (+ k p.r)))) ys[2]))"
        assert value(src) == 12

    def test_calls_functions(self):
        src = (
            f"(func 'twice' (params (a 0.0)) (* 2 a)) {POINTS}"
            " (real 'v' (let ((ys (map points p (twice p.y)))) ys[1]))"
        )
        assert value(src) == 16

    def test_follows_the_scene(self):
        m = compile_model(parse(f"{POINTS} (real 'v' (let ((xs (map points p p.x))) xs[0]))"))
        ev = Evaluator(m, random.Random(0))
        ev.write(m["points"].members[0], "x", 7.0)  # ty: ignore[unresolved-attribute]
        assert ev.value(m["v"], "value") == 7

    def test_inside_a_shape(self):
        m = compile_model(
            parse(
                "(scene 's' (group 'g' (circle _ (r 1)) (circle _ (r 2)))"
                " (circle 'c' (r (let ((rs (map g q q.r))) rs[1]))))"
            )
        )
        assert isinstance(m["c"].r, Bound)  # ty: ignore[unresolved-attribute]
        assert Evaluator(m, random.Random(0)).value(m["c"], "r") == 2


class TestOverAList:
    def test_known_lists_fold(self):
        m = compile_model(
            parse("(const 'xs' [1 2 3]) (real 'v' (let ((ys (map xs a (* 2 a)))) ys[2])) (scene _)")
        )
        assert m["v"].value == Free(6.0)  # ty: ignore[unresolved-attribute]

    def test_a_list_from_another_map(self):
        src = f"{POINTS} (real 'v' (let ((xs (map points p p.x)) (ys (map xs a (* a a)))) ys[1]))"
        assert value(src) == 36

    def test_a_list_literal(self):
        assert compile_model(
            parse("(real 'v' (let ((ys (map [1 2] a (+ a 1)))) ys[0])) (scene _)")
        )["v"].value == Free(2.0)  # ty: ignore[unresolved-attribute]


class TestNamesInsideIndexes:
    def test_an_item_used_as_an_index(self):
        src = f"{POINTS} (real 'v' (let ((xs (map points p p.x)) (ys (map [2 0] m xs[m]))) ys[0]))"
        assert value(src) == 1

    def test_a_member_used_inside_an_index(self):
        src = (
            f"{POINTS} (real 'v' (let ((xs (map points p p.x))"
            " (ys (map [0 1] m xs[(+ m 1)]))) ys[1]))"
        )
        assert value(src) == 1


class TestExport:
    def test_unrolls_into_a_list_of_reads(self):
        doc = to_json(
            compile_model(parse(f"{POINTS} (real 'v' (let ((xs (map points p p.x))) xs[1]))"))
        )
        v = doc["objects"][doc["names"]["v"]]["attrs"]["value"]
        members = doc["objects"][doc["names"]["points"]]["members"]
        assert v[0] == "part" and v[2] == 1
        hidden = doc["objects"][v[1][1]]
        assert hidden["attrs"]["value"] == ["list", *(["read", m, "x", None] for m in members)]


class TestErrors:
    @pytest.mark.parametrize(
        "body, match",
        [
            ("(map points p)", "map takes a collection, a name for each item, and a body"),
            ("(map 3 p 1)", "map walks a group or a list"),
            ("(map points 3 p.x)", "the name after a map's collection must be a plain name"),
            ("(map points p 'a')", "a map's body must be a number"),
            ("(map points p (map points q q.x))", "a map's body must be a number"),
            ("(map nope p 1)", "nope"),
        ],
    )
    def test_invalid(self, body, match):
        error(f"{POINTS} (real 'v' (let ((ys {body})) ys[0]))", match)
