"""Folding: whatever is known when compiling is written as a plain value (docs/data-model.md
"Two properties of every expression"; docs/mtpc.md "Everything known when compiling is
already folded")."""

import pytest

from mathterpiece.compiler import CompileError, compile_source

DOUBLE = "(func double (real x) (* 2 x))"
FACT = "(func fact (int n) (if (<= n 1) 1 (* n (fact (- n 1)))))"


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def value(src, name):
    place = model(src).get(name).value
    assert not place.bound, f"{name} is not known when compiling"
    return place.value


class TestCalls:
    def test_a_call_with_known_arguments(self):
        assert value(f"{DOUBLE} (real k (double 3))", "k") == 6

    def test_recursion(self):
        assert value(f"{FACT} (int k (fact 5))", "k") == 120

    def test_a_call_with_an_argument_known_only_while_drawing(self):
        assert model(f"{DOUBLE} (real j) (real k (double j))").get("k").value.bound

    def test_a_body_that_reads_a_const_variable(self):
        assert value("(real c 3 (const)) (func f (real x) (* c x)) (real k (f 2))", "k") == 6

    def test_a_body_that_reads_a_free_variable(self):
        src = "(real c 3) (func f (real x) (* c x)) (real k (f 2))"
        assert model(src).get("k").value.bound

    def test_known_inputs_where_the_function_is_undefined(self):
        error("(func f (real x) (/ 1 x)) (real|none d (f 0))", "division by zero")

    def test_functions_as_arguments(self):
        src = f"{DOUBLE} (func twice ((func[real real] f) (real x)) (f (f x)))"
        assert value(f"{src} (real k (twice double 3))", "k") == 12
        assert value(f"{src} (real k (twice (fn y (+ y 1)) 3))", "k") == 5

    def test_too_deep_to_fold_stays_a_call(self):
        src = "(func down (int n) (if (<= n 0) 0 (down (- n 1)))) (int k (down 100000))"
        assert model(src).get("k").value.bound

    def test_folding_adds_no_functions(self):
        src = f"{DOUBLE} (real k (double 3))"
        assert len(model(src).functions) == 1


class TestCollections:
    def test_map(self):
        assert value(f"{DOUBLE} (list ys (map [1 2] double))", "ys") == [2, 4]
        assert value("(list ys (map [1 2] (fn x (* x x))))", "ys") == [1, 4]

    def test_where_sort_count_reduce(self):
        assert value("(list ys (where [3 1 2] (fn x (> x 1))))", "ys") == [3, 2]
        assert value("(list ys (sort [3 1 2] (fn x (- 0 x))))", "ys") == [3, 2, 1]
        assert value("(int n (count [3 1 2] (fn x (> x 1))))", "n") == 2
        assert value("(int n (reduce [1 2 3] 0 (fn ((int t) (int x)) (+ t x))))", "n") == 6
        assert value("(bool b (all [1 2] (fn x (> x 0))))", "b") is True

    def test_a_captured_known_name(self):
        assert value("(list ys (let ((k 10)) (map [1 2] (fn x (* k x)))))", "ys") == [10, 20]


class TestFoldedPlaces:
    # docs/mtpc.md "Places": a place known when compiling is free with a const constraint,
    # whether the author wrote (const) or the compiler folded it. A place given by an expression
    # is bound, so nothing may write it (data-model.md, "What changes, and what follows").
    def test_a_folded_expression_is_const(self):
        from mathterpiece.compiler import _is_const

        m = model("(real k 1) (real d (+ 1 2))")
        assert not _is_const(m.get("k").value.type)
        assert _is_const(m.get("d").value.type)

    def test_so_no_writer_can_write_it(self):
        error("(real d (+ 1 2)) (animation a (d (transition (to 1) (duration 1))))", "d is const")

    def test_a_literal_list_is_still_free(self):
        from mathterpiece.compiler import _is_const

        assert not _is_const(model("(list xs [1 2])").get("xs").value.type)


def test_a_parameters_default_is_known_when_compiling():
    error("(real k) (func f (real x k) x)", "a parameter's default must be known when compiling")
