import random

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.parse import parse

GROUPS = (
    "(scene 's' (circle 'x' (pos [0 0]))"
    " (group 'three' (circle _ (pos [3 4]) (r 1)) (circle _ (pos [6 8]) (r 2))"
    " (circle _ (pos [1 0]) (r 3)))"
    " (group 'two' (circle _ (r 5)) (circle _ (r 7))))"
)


def model(funcs, values):
    return compile_model(parse(f"(real 'n' 0) {funcs} {GROUPS} {values}"))


def value(funcs, expr):
    m = model(funcs, f"(real 'v' {expr})")
    return Evaluator(m, random.Random(0)).value(m["v"], "value")


def body(funcs, name):
    doc = to_json(model(funcs, ""))
    return doc["functions"][name]["body"]


def ops(expr) -> set[str]:
    if not isinstance(expr, list) or not expr:
        return set()
    head = {expr[0]} if isinstance(expr[0], str) else set()
    return head.union(*(ops(e) for e in expr))


WALKS = {"walk-map", "walk-reduce", "walk-sort", "walk-any", "walk-all"}


class TestKnownSizesUnroll:
    def test_a_list_parameter(self):
        f = "(func 'f' (params (xs [1 2 3])) (sum xs v v))"
        assert not ops(body(f, "f")) & WALKS
        assert value(f, "(f [4 5 6])") == 15

    def test_a_literal_and_a_let(self):
        f = "(func 'f' (params (k 1)) (let ((ys (map [1 2 3] a (* a k)))) (count ys y (> y 2))))"
        assert not ops(body(f, "f")) & WALKS
        assert value(f, "(f 2)") == 2

    def test_a_const(self):
        f = "(const 'cs' [1 2 3 4]) (func 'f' (params (k 1)) (any (map cs c (> c k))))"
        assert not ops(body(f, "f")) & WALKS


class TestGroupParameters:
    @pytest.mark.parametrize(
        "f, call, expected",
        [
            ("(func 'f' (params (g)) (sum g p p.r))", "(f three)", 6),
            ("(func 'f' (params (g)) (sum g p p.r))", "(f two)", 12),
            ("(func 'f' (params (g) (k 0.0)) (count g p (> p.r k)))", "(f three 1)", 2),
            ("(func 'f' (params (g)) (reduce g p (best 0) (max best p.r)))", "(f two)", 7),
            ("(func 'f' (params (g)) (let ((rs (map g p p.r))) rs[1]))", "(f three)", 2),
            ("(func 'f' (params (g)) (let ((rs (map g p p.r))) (sum rs v v)))", "(f two)", 12),
            ("(func 'f' (params (g)) g[1].r)", "(f two)", 7),
        ],
    )
    def test_values(self, f, call, expected):
        assert value(f, call) == pytest.approx(expected)

    def test_they_walk_while_drawing(self):
        assert "walk-reduce" in ops(body("(func 'f' (params (g)) (sum g p p.r))", "f"))

    def test_sort_by_key(self):
        f = "(func 'f' (params (g) (o)) (let ((ns (sort g p (dist o p)))) ns[0].r))"
        assert value(f, "(f three x)") == 3
        f = "(func 'f' (params (g)) (let ((ns (reverse (sort-desc g p p.r)))) ns[0].r))"
        assert value(f, "(f three)") == 1

    def test_any_and_all_stop_early(self):
        f = "(func 'f' (params (g) (d 0.0)) (any (map g p (or (> p.r 2) (> (/ 1 d) 0)))))"
        m = model(f, "(bool 'v' (f two n))")
        assert Evaluator(m, random.Random(0)).value(m["v"], "value") is True
        f = "(func 'f' (params (g)) (all (map g p (> p.r 4))))"
        m = model(f, "(bool 'v' (f two))")
        assert Evaluator(m, random.Random(0)).value(m["v"], "value") is True

    def test_nested(self):
        f = "(func 'f' (params (g)) (sum g p (count g q (< q.r p.r))))"
        assert value(f, "(f three)") == 3

    def test_a_function_never_called_still_builds(self):
        assert body("(func 'f' (params (g)) (sum g p p.r))", "f")

    def test_follows_the_scene(self):
        m = model("(func 'f' (params (g)) (sum g p p.r))", "(real 'v' (f two))")
        ev = Evaluator(m, random.Random(0))
        ev.write(m["two"].members[0], "r", 10.0)
        assert ev.value(m["v"], "value") == 17

    def test_walking_an_object_that_is_not_a_group(self):
        with pytest.raises(CompileError, match="sum walks a group or a list"):
            model("(func 'f' (params (g)) (sum g p p.r))", "(real 'v' (f x))")


class TestRef:
    def test_ref_in_a_function_body(self):
        assert value("(func 'f' (params (k 1)) (* (ref 'k') 2))", "(f 4)") == 8
