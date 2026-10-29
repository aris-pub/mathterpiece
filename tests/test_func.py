import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Bound, Circle, Free, Motif, Real, local_names
from mathterpiece.nodes import Form, IntLit, Name, RealLit

SQ = "(func 'sq' (params (x 0.0)) (* x x))"
GAP = "(func 'gap' (params (a) (b)) (- (dist a b) a.r b.r))"


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def n(*parts):
    return Name(tuple(parts))


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


def value_of(src):
    return get(scene(src), "v", Real).value


class TestCalls:
    def test_folds_when_arguments_are_known(self):
        assert get(scene(f"{SQ} (circle 'c' (r (sq 3)))"), "c", Circle).r == Free(9.0)

    def test_defaults_fill_missing_arguments(self):
        assert value_of("(func 'f' (params (x 0.0) (y 2.0)) (+ x y)) (real 'v' (f 1))") == Free(3.0)

    def test_optional_argument_left_out(self):
        assert value_of(f"{SQ} (real 'v' (sq))") == Free(0.0)

    def test_no_parameters(self):
        assert value_of("(func 'one' 1) (real 'v' (one))") == Free(1.0)

    def test_argument_types_widen(self):
        assert value_of(f"{SQ} (real 'v' (sq 1/2))") == Free(0.25)

    def test_body_sees_consts(self):
        assert value_of(
            "(const 'g' 2) (func 'f' (params (x 0.0)) (* g x)) (real 'v' (f 3))"
        ) == Free(6.0)

    def test_body_sees_builtins(self):
        assert isinstance(value_of("(func 'f' (params (x 0.0)) (* pi x)) (real 'v' (f 1))"), Bound)

    def test_calls_an_earlier_function(self):
        assert value_of(
            f"{SQ} (func 'quad' (params (x 0.0)) (sq (sq x))) (real 'v' (quad 2))"
        ) == Free(16.0)

    def test_hides_a_standard_library_function(self):
        assert value_of("(func 'dist' (params (a 0.0)) (* 2 a)) (real 'v' (dist 3))") == Free(6.0)

    def test_let_in_the_body(self):
        src = "(func 'f' (params (x 0.0)) (let ((y (* x 2))) (+ y y))) (real 'v' (f 3))"
        assert value_of(src) == Free(12.0)

    def test_in_a_motif_body(self):
        m = scene(f"{SQ} (motif 'dot' (params (r 1.0)) (circle 'c' (r (sq r)))) (dot 'd' (r 3))")
        c = local_names(get(m, "d", Motif))["c"]
        assert isinstance(c, Circle) and c.r == Free(9.0)

    def test_with_a_loop_variable(self):
        assert get(
            scene(f"{SQ} (repeat i 3 (circle $'c{{i}}' (r (sq i))))"), "c2", Circle
        ).r == Free(4.0)


class TestBoundArguments:
    def test_bound_argument_keeps_the_call(self):
        v = value_of(f"(real 'k' 2) {SQ} (real 'v' (sq k))")
        assert v == Bound(Form((n("sq"), n("k"))))

    def test_object_arguments_keep_the_call(self):
        v = value_of(f"{GAP} (circle 'p') (circle 'q' (x 5)) (real 'v' (gap p q))")
        assert v == Bound(Form((n("gap"), n("p"), n("q"))))

    def test_self_as_an_argument(self):
        src = "(func 'twice-x' (params (o)) (* 2 o.x)) (circle 'c' (x 3) (r (twice-x self)))"
        assert get(scene(src), "c", Circle).r == Bound(Form((n("twice-x"), n("self"))))

    def test_indexed_object_argument(self):
        src = (
            "(func 'radius-of' (params (o)) o.r) (group 'g' (circle _ (r 1)) (circle _ (r 2)))"
            " (repeat i 2 (circle $'c{i}' (x (radius-of g[i]))))"
        )
        x = get(scene(src), "c1", Circle).x
        assert x == Bound(Form((n("radius-of"), Name(("g", IntLit(1))))))

    def test_the_model_holds_the_functions(self):
        m = scene(f"(const 'g' 2.0) (func 'f' (params (x 0.0)) (* g x)) {SQ}")
        assert set(m.functions) == {"f", "sq"}
        assert m.functions["f"].body == Form((n("*"), RealLit(2.0), n("x")))


class TestErrors:
    @pytest.mark.parametrize(
        "src, match",
        [
            (f"{GAP} (circle 'p') (real 'v' (gap p))", "'b'"),
            (f"{SQ} (real 'v' (sq 1 2))", None),
            (f"{SQ} (real 'v' (sq 'a'))", None),
            ("(func 'f' (params (n 1)) n) (real 'v' (f 2.5))", None),
            (f"{GAP} (circle 'p') (real 'v' (gap p 1))", None),
            (f"{SQ} (circle 'p') (real 'v' (sq p))", None),
            ("(real 'k' 2) (func 'f' (params (x 0.0)) (* k x))", "'k'"),
            ("(func 'f' (params (x 0.0)) (f x))", "what 'f' returns"),
            ("(func 'f' (params (x 0.0)) (+ x 'a'))", None),
            ("(func 'f' (params (x 0.0)) x x)", "one"),
            ("(func 'f' (params (x 0.0)))", None),
            ("(func 'f')", None),
            ("(func f 1)", None),
            ("(func 'if' 1)", "if"),
            ("(func 'func' 1)", "func"),
            ("(circle 'func')", "func"),
            ("(func 'circle' 1)", "circle"),
            ("(motif 'm' (circle 'c')) (func 'm' 1)", "'m'"),
            ("(func 'f' 1) (motif 'f' (circle 'c'))", "'f'"),
            ("(func 'f' 1) (func 'f' 2)", "'f'"),
            ("(scene _ (func 'f' 1))", None),
            ("(motif 'm' (func 'f' 1))", None),
            ("(func 'f' (params (x 0.0) (x 1.0)) x)", "'x'"),
            ("(func 'f' (params (x (rand))) x)", None),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


def evaluated(src):
    m = scene(src)
    return Evaluator(m, random.Random(0)).value(m["v"], "value")


class TestEvaluation:
    def test_reacts_to_bound_arguments(self):
        assert evaluated(f"(real 'k' 3.0) {SQ} (real 'v' (sq k))") == 9.0

    def test_random_argument_is_computed_once(self):
        assert evaluated("(func 'zero' (params (x 0.0)) (- x x)) (real 'v' (zero (rand)))") == 0.0

    def test_object_arguments(self):
        assert evaluated(f"{GAP} (circle 'p') (circle 'q' (x 5)) (real 'v' (gap p q))") == 3.0

    def test_two_calls_with_lets_in_one_expression(self):
        src = (
            "(real 'k' 1) (func 'f' (params (x 0.0)) (let ((y (* x 2))) (+ y y)))"
            " (real 'v' (+ (f k) (f 2)))"
        )
        assert evaluated(src) == 12.0
