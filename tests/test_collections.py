"""Collection functions and parameters typed with shapes or interfaces (docs/syntax.md
"Functions as arguments"; docs/reference.md "Collections"; docs/type-system.md 5.c and 6)."""

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import BOOL, INT, POINT, REAL, ListT, Maybe, Refine

RADIUS = Refine(REAL, ((">=", 0),))
G = "(group g (circle a (r 1)) (circle b (r 2)))"


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def expr(src, name):
    place = model(src).get(name).value
    return place.expr if place.bound else place


class TestMap:
    def test_over_a_list(self):
        e = expr("(real k) (list ys (map [k 2] (fn x (* 2 x))))", "ys")
        assert e.op == "map"
        assert e.type == Refine(ListT(REAL), (("length", 2),))

    def test_over_a_group_depends_on_what_the_function_reads(self):
        m = model(f"(scene s {G} (list rs (map g (fn p (* 2 p.r)))))")
        e = m.get("rs").value.expr
        assert {(m.id("a"), "r"), (m.id("b"), "r")} <= e.deps
        assert e.type == Refine(ListT(RADIUS), (("length", 2),))

    def test_a_named_function(self):
        m = model("(func double (real x) (* 2 x)) (real k) (list ys (map [k] double))")
        assert m.get("ys").value.expr.args[1].op == "func"

    def test_the_function_must_fit_the_items(self):
        error("(list ys (map ['a'] (fn (real x) x)))", "expected func")

    def test_the_result_has_a_known_length(self):
        model(f"(scene s {G} (real k (. (map g (fn p p.r)) 1)))")


class TestWhereSortReverse:
    def test_where_gives_members_of_unknown_length(self):
        e = expr(f"(scene s {G} (real|none k (. (. (where g (fn p (> p.r 1))) 0) r)))", "k")
        assert e.type == Maybe(RADIUS)

    def test_sort_keeps_the_length(self):
        m = model(f"(scene s {G} (real k (. (. (sort g (fn p p.r)) 0) r)))")
        assert {(m.id("a"), "r"), (m.id("b"), "r")} <= m.get("k").value.deps

    def test_reverse(self):
        assert model("(list ys (reverse [1 2 3]))").get("ys").value.value == [3, 2, 1]

    def test_sort_needs_a_real_key(self):
        error(f"(scene s {G} (list xs (sort g (fn p 'a'))))", "expected real, got string")


class TestCountSumReduce:
    def test_count(self):
        assert model(f"(scene s {G} (int n (count g)))").get("n").value.value == 2
        e = expr(f"(scene s {G} (int n (count g (fn p (> p.r 1)))))", "n")
        assert e.type == INT

    def test_sum(self):
        assert model("(real k (sum [1 2 3.5]))").get("k").value.value == 6.5
        assert expr("(real j) (real k (sum [j 1]))", "k").type == REAL

    def test_reduce(self):
        src = f"(scene s {G} (real total (reduce g 0 (fn ((real t) (circle p)) (+ t p.r)))))"
        m = model(src)
        assert (m.id("b"), "r") in m.get("total").value.deps

    def test_any_and_all(self):
        assert model("(bool b (any [false true]))").get("b").value.value is True
        assert expr(f"(scene s {G} (bool ok (all g (fn p (> p.r 0)))))", "ok").type == BOOL

    def test_items_that_may_be_none(self):
        error("(list[real|none] xs [1 none]) (real k (sum xs))", "may be none")
        error("(list[real|none] xs [1 none]) (int n (count xs))", "may be none")
        e = expr("(list[real|none] xs [1 none]) (list ys (reverse xs))", "ys")
        assert e.type == ListT(Maybe(REAL))


class TestShapeParameters:
    def test_a_parameter_typed_with_a_shape(self):
        m = model(
            "(func area (circle o) (* 3 o.r o.r)) (scene s (circle c (r 2)) (real k (area c)))"
        )
        assert (m.id("c"), "r") in m.get("k").value.deps

    def test_an_interface_reads_only_what_it_lists(self):
        error("(func area (shape o) (* 3 o.r))", "a shape has no attribute 'r'")
        model("(func left (positioned o) (- o.x 1)) (scene s (rect b) (real k (left b)))")

    def test_a_variant_is_accepted_where_its_base_is(self):
        src = "(variant big () (circle _ (r 5))) (func area (circle o) o.r)"
        m = model(f"{src} (scene s (big b) (real k (area b)))")
        assert (m.id("b"), "r") in m.get("k").value.deps

    def test_a_shape_of_the_wrong_type(self):
        error("(func area (circle o) o.r) (scene s (rect b) (real k (area b)))", "expected circle")

    def test_a_group_as_a_sequence(self):
        src = "(func total ((sequence[circle] xs)) (sum (map xs (fn p p.r))))"
        m = model(f"{src} (scene s {G} (real k (total g)))")
        assert (m.id("a"), "r") in m.get("k").value.deps
        error(f"{src} (scene s (group h (rect r1)) (real k (total h)))", "sequence")


def test_a_position_on_a_sequence_parameter_may_be_none():
    m = model("(func second-r (sequence[circle] g) g[1].r)")
    f = m.functions[m.funcs["second-r"]]
    assert f.result == Maybe(RADIUS)
    assert f.reads == {"g": frozenset({"[].r"})}


def test_reduce_starts_from_a_literal_point():
    src = f"(scene s {G} (point p (reduce g.pos [0 0] (fn ((point acc) (point q)) (+ acc q)))))"
    assert model(src).get("p").value.expr.type == POINT
