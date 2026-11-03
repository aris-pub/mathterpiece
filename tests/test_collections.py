"""Collection functions and parameters typed with shapes or interfaces (docs/syntax.md
"Functions as arguments"; docs/reference.md "Collections"; docs/type-system.md 5.c and 6)."""

import json

import pytest
from helpers import bound, doc, error, model, typ, value
from mtpc_check import errors

from mathterpiece.builtins import Undefined, range_by_count, range_by_gap
from mathterpiece.compiler import _core, _type_range
from mathterpiece.types import BOOL, INT, POINT, REAL, ListT, Maybe, Refine

RADIUS = Refine(REAL, ((">=", 0),))
G = "(group g (circle a (r 1)) (circle b (r 2)))"


def expr(src, name):
    attribute = model(src).get(name).value
    return attribute.expr if attribute.bound else attribute


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
        # So reading item 1 gives a real, never none.
        k = model(f"(scene s {G} (real k (. (map g (fn p p.r)) 1)))").get("k").value
        assert k.expr.type == RADIUS


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
        src = "(variant big () (circle_ (r 5))) (func area (circle o) o.r)"
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


class TestMapTypedByItsList:
    # mtp-dqj: map's function takes its parameter's type and range from the list's items, and its
    # result's type from the type expected of the map.
    def test_the_declared_item_type_reaches_a_literal_in_the_function(self):
        m = model("(real s) (list[point] corners (map [0 1 2 3] (fn k [(* s k) 0])))")
        t = m.get("corners").value.expr.type
        assert t.base == ListT(POINT)

    def test_a_folded_map_takes_the_declared_item_type(self):
        m = model("(list[point] corners (map [0 1] (fn k [k 0])))")
        assert m.get("corners").value.value == [(0, 0), (1, 0)]

    def test_the_parameter_takes_the_range_of_a_known_lists_items(self):
        # face[f] on a four-item list is proved in range, so it is never none.
        m = model(
            "(real s) (list[int] face [3 1 2 0] (const))"
            " (list[int] picks (map [0 1 2 3] (fn f (+ face[f] (floor s)))))"
        )
        assert m.get("picks").value.expr.type.base == ListT(INT)

    def test_a_position_proved_in_range_is_never_none(self):
        m = model("(list[int] face [3 1 2 0] (const)) (int f 0 (>= 0) (<= 3)) (int k face[f])")
        assert m.get("k").value.expr.type == INT

    def test_a_position_that_may_be_out_of_range_may_be_none(self):
        error(
            "(list[int] face [3 1 2 0] (const)) (int f 0 (>= 0) (<= 4)) (int k face[f])",
            "may be none",
        )

    def test_the_type_expected_of_an_argument_reaches_the_function(self):
        m = model(
            "(func first-x ((list[point] ps)) (or? ps[0].x 0)) (real s)"
            " (real x (first-x (map [1 2] (fn k [(* s k) 0]))))"
        )
        assert m.get("x").value.bound


