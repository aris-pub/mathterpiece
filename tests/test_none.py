"""none: where it comes from, how it spreads, and where it must be handled (docs/type-system.md,
section 5.c; the Undefined column in docs/reference.md)."""

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import BOOL, REAL, STRING, ListT, Maybe, Refine


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def typ(src, name):
    return model(src).get(name).value.type


def bound(src, name):
    attribute = model(src).get(name).value
    assert attribute.bound
    return attribute.expr


def value(src, name):
    attribute = model(src).get(name).value
    assert not attribute.bound
    return attribute.value


class TestWhereItComesFrom:
    def test_written_on_purpose(self):
        assert value("(real|none c none)", "c") is None

    def test_a_division_that_may_be_by_zero(self):
        assert typ("(real k 1) (real|none d (/ 1 k))", "d") == Maybe(REAL)
        error("(real k 1) (real d (/ 1 k))", "may be none")

    def test_a_division_proven_safe(self):
        model("(real k 1 (>= 1)) (real d (/ 1 k))")
        model("(real k -3 (< -2)) (real d (/ 1 k))")

    def test_mod_by_a_divisor_that_may_be_zero(self):
        error("(int k 1) (int d (mod 7 k))", "may be none")
        model("(int k 1 (>= 1)) (int d (mod 7 k))")

    def test_known_inputs_are_a_compile_error(self):
        error("(real d (mod 1 0))", "division by zero")
        error("(real d (^ 0 -1))", "undefined")
        error("(real d (^ -8 0.5))", "undefined")

    def test_a_result_too_large_for_a_real(self):
        error("(real d (* 1e150 1e150 1e150))", "too large for a real")
        assert typ("(real a) (real b) (real c) (real|none d (* a b c))", "d") == Maybe(REAL)
        model("(real a) (real b) (real d (* a b))")

    def test_a_literal_beyond_the_limit(self):
        error("(real d 1e151)", "beyond")

    def test_a_bound_value_that_may_break_its_constraint(self):
        e = bound("(real k 1) (real|none d (* 2 k) (>= 0))", "d")
        assert e.op == "check"
        assert e.type == Maybe(REAL)
        error("(real k 1) (real d (* 2 k) (>= 0))", r"may break \(>= 0\)")


class TestHowItSpreads:
    def test_anything_computed_from_none_is_none(self):
        assert typ("(real|none c) (real|none d (+ 1 c))", "d") == Maybe(REAL)
        error("(real|none c) (real d (+ 1 c))", "may be none")

    def test_a_known_none_folds(self):
        assert value("(real|none c none (const)) (real|none d (* 2 c))", "d") is None

    def test_a_part_of_none(self):
        assert typ("(point|none p) (real|none d p.x)", "d") == Maybe(REAL)

    def test_a_string_with_a_part_that_is_none(self):
        assert typ("(real|none c) (string|none s $'c = {c:.2f}')", "s") == Maybe(STRING)
        assert value("(real|none c none (const)) (string|none s $'{c}')", "s") is None

    def test_equality(self):
        assert value("(bool b (= none none))", "b") is True
        assert value("(bool b (= none 3))", "b") is False
        assert typ("(real|none c) (bool b (= c 3))", "b") == BOOL

    def test_a_comparison_of_none_is_none(self):
        assert typ("(real|none c) (bool|none b (< c 3))", "b") == Maybe(BOOL)

    def test_if_with_a_none_branch(self):
        model("(bool t) (real|none d (if t 1 none))")
        error("(bool t) (real d (if t 1 none))", "may be none")


class TestConditions:
    def test_a_condition_never_receives_none(self):
        error("(bool|none t) (real d (if t 1 2))", "may be none")
        error("(bool|none t) (bool d (and t true))", "may be none")
        error("(bool|none t) (bool d (not t))", "may be none")


class TestHandling:
    def test_or_default(self):
        assert typ("(real k 1) (real d (or? (/ 1 k) 0))", "d") == REAL
        assert value("(real|none c none (const)) (real d (or? c 5))", "d") == 5

    def test_or_default_range(self):
        model("(scene s (real k 1 (>= 1)) (real|none c 1 (>= 0)) (circle o (r (or? c k))))")

    def test_none_and_some(self):
        assert typ("(real|none c) (bool b (none? c))", "b") == BOOL
        assert value("(bool b (some? none))", "b") is False

    def test_no_narrowing_after_a_test(self):
        error("(real|none c) (real d (if (some? c) (* 2 c) 0))", "may be none")

    def test_somes(self):
        t = typ("(list[real|none] xs [1 none 2]) (list[real] ys (somes xs))", "ys")
        assert t == ListT(REAL)
        assert value("(list[real|none] xs [1 none 2] (const)) (list ys (somes xs))", "ys") == [1, 2]

    def test_somes_takes_a_list(self):
        error("(real k) (list[real] ys (somes k))", "somes takes a list")


class TestLists:
    def test_a_fixed_position_on_a_list_of_known_length(self):
        assert typ("(real k) (real d (. [k 2] 0))", "d") == REAL
        assert typ("(list[real] xs [1 2] (length 2)) (real d xs[1])", "d") == REAL
        error("(list[real] xs [1 2] (length 2)) (real d xs[2])", "out of range")

    def test_a_list_of_unknown_length(self):
        error("(list[real] xs [1 2]) (real d xs[0])", "may be none")

    def test_a_position_known_only_while_drawing(self):
        assert typ("(int i) (real k) (real|none d (. [k 2] i))", "d") == Maybe(REAL)


class TestShapes:
    def test_a_drawing_essential_attribute_may_not_be_none(self):
        error("(scene s (real|none c) (circle o (r (or? c 1)) (x c)))", "may be none")

    def test_a_shape_that_may_be_absent(self):
        m = model("(scene s (real k 1) (circle|none o (r (/ 1 k))))")
        o = m.get("o")
        assert o.type == Maybe(o.type.inner)
        assert o.attrs["r"].type == Maybe(Refine(REAL, ((">=", 0),)))

    def test_reading_a_shape_that_may_be_absent(self):
        error("(scene s (real k 1) (circle|none o (r (/ 1 k))) (circle p (r o.r)))", "may be none")

    def test_fill_and_stroke_accept_none(self):
        model("(scene s (color|none ink) (circle o (fill ink) (stroke none)))")

    def test_a_radius_that_may_break_its_constraint_makes_the_shape_absent(self):
        model("(scene s (real k 1) (circle|none o (r k)))")
        error("(scene s (real k 1) (circle o (r k)))", r"r may break \(>= 0\)")


def test_or_on_a_value_known_when_compiling_is_not_none():
    # mtp-62j: (top 2) is known when compiling, so or? gives it its default only if it is none.
    m = model("(func top ((real k)) (/ 6 k)) (real z (or? (top 2) 0))")
    assert m.get("z").value.value == 3
