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


class TestReadsThroughFunctionValues:
    # mtp-59e: what a function passed as a value reads through a shape it is given counts as a
    # read of the call, so the call is recomputed when it changes.
    C = "(scene sc (circle c (r 2)) (group g (circle d (r 1)) (circle e (r 3))))"

    def deps(self, src):
        m = model(f"{self.C} {src}")
        return m, bound(f"{self.C} {src}", "v").deps

    def test_a_fn_given_to_a_function_that_applies_it(self):
        m, deps = self.deps(
            "(func app ((func[circle real] f) (circle s)) (f s)) (real v (app (fn p p.r) c))"
        )
        assert (m.id("c"), "r") in deps

    def test_a_named_function_given_as_a_value(self):
        m, deps = self.deps(
            "(func rad ((circle p)) p.r)"
            " (func app ((func[circle real] f) (circle s)) (f s)) (real v (app rad c))"
        )
        assert (m.id("c"), "r") in deps

    def test_a_function_bound_with_let(self):
        m, deps = self.deps("(real k 1) (real v (let ((f (fn ((circle p)) (* k p.r)))) (f c)))")
        assert {(m.id("c"), "r"), (m.id("k"), None)} <= deps

    def test_items_of_a_group_given_with_the_function(self):
        m, deps = self.deps(
            "(func app ((func[circle real] f) (sequence[circle] s)) (sum (map s (fn q (f q)))))"
            " (real v (app (fn p p.r) g))"
        )
        assert {(m.id("d"), "r"), (m.id("e"), "r")} <= deps


class TestDeclaredResults:
    # mtp-gn4: (func[T] name params body) declares the result's type; the compiler proves the body
    # fits it, and every call has that type and range.
    def test_a_call_has_the_declared_range(self):
        m = model(
            "(func[(real (>= 0) (<= 1))] near ((real x)) (/ (+ (sind x) 1) 2))"
            " (real k) (scene s (circle c (opacity (near k))))"
        )
        f = m.functions[m.funcs["near"]]
        assert f.result.constraints == ((">=", 0), ("<=", 1))

    def test_without_it_the_call_may_break_a_constraint(self):
        error(
            "(func near ((real x)) (* 2 x)) (real k 0 (>= 0) (<= 1))"
            " (scene s (circle c (opacity (near (/ k 2)))))",
            "may break",
        )

    def test_the_body_must_be_proved_to_fit(self):
        error(
            "(func[(real (>= 0) (<= 1))] f ((real x)) (* 2 x))",
            "f's result may break \\(>= 0\\)",
        )

    def test_the_body_must_have_the_type(self):
        error("(func[bool] f ((real x)) (* 2 x))", "expected bool")

    def test_the_declared_type_reaches_a_literal_in_the_body(self):
        m = model("(func[point] f ((real x)) [x 0]) (real k) (point p (f k))")
        assert m.get("p").value.bound

    def test_a_folded_call_has_the_declared_type(self):
        assert model("(func[point] f ((real x)) [x 0]) (point p (f 2))").get("p").value.value == (
            2,
            0,
        )

    def test_a_recursive_function_with_a_declared_result(self):
        m = model(
            "(func[point] f ((int n)) (if (<= n 0) [0 0] (let ((r (f (- n 1)))) [(+ r.x 1) r.y])))"
            " (point q (f 3))"
        )
        assert tuple(m.get("q").value.value) == (3, 0)

    def test_a_result_that_may_be_none_is_checked(self):
        nn = "(type nonneg real (>= 0)) (func[nonneg|none] f ((real x)) x)"
        m = model(f"{nn} (real|none a (f 2)) (real|none b (f -2))")
        assert (m.get("a").value.value, m.get("b").value.value) == (2, None)
        m = model(f"{nn} (real k) (real|none a (f k))")
        assert m.functions[m.funcs["f"]].body.op == "check"

    def test_only_at_the_top_level(self):
        error("(scene s (func[real] f ((real x)) x))", "declared only at the top level")