class TestRange:
    # mtp-966, the author 2026-11-03: (range start stop (gap g)) steps by g and leaves stop out;
    # (range start stop (num n)) gives n items from start to stop, both included. (map n f) and
    # (foreach i n …) stand for (map (range 0 n (gap 1)) f) and the same for foreach.
    def test_by_a_gap(self):
        assert value("(list v (range 0 5 (gap 1)))") == [0, 1, 2, 3, 4]
        assert value("(list v (range 1 2 (gap 0.25)))") == [1, 1.25, 1.5, 1.75]
        assert value("(list v (range 5 0 (gap -2)))") == [5, 3, 1]

    def test_a_gap_that_points_away_gives_no_items(self):
        assert value("(list[int] v (range 0 5 (gap -1)))") == []

    def test_a_gap_of_0_is_undefined(self):
        error("(list v (range 0 5 (gap 0)))", "undefined")

    def test_by_a_number_of_items(self):
        assert value("(list v (range 0 1 (num 5)))") == [0, 0.25, 0.5, 0.75, 1]
        assert value("(list v (range 0 200 (num 201)))")[-3:] == [198, 199, 200]
        assert value("(list v (range 3 7 (num 1)))") == [3]
        assert value("(list[real] v (range 3 7 (num 0)))") == []
        error("(list v (range 0 1 (num -1)))", "undefined")

    def test_the_item_type(self):
        def item(src):
            return _core(typ(f"(list v {src})").base.item)

        assert item("(range 0 5 (gap 1))") == INT
        assert item("(range 0 1 (gap 0.5))") == REAL
        assert item("(range 0 1 (num 3))") == REAL
        # Whole items from whole ends are ints, so a declared list of ints takes them.
        model("(list[(int (>= 0) (<= 200))] v (range 0 200 (num 201)))")

    def test_known_when_compiling_it_has_a_length(self):
        assert ("length", 5) in typ("(list v (range 0 5 (gap 1)))").constraints
        assert _core(typ("(list xs (range 0 5 (gap 1))) (int v xs[4])")) == INT

    def test_while_drawing_its_length_is_not_known(self):
        e = bound("(int n 3 (>= 0) (<= 10)) (list v (range 0 n (gap 1)))")
        assert e.op == "range" and _core(e.type.item) == INT
        assert typ("(int n 3 (>= 0) (<= 10)) (list xs (range 0 n (gap 1))) (int|none v xs[0])")

    def test_its_items_lie_between_its_ends(self):
        e = bound("(real a 1 (>= 0) (<= 4)) (list v (range a 10 (gap 1)))")
        assert _type_range(e.type.item) == (0, 10)

    def test_a_gap_that_may_be_0_may_give_none(self):
        assert isinstance(
            typ("(real g 1 (>= -1) (<= 1)) (list[real]|none v (range 0 5 (gap g)))"), Maybe
        )
        assert not isinstance(typ("(real g 1 (>= 0.5) (<= 1)) (list v (range 0 5 (gap g)))"), Maybe)

    def test_it_takes_a_gap_or_a_number(self):
        for src in (
            "(range 0 5)",
            "(range 0 5 1)",
            "(range 0 5 (step 1))",
            "(range 0 (gap 1))",
            "(range 0 5 (gap 1) (num 2))",
        ):
            error(f"(list v {src})", r"range is \(range n\), \(range start stop \(gap g\)\)")

    def test_map_over_a_count(self):
        assert value("(list v (map 4 (fn (int i) (* i i))))") == [0, 1, 4, 9]
        e = bound("(int n 3 (>= 0) (<= 10)) (list v (map n (fn (int i) (* 2 i))))")
        assert e.op == "map" and e.args[0].op == "range"

    def test_foreach_over_a_range(self):
        m = model("(scene s (foreach x (range 0 1 (num 3)) (circle_ (pos [x 0]))))")
        assert [m.objects[c].attrs["x"].value for c in m.get("s").members] == [0, 0.5, 1]

    def test_the_compiled_file(self):
        d = doc("(int n 3 (>= 0) (<= 10)) (list v (range 0 n (gap 1)))")
        assert errors(d) == []
        assert json.dumps(d).count('"range"') == 1


class TestRangeOfACount:
    # The author, 2026-11-03: (range n) stands for (range 0 n (gap 1)).
    def test_known(self):
        assert value("(list v (range 5))") == [0, 1, 2, 3, 4]
        assert value("(list[int] v (range 0))") == []
        assert value("(list[int] v (range -3))") == []
        assert _core(typ("(list v (range 5))").base.item) == INT

    def test_a_real_count(self):
        assert value("(list v (range 2.5))") == [0, 1, 2]
        assert _core(typ("(list v (range 2.5))").base.item) == REAL

    def test_while_drawing(self):
        e = bound("(int n 3 (>= 0) (<= 10)) (list v (range n))")
        assert e.op == "range" and _core(e.type.item) == INT and not isinstance(e.type, Maybe)

    def test_the_forms_it_takes(self):
        for src in ("(range)", "(range 1 2)", "(range 1 (gap 1))", "(range (gap 1))"):
            error(f"(list v {src})", r"range is \(range n\), \(range start stop \(gap g\)\)")


