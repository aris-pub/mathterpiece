"""Functions: func, calls, recursion, functions as values and fn (docs/syntax.md section 5;
docs/type-system.md sections 2 and 5.a; docs/mtpc.md "Functions")."""

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import INT, REAL, FuncT, Maybe


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def bound(src, name):
    attribute = model(src).get(name).value
    assert attribute.bound
    return attribute.expr


class TestDeclaring:
    def test_a_function_and_its_inferred_result(self):
        m = model("(func double (real x) (* 2 x))")
        f = m.functions[m.funcs["double"]]
        assert [p.name for p in f.params] == ["x"]
        assert f.result == REAL

    def test_several_parameters_and_defaults(self):
        m = model("(func hyp ((real a) (real b 0)) (+ (* a a) (* b b)))")
        assert m.functions[m.funcs["hyp"]].params[1].default is not None

    def test_no_parameters(self):
        assert model("(func one () 1)").functions[0].result == INT

    def test_parameters_are_typed(self):
        error("(func f (x) x)", "expected a parameter such as")

    def test_names_are_unique(self):
        error("(real f 1) (func f (real x) x)", "'f' is already declared")

    def test_the_body_is_checked_at_the_definition(self):
        error("(func f (real x) (+ x 'a'))", "takes numbers")


class TestCalls:
    def test_a_call(self):
        e = bound("(func double (real x) (* 2 x)) (real k 1) (real d (double k))", "d")
        assert e.op == "call"
        assert e.type == REAL

    def test_defaults_are_filled_in(self):
        m = model("(func f ((real a) (real b 5)) (+ a b)) (real k 1) (real d (f k))")
        assert len(m.get("d").value.expr.args) == 3

    def test_too_many(self):
        error("(func f (real a) a) (real d (f 1 2))", "f takes 1 argument")
        error("(func f ((real a) (real b)) a) (real d (f 1 2 3))", "f takes 2 arguments")

    def test_one_left_out_takes_its_types_value(self):
        # reference.md "Defaults": a parameter without a default that a call leaves out.
        m = model("(func f ((real a) (real b)) (+ a b)) (real d (f))")
        assert m.get("d").value.value == 0

    def test_argument_types(self):
        error("(func f (real a) a) (real d (f 'x'))", "expected real, got string")

    def test_a_constrained_parameter_needs_a_proof(self):
        src = "(func f (real a (>= 0)) a)"
        model(f"{src} (real k 1 (>= 1)) (real d (f k))")
        error(f"{src} (real k 1) (real d (f k))", r"may break \(>= 0\)")
        error(f"{src} (real d (f -1))", r"-1 breaks \(>= 0\)")

    def test_an_argument_that_may_be_none_makes_the_call_none(self):
        src = "(func f (real a) a) (real|none c)"
        assert bound(f"{src} (real|none d (f c))", "d").type == Maybe(REAL)

    def test_a_parameter_that_accepts_none(self):
        src = "(func f (real|none a) (or? a 0)) (real|none c)"
        assert bound(f"{src} (real d (f c))", "d").type == REAL

    def test_what_the_body_reads_is_a_dependency(self):
        m = model("(real k 1) (func f (real a) (* k a)) (real j 2) (real d (f j))")
        assert m.get("d").value.deps == {(m.id("k"), None), (m.id("j"), None)}

    def test_reads_in_a_body_are_in_the_callers_frame(self):
        m = model("(scene s (circle p)) (func f (real a) (+ a p.x))")
        body = m.functions[m.funcs["f"]].body
        read = body.args[1]
        assert read.args == (m.id("p"), "x", "caller")


class TestRecursion:
    def test_through_the_branch_that_does_not_recurse(self):
        m = model("(func fact (int n) (if (<= n 1) 1 (* n (fact (- n 1)))))")
        assert m.functions[m.funcs["fact"]].result == INT

    def test_no_base_case(self):
        error("(func f (int n) (f n))", "no base case")


class TestFunctionsAsValues:
    def test_a_parameter_that_takes_a_function(self):
        src = "(func double (real x) (* 2 x)) (func twice ((func[real real] f) (real x)) (f (f x)))"
        m = model(src)
        assert m.functions[m.funcs["twice"]].result == REAL
        e = bound(f"{src} (real k) (real d (twice double k))", "d")
        assert e.args[1].op == "func"
        assert e.args[1].type == FuncT((REAL,), REAL)

    def test_a_function_that_does_not_fit(self):
        src = "(func twice ((func[real real] f) (real x)) (f x)) (func g ((real a) (real b)) a)"
        error(f"{src} (real d (twice g 1))", "expected func")

    def test_fn_in_place(self):
        src = "(func twice ((func[real real] f) (real x)) (f x)) (real k 2)"
        e = bound(f"{src} (real d (twice (fn y (* k y)) 1))", "d")
        assert e.args[1].op == "func"

    def test_fn_needs_where_it_is_used_to_type_a_bare_parameter(self):
        error("(real k (let ((f (fn y y))) 1))", "needs its type")

    def test_variables_never_hold_functions(self):
        error(
            "(func double (real x) (* 2 x)) (func[real real] f double)",
            "a variable cannot hold a function",
        )


class TestRecursiveResults:
    # mtp-1jo: inside a recursive function, its own call's result has the type of its other
    # branches.
    def test_reading_the_result_of_the_recursive_call(self):
        m = model(
            "(func f ((int n)) (if (<= n 0) (as point [0 0])"
            " (let ((r (f (- n 1)))) (as point [(+ r.x 1) r[1]]))))"
            " (point q (f 3))"
        )
        assert tuple(m.get("q").value.value) == (3, 0)
