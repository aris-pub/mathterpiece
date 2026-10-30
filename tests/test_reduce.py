import random

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Free
from mathterpiece.parse import parse

POINTS = (
    "(scene 's' (circle 'x' (pos [0 0]))"
    " (group 'points' (circle _ (pos [3 4]) (r 1)) (circle _ (pos [6 8]) (r 2))"
    " (circle _ (pos [1 0]) (r 3))))"
)


def evaluate(src, name="v"):
    m = compile_model(parse(f"{POINTS} {src}"))
    ev = Evaluator(m, random.Random(0))
    return m, ev, ev.value(m[name], "value")


def value(src):
    return evaluate(src)[2]


class TestReduce:
    def test_sums(self):
        assert value("(real 'v' (reduce points p (total 0) (+ total p.r)))") == 6

    def test_counts(self):
        src = "(real 'v' (reduce points p (n 0) (if (<= (dist x p) 5) (+ n 1) n)))"
        assert value(src) == 2

    def test_finds_the_largest(self):
        assert value("(real 'v' (reduce points p (best 0) (max best (dist x p))))") == 10

    def test_multiplies(self):
        assert value("(real 'v' (reduce points p (product 1) (* product p.r)))") == 6

    def test_a_running_value_used_more_than_once_does_not_blow_up(self):
        src = (
            "(scene 's' (group 'g' (repeat 40 i (circle _ (r i)))))"
            " (real 'v' (reduce g p (n 0) (if (> p.r 19) (+ n 1) n)))"
        )
        m = compile_model(parse(src))
        assert Evaluator(m, random.Random(0)).value(m["v"], "value") == 20

    def test_follows_the_scene(self):
        m, ev, _ = evaluate("(real 'v' (reduce points p (total 0) (+ total p.r)))")
        ev.write(m["points"].members[2], "r", 10.0)
        assert ev.value(m["v"], "value") == 13

    def test_over_a_map(self):
        src = (
            "(real 'v' (let ((ds (map points p (dist x p)))) (reduce ds d (total 0) (+ total d))))"
        )
        assert value(src) == pytest.approx(5 + 10 + 1)

    def test_known_lists_fold(self):
        m = compile_model(
            parse("(const 'xs' [1 2 3 4]) (real 'v' (reduce xs a (total 0) (+ total a))) (scene _)")
        )
        assert m["v"].value == Free(10.0)  # ty: ignore[unresolved-attribute]

    def test_strings(self):
        src = "(scene _ (text 't' (reduce [1 2 3] a (s '') (let ((n a)) $'{s}{n:.0f}'))))"
        assert compile_model(parse(src))["t"].value == Free("123")  # ty: ignore[unresolved-attribute]

    def test_an_empty_group_gives_the_start(self):
        m = compile_model(
            parse("(scene 's' (group 'empty')) (real 'v' (reduce empty p (total 7) (+ total p.r)))")
        )
        assert m["v"].value == Free(7.0)  # ty: ignore[unresolved-attribute]


class TestErrors:
    @pytest.mark.parametrize(
        "body, match",
        [
            ("(reduce points p (total 0))", "reduce takes a collection, a name for each item"),
            (
                "(reduce points p total (+ total p.r))",
                r"the running value is written \(name start\)",
            ),
            ("(reduce points p (3 0) (+ 1 p.r))", r"the running value is written \(name start\)"),
            ("(reduce points 3 (total 0) (+ total 1))", "the name after a reduce's collection"),
            ("(reduce 3 p (total 0) (+ total 1))", "reduce walks a group or a list"),
            (
                "(reduce points p (total 0) 'a')",
                "a reduce's body must give the same type as its start",
            ),
        ],
    )
    def test_invalid(self, body, match):
        with pytest.raises(CompileError, match=match):
            compile_model(parse(f"{POINTS} (real 'v' {body})"))


class TestSumAndCount:
    def test_sum(self):
        assert value("(real 'v' (sum points p p.r))") == 6

    def test_count(self):
        assert value("(real 'v' (count points p (<= (dist x p) 5)))") == 2

    def test_they_unroll_like_reduce(self):
        m = compile_model(parse("(const 'xs' [1 2 3 4]) (real 'v' (sum xs a (* a a))) (scene _)"))
        assert m["v"].value == Free(30.0)  # ty: ignore[unresolved-attribute]

    def test_names_inside_do_not_clash_with_the_running_value(self):
        src = "(real 'total' 100) (real 'v' (sum points p (+ p.r total)))"
        assert value(src) == 306

    @pytest.mark.parametrize("form", ["sum", "count"])
    def test_over_a_lets_list(self, form):
        body = "d" if form == "sum" else "(> d 4)"
        src = f"(real 'v' (let ((ds (map points p (dist x p)))) ({form} ds d {body})))"
        assert value(src) == pytest.approx(16 if form == "sum" else 2)

    def test_an_empty_group(self):
        m = compile_model(parse("(scene 's' (group 'empty')) (real 'v' (count empty p (> p.r 0)))"))
        assert m["v"].value == Free(0)  # ty: ignore[unresolved-attribute]

    @pytest.mark.parametrize(
        "body, match",
        [
            ("(sum points p 'a')", "a sum's body must be a number"),
            ("(count points p p.r)", "a count's body must be true or false"),
            ("(count points p)", "count takes a collection, a name for each item, and a body"),
        ],
    )
    def test_invalid(self, body, match):
        with pytest.raises(CompileError, match=match):
            compile_model(parse(f"{POINTS} (real 'v' {body})"))

    @pytest.mark.parametrize("form", ["map", "reduce"])
    def test_map_and_reduce_are_part_of_the_language(self, form):
        with pytest.raises(CompileError, match="part of the language"):
            compile_model(parse(f"(func '{form}' (params (a 0.0)) a) (scene _)"))

    def test_an_authors_own_count_hides_the_librarys(self):
        m = compile_model(
            parse("(func 'count' (params (a 0.0)) (* a 10)) (real 'v' (count 2)) (scene _)")
        )
        assert m["v"].value == Free(20.0)  # ty: ignore[unresolved-attribute]

    def test_count_is_still_an_ordinary_name(self):
        m = compile_model(
            parse("(motif 'm' (params (count 3)) (circle 'c' (r count))) (scene _ (m 'd'))")
        )
        assert m is not None