class TestRangeEdges:
    def test_floating_gaps_stop_before_stop(self):
        assert value("(list v (range 0 0.3 (gap 0.1)))") == pytest.approx([0, 0.1, 0.2])
        assert len(value("(list v (range 0 1 (gap 0.1)))")) == 10
        assert len(value("(list v (range 0 1 (gap (/ 1 3))))")) == 3

    def test_items_do_not_drift(self):
        # Item k is start + k gap, not the gap added k times.
        assert value("(list v (range 0 100 (gap 0.1)))")[999] == pytest.approx(99.9, abs=1e-12)

    def test_the_same_start_and_stop(self):
        assert value("(list[int] v (range 3 3 (gap 1)))") == []
        assert value("(list v (range 3 3 (num 2)))") == [3, 3]

    def test_num_ends_exactly_at_stop(self):
        assert value("(list v (range 0 0.3 (num 4)))")[-1] == 0.3
        assert value("(list v (range 1 0 (num 3)))") == [1, 0.5, 0]
        assert value("(list v (range 2 9 (num 2)))") == [2, 9]

    def test_whole_items_from_num_are_ints_only_when_all_are_whole(self):
        assert _core(typ("(list v (range 0 10 (num 6)))").base.item) == INT
        assert _core(typ("(list v (range 0 10 (num 5)))").base.item) == REAL

    def test_more_than_a_million_items_is_undefined(self):
        error("(list v (range 0 10000000 (gap 1)))", "undefined")
        error("(list v (range 0 1 (num 2000000)))", "undefined")

    def test_argument_types(self):
        error("(list v (range 'a' 5 (gap 1)))", "range's start is a real")
        error("(list v (range 0 true (gap 1)))", "range's stop is a real")
        error("(list v (range 0 5 (gap 'x')))", "range's gap is a real")
        error("(list v (range 0 5 (num 1.5)))", "range's num is an int")
        error("(real|none k) (list v (range k 5 (gap 1)))", "range's start is a real")

    def test_a_num_that_may_be_negative_may_give_none(self):
        assert isinstance(typ("(int n 1 (>= -1)) (list[real]|none v (range 0 1 (num n)))"), Maybe)
        assert not isinstance(typ("(int n 1 (>= 0)) (list v (range 0 1 (num n)))"), Maybe)

    def test_foreach_needs_a_range_known_when_compiling(self):
        error(
            "(int n 3 (>= 0) (<= 9)) (scene s (foreach i (range n) (circle_)))",
            "known when compiling",
        )

    def test_map_over_a_count_that_is_not_an_int(self):
        error("(list v (map 2.5 (fn (real x) x)))", "map")


class TestRangeFolding:
    # The functions the compiler folds with, which the runtime mirrors (web/src/builtins.ts).
    def test_by_gap(self):
        assert range_by_gap(0, 5, 1) == [0, 1, 2, 3, 4]
        assert range_by_gap(5, 0, -1) == [5, 4, 3, 2, 1]
        assert range_by_gap(0, 5, -1) == []
        assert range_by_gap(0, -5, 1) == []
        with pytest.raises(Undefined):
            range_by_gap(0, 5, 0)
        with pytest.raises(Undefined):
            range_by_gap(0, 1e9, 1)

    def test_by_count(self):
        assert range_by_count(0, 1, 0) == []
        assert range_by_count(0, 1, 1) == [0]
        assert range_by_count(0, 1, 3) == [0, 0.5, 1]
        with pytest.raises(Undefined):
            range_by_count(0, 1, -1)
