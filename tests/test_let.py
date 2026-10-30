import random

import pytest
from helpers import with_scene

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Bound, Circle, Free, Motif, Text, local_names
from mathterpiece.nodes import Form, InterpStrLit, Name


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def get[T](model, name, cls: type[T]) -> T:
    obj = model[name]
    assert isinstance(obj, cls)
    return obj


def n(*parts):
    return Name(tuple(parts))


def hidden(attr) -> str:
    assert isinstance(attr, Bound) and isinstance(attr.expr, Name)
    (name,) = attr.expr.parts
    assert isinstance(name, str)
    return name


class TestInExpressions:
    def test_folds_when_known(self):
        assert get(scene("(circle 'c' (r (let ((h 2)) (* h h))))"), "c", Circle).r == Free(4.0)

    def test_bindings_see_earlier_ones(self):
        c = get(scene("(circle 'c' (r (let ((a 2) (b (* a 3))) b)))"), "c", Circle)
        assert c.r == Free(6.0)

    def test_shadows_a_global(self):
        c = get(scene("(real 'k' 5) (circle 'c' (r (let ((k 1)) k)))"), "c", Circle)
        assert c.r == Free(1.0)

    def test_inner_let_shadows_outer(self):
        c = get(scene("(circle 'c' (r (let ((a 1)) (let ((a 2)) a))))"), "c", Circle)
        assert c.r == Free(2.0)

    def test_bound_value_is_named_once(self):
        c = get(scene("(real 'k' 2) (circle 'c' (r (let ((h (* k 2))) (* h h))))"), "c", Circle)
        assert isinstance(c.r, Bound) and isinstance(c.r.expr, Form)
        _, a, b = c.r.expr.items
        assert a == b and isinstance(a, Name) and a.parts != ("h",)

    def test_bound_value_in_a_string(self):
        t = get(scene("(real 'k' 2) (text 't' (let ((a (* k 2))) $'v={a}'))"), "t", Text)
        assert isinstance(t.value, Bound) and isinstance(t.value.expr, InterpStrLit)
        assert t.value.expr.parts[0] == "v="

    def test_known_value_in_a_string(self):
        t = get(scene("(text 't' (let ((a 2)) $'v={a}'))"), "t", Text)
        assert t.value == Free("v=2")


class TestAroundMembers:
    def test_shared_by_several_objects(self):
        m = scene("(let ((a 2)) (circle 'c' (r a)) (circle 'd' (x a)))")
        assert (get(m, "c", Circle).r, get(m, "d", Circle).x) == (Free(2.0), Free(2.0))
        assert [o.name for o in m.root.members] == ["c", "d"]

    def test_inside_a_group(self):
        m = scene("(group 'g' (let ((a 3)) (circle 'c' (r a))))")
        assert get(m, "c", Circle).r == Free(3.0)

    def test_per_iteration_in_a_repeat(self):
        m = scene("(repeat 3 i (let ((a (* i 10))) (circle $'c{i}' (x a))))")
        assert get(m, "c2", Circle).x == Free(20.0)

    def test_in_an_object_name(self):
        m = scene("(repeat 2 i (let ((j (+ i 1))) (circle $'c{j}')))")
        assert "c1" in m and "c2" in m

    def test_in_a_motif_body(self):
        m = scene(
            "(motif 'dot' (params (r 1.0)) (let ((d (* 2 r))) (circle 'c' (r d)))) (dot 'x' (r 3))"
        )
        c = local_names(get(m, "x", Motif))["c"]
        assert isinstance(c, Circle) and c.r == Free(6.0)

    def test_bound_value_is_the_same_object_for_every_use(self):
        m = scene("(real 'k' 2) (let ((a (* k 3))) (circle 'c' (x a) (y a)) (circle 'd' (r a)))")
        c, d = get(m, "c", Circle), get(m, "d", Circle)
        assert hidden(c.x) == hidden(c.y) == hidden(d.r)

    def test_names_are_gone_after_the_let(self):
        error("(let ((a 1)) (circle 'c')) (circle 'd' (r a))", match="'a'")

    def test_at_the_top_level_around_values_and_canvases(self):
        m = scene("(let ((w 4)) (real 'k' w) (canvas 'cnv' (view-width w)))")
        assert get(m, "k", object) is not None


class TestErrors:
    @pytest.mark.parametrize(
        "expr",
        [
            "(let (a 1) a)",
            "(let ((a)) a)",
            "(let ((a 1 2)) a)",
            "(let ((a 1)))",
            "(let ((a 1)) a a)",
            "(let ((a.b 1)) a)",
            "(let ((1 1)) 1)",
            "(let a a)",
            "(let)",
        ],
    )
    def test_malformed(self, expr):
        error(f"(circle 'c' (r {expr}))")

    def test_values_only(self):
        error("(circle 'a') (circle 'c' (r (let ((b a)) 1)))", match="value")

    def test_no_group_attribute_lists(self):
        error("(group 'g' (circle _)) (circle 'c' (r (let ((rs g.r)) 1)))")

    def test_a_value_has_no_attributes(self):
        error("(circle 'c' (r (let ((a 1)) a.x)))")

    def test_let_is_syntax(self):
        error("(circle 'let')", match="let")
        error("(circle 'c' (r (let ((let 1)) 1)))", match="let")

    def test_cycle_through_a_let(self):
        error("(real 'k') (circle 'c' (x (let ((a (+ k self.x))) a)))", match="circular")


def ev_of(src, seed=0):
    m = scene(src)
    return m, Evaluator(m, random.Random(seed))


class TestEvaluation:
    def test_rand_is_computed_once_and_shared(self):
        m, ev = ev_of("(let ((a (rand))) (circle 'c' (x a) (y a)) (circle 'd' (r a)))")
        c, d = m["c"], m["d"]
        assert ev.value(c, "x") == ev.value(c, "y") == ev.value(d, "r")

    def test_rand_is_new_in_each_iteration(self):
        m, ev = ev_of("(repeat 2 i (let ((a (rand))) (circle $'c{i}' (x a))))")
        assert ev.value(m["c0"], "x") != ev.value(m["c1"], "x")

    def test_rand_in_an_expression(self):
        m, ev = ev_of("(circle 'c' (r (let ((h (rand))) (- h h))))")
        assert ev.value(m["c"], "r") == 0.0

    def test_self_in_an_expression_let(self):
        m, ev = ev_of("(circle 'c' (x 3) (r (let ((h self.x)) (* h 2))))")
        assert ev.value(m["c"], "r") == 6.0

    def test_bound_value(self):
        m, ev = ev_of("(real 'k' 2) (let ((a (* k 3))) (circle 'c' (x a)))")
        assert ev.value(m["c"], "x") == 6.0

    def test_bound_motif_param(self):
        src = (
            "(real 'k' 2.0) (motif 'dot' (params (r 1.0)) (let ((d (* 2 r))) (circle 'c' (r d))))"
            " (dot 'a' (r k)) (dot 'b' (r k))"
        )
        m, ev = ev_of(src)
        for name in ("a", "b"):
            c = local_names(get(m, name, Motif))["c"]
            assert ev.value(c, "r") == 4.0

    def test_string_value(self):
        m, ev = ev_of("(real 'k' 2) (text 't' (let ((a (* k 2))) $'v={a}'))")
        assert ev.value(m["t"], "value") == "v=4.0"
