import math
import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Bound, Circle, Free, Group, Motif, Real, Text, local_names
from mathterpiece.nodes import Form, IntLit, Name


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


def member[T](motif, name, cls: type[T]) -> T:
    obj = local_names(motif)[name]
    assert isinstance(obj, cls)
    return obj


class TestConst:
    def test_folds(self):
        assert get(scene("(const 'g' 2) (circle 'c' (r g))"), "c", Circle).r == Free(2.0)

    def test_computed_from_an_expression(self):
        c = get(scene("(const 'g' (* 180 (- 3 (sqrt 5)))) (circle 'c' (r g))"), "c", Circle)
        assert c.r == Free(pytest.approx(180 * (3 - math.sqrt(5))))

    def test_uses_an_earlier_const(self):
        c = get(scene("(const 'a' 2) (const 'b' (* a 3)) (circle 'c' (r b))"), "c", Circle)
        assert c.r == Free(6.0)

    def test_strings_and_bools(self):
        src = "(const 'gold' '#f6c453') (const 'on' true) (circle 'c' (fill (if on gold 'red')))"
        assert get(scene(src), "c", Circle).fill == Free("#f6c453ff")

    def test_visible_in_a_motif_body(self):
        m = scene("(const 'g' 137.5) (motif 'dot' (circle 'c' (x g))) (dot 'd')")
        assert member(get(m, "d", Motif), "c", Circle).x == Free(137.5)

    def test_in_a_parameter_default(self):
        m = scene("(const 'g' 2.0) (motif 'dot' (params (r g)) (circle 'c' (r r))) (dot 'd')")
        assert member(get(m, "d", Motif), "c", Circle).r == Free(2.0)

    def test_written_into_bound_expressions(self):
        c = get(scene("(const 'g' 2) (real 'k' 1) (circle 'c' (r (* g k)))"), "c", Circle)
        assert c.r == Bound(Form((Name(("*",)), IntLit(2), Name(("k",)))))

    def test_in_strings(self):
        assert get(scene("(const 'g' 2) (text 't' $'g={g}')"), "t", Text).value == Free("g=2")

    def test_as_a_repeat_count(self):
        m = scene("(const 'n' 3) (group 'g' (repeat n i (circle _)))")
        assert len(get(m, "g", Group).members) == 3

    def test_in_an_object_name(self):
        assert "c7" in scene("(const 'k' 7) (circle $'c{k}')")

    def test_not_in_the_model(self):
        assert "g" not in scene("(const 'g' 2)")

    def test_hides_a_builtin(self):
        m = scene("(const 'pi' 3) (circle 'c' (r pi)) (circle 'd' (r tau))")
        assert get(m, "c", Circle).r == Free(3.0)
        assert isinstance(m["tau"], Real)


class TestShadowing:
    def test_by_let(self):
        c = get(scene("(const 'g' 2) (circle 'c' (r (let ((g 5)) g)))"), "c", Circle)
        assert c.r == Free(5.0)

    def test_by_a_parameter(self):
        m = scene("(const 'r' 9.0) (motif 'dot' (params (r 1.0)) (circle 'c' (r r))) (dot 'd')")
        assert member(get(m, "d", Motif), "c", Circle).r == Free(1.0)

    def test_by_a_bound_parameter(self):
        src = "(real 'k') (const 'r' 9.0) (motif 'dot' (params (r 1.0)) (circle 'c' (r r)))"
        m = scene(src + " (dot 'd' (r k))")
        assert member(get(m, "d", Motif), "c", Circle).r == Bound(Name(("r",)))

    def test_by_a_member(self):
        src = "(const 'c' 2) (motif 'dot' (circle 'c') (circle 'e' (r c.r))) (dot 'd')"
        e = member(get(scene(src), "d", Motif), "e", Circle)
        assert e.r == Bound(Name(("c", "r")))


class TestErrors:
    @pytest.mark.parametrize(
        "src, match",
        [
            ("(real 'k') (const 'g' k)", "compile time"),
            ("(const 'g' (rand))", "compile time"),
            ("(circle 'c') (const 'g' c)", None),
            ("(const 'a' 1) (circle 'a')", "'a'"),
            ("(circle 'a') (const 'a' 1)", "'a'"),
            ("(const 'a' 1) (const 'a' 2)", "'a'"),
            ("(const 'a' 1) (real 'a')", "'a'"),
            ("(scene _ (const 'g' 1))", "outside the scene"),
            ("(const 'g' 1) (circle 'c' (r g.x))", "g"),
            ("(circle 'c' (r g)) (const 'g' 1)", "'g'"),
            ("(const 'g')", None),
            ("(const g 1)", None),
            ("(const 'g' 1 2)", None),
            ("(const 'if' 1)", "if"),
            ("(const 'const' 1)", "const"),
            ("(motif 'dot' (const 'g' 1))", None),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestLerp:
    @pytest.mark.parametrize(
        "expr, value",
        [
            ("(lerp 0 10 0.25)", 2.5),
            ("(lerp 2 4 0)", 2.0),
            ("(lerp 2 4 1)", 4.0),
            ("(lerp 1 3 2)", 5.0),
        ],
    )
    def test_folded(self, expr, value):
        assert get(scene(f"(real 'v' {expr})"), "v", Real).value == Free(value)

    def test_bound(self):
        v = get(scene("(real 'k') (real 'v' (lerp 0 10 k))"), "v", Real).value
        assert isinstance(v, Bound)

    @pytest.mark.parametrize("expr", ["(lerp 0 1)", "(lerp 0 1 2 3)", "(lerp 'a' 1 0.5)"])
    def test_invalid(self, expr):
        error(f"(real 'v' {expr})")

    def test_evaluated(self):
        m = scene("(real 'k' 0.5) (real 'v' (lerp 2 6 k))")
        assert Evaluator(m, random.Random(0)).value(m["v"], "value") == 4.0
