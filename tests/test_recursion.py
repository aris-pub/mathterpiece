import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import EvalError, Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import RECURSION_LIMIT, Bound, Free, Local, Real

FACT = "(func 'fact' (params (n 0.0)) (if (< n 2) 1 (* n (fact (- n 1)))))"
SUM_TO = "(func 'sum-to' (params (n 0.0)) (if (= n 0) 0 (+ n (sum-to (- n 1)))))"
DOWN = "(func 'down' (params (n 0.0)) (if (< n 0) 0 (down (+ n 1))))"
ESCAPE = (
    "(func 'escape' (params (z 0+0i) (c 0+0i) (k 0))"
    "  (cond ((> (abs z) 2) k) ((>= k 50) k) (else (escape (+ (* z z) c) c (+ k 1)))))"
)


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def value_of(src):
    v = scene(src)["v"]
    assert isinstance(v, Real)
    return v.value


def evaluated(src, seed=0):
    m = scene(src)
    return Evaluator(m, random.Random(seed)).value(m["v"], "value")


class TestCompileTime:
    def test_limit_is_like_pythons(self):
        assert RECURSION_LIMIT == 1000

    def test_folds_when_arguments_are_known(self):
        assert value_of(f"{FACT} (real 'v' (fact 5))") == Free(120.0)

    def test_deep_but_within_the_limit(self):
        assert value_of(f"{SUM_TO} (real 'v' (sum-to 900))") == Free(405450.0)

    def test_too_deep(self):
        error(f"{DOWN} (real 'v' (down 0))", match="1000")

    def test_bound_argument_keeps_the_call(self):
        assert isinstance(value_of(f"(real 'k' 5) {FACT} (real 'v' (fact k))"), Bound)

    def test_result_type_is_worked_out(self):
        error(f"{FACT} (text 't' (fact 3))", match="real")

    def test_no_result_without_a_base_case(self):
        error("(func 'f' (params (n 0)) (f n)) (real 'v' (f 1))", match="what 'f' returns")

    def test_escape_time(self):
        assert value_of(f"{ESCAPE} (real 'v' (escape 0 1))") == Free(3.0)
        assert value_of(f"{ESCAPE} (real 'v' (escape 0 -1))") == Free(50.0)

    def test_abs(self):
        assert value_of("(real 'v' (abs 3-4i))") == Free(5.0)
        assert value_of("(real 'v' (abs -2))") == Free(2.0)


class TestWhileDrawing:
    def test_bound_argument(self):
        assert evaluated(f"(real 'k' 5) {FACT} (real 'v' (fact k))") == 120

    def test_deep_but_within_the_limit(self):
        assert evaluated(f"(real 'k' 900) {SUM_TO} (real 'v' (sum-to k))") == 405450

    def test_too_deep(self):
        with pytest.raises(EvalError, match="1000"):
            evaluated(f"(real 'k' 0) {DOWN} (real 'v' (down k))")

    def test_escape_time(self):
        assert evaluated(f"(real 'k' 1) {ESCAPE} (real 'v' (escape 0 k))") == 3

    def test_let_in_a_body_is_per_call(self):
        src = "(func 'f' (params (x 0.0)) (let ((y (* x 2))) (+ y y))) (real 'k' 3)"
        m = scene(f"{src} (real 'v' (+ (f k) (f 1)))")
        assert Evaluator(m, random.Random(0)).value(m["v"], "value") == 16
        assert not any(isinstance(o, Local) for o in m)

    def test_rand_in_a_body_is_drawn_per_call(self):
        src = "(func 'noisy' (params (x 0.0)) (+ x (rand))) (real 'v' (- (noisy 0) (noisy 0)))"
        assert isinstance(value_of(src), Bound)
        assert evaluated(src) != 0

    def test_a_function_that_hides_a_library_one_only_counts_after_it(self):
        src = (
            "(real 'k' 3) (real 'early' (dist 0 0 k 0))"
            " (func 'dist' (params (x 0.0)) (* 2 x)) (real 'v' (dist k))"
        )
        m = scene(src)
        ev = Evaluator(m, random.Random(0))
        assert (ev.value(m["early"], "value"), ev.value(m["v"], "value")) == (3.0, 6.0)
