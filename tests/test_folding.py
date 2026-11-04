"""Folding: whatever is known when compiling is written as a plain value (docs/data-model.md
"Two properties of every expression"; docs/mtpc.md "Everything known when compiling is
already folded")."""

import pytest
from helpers import error, model, value

DOUBLE = "(func double (real x) (* 2 x))"
FACT = "(func fact (int n) (if (<= n 1) 1 (* n (fact (- n 1)))))"


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


class TestFoldedValues:
    # docs/mtpc.md "Free and bound values": a variable or an attribute given a constant (the bare
    # name of a const variable or of a built-in constant) is free, starting at its value, as if
    # the author had written that value. Any other expression known when compiling is folded and
    # free with a const constraint, so no writer can write it.
    def test_a_folded_expression_is_const(self):
        from mathterpiece.compiler import _is_const

        m = model("(real k 1) (real d (+ 1 2))")
        assert not _is_const(m.get("k").value.type)
        assert _is_const(m.get("d").value.type)

    def test_so_no_writer_can_write_it(self):
        error("(real d (+ 1 2)) (animation a (move d (to 1) (duration 1)))", "d is const")

    def test_a_constant_gives_a_free_value(self):
        from mathterpiece.compiler import _is_const

        m = model("(real g 137.5 (const)) (real a g) (real b pi)")
        for name in "ab":
            attribute = m.get(name).value
            assert not attribute.bound and not _is_const(attribute.type)
        assert m.get("a").value.value == 137.5

    def test_a_const_attribute_is_a_constant(self):
        # c.r is const, so d.r folds to a plain 2 that the move may write.
        m = model(
            "(scene s (circle c (r (+ 1 1))) (circle d (r c.r)))"
            " (animation a (move d.r (to 1) (duration 1)))"
        )
        r = m.get("d").attrs["r"]
        assert not r.bound and r.value == 2
        assert m.get("a").data["steps"][1] == (m.id("d"), "r")

    def test_so_a_writer_may_write_it(self):
        m = model(
            "(real g (* 180 (- 3 (sqrt 5))) (const))"
            " (scene s (circle c (r g)))"
            " (animation a (move c.r (to 1) (duration 1)))"
        )
        r = m.get("c").attrs["r"]
        assert not r.bound and r.value == pytest.approx(180 * (3 - 5**0.5))
        assert m.get("a").data["steps"][1] == (m.id("c"), "r")

    def test_an_expression_of_a_constant_is_still_const(self):
        src = "(real g 2 (const)) (real d (* 2 g))"
        src += " (animation a (move d (to 1) (duration 1)))"
        error(src, "d is const")

    def test_a_literal_list_is_still_free(self):
        from mathterpiece.compiler import _is_const

        assert not _is_const(model("(list xs [1 2])").get("xs").value.type)


def test_a_parameters_default_is_known_when_compiling():
    error("(real k) (func f (real x k) x)", "a parameter's default must be known when compiling")


class TestWorkDoneOnce:
    """A plain list takes its item type from its value, but that value is worked out once: before
    mtp-9i9y it was folded a second time, which doubled the time to compile."""

    @pytest.fixture
    def folds(self, monkeypatch):
        from mathterpiece.compiler import _Compiler

        counts: dict = {}
        fold_call = _Compiler.fold_call

        def counted(self, fid, args):
            name = self.model.functions[fid].name
            counts[name] = counts.get(name, 0) + 1
            return fold_call(self, fid, args)

        monkeypatch.setattr(_Compiler, "fold_call", counted)
        return counts

    def test_a_plain_list(self, folds):
        src = f"{DOUBLE} (list ys (map [1 2 3] double))"
        src += " (scene s (foreach y ys (circle_ (r y))))"
        assert value(src, "ys") == [2, 4, 6]
        assert folds["double"] == 3

    def test_a_plain_list_with_a_constraint(self, folds):
        assert value(f"{DOUBLE} (list ys (map [1 2 3] double) (const))", "ys") == [2, 4, 6]
        assert folds["double"] == 3
        error(f"{DOUBLE} (list ys (map [1 2 3] double) (length 2))", "breaks")

    def test_a_plain_list_in_a_motif_body(self, folds):
        src = f"{DOUBLE} (motif m (real k 1) (list ys (map [1 2 3] double)) (circle c (r 1)))"
        model(src + " (scene s (m a))")
        one = folds.pop("double")
        model(src + " (scene s (m a) (m b))")
        # Each instance works out its body once, so another instance adds three calls.
        assert folds["double"] - one == 3

    def test_a_plain_list_as_a_default(self, folds):
        model(f"{DOUBLE} (func f (list ys (map [1 2 3] double)) (count ys)) (int n (f))")
        assert folds["double"] == 3

    def test_a_motif_parameters_default(self, folds):
        src = f"{DOUBLE} (motif m (list ys (map [1 2 3] double)) (circle c (r 1)))"
        model(src + " (scene s (m a) (m b))")
        assert folds["double"] == 3


class TestKeptFolds:
    """A named function's folded calls are kept, so a call made again is not folded again
    (mtp-pffq). A kept value is used only where the call would fold to that same value."""

    @pytest.fixture
    def bodies(self, monkeypatch):
        """How many times each function's body is compiled to fold a call."""
        from mathterpiece.compiler import _Compiler

        counts: dict = {}
        fold_key = _Compiler.fold_key

        def counted(self, fid, f, args):
            key = fold_key(self, fid, f, args)
            if key is None or key not in self.folded:
                counts[f.name] = counts.get(f.name, 0) + 1
            return key

        monkeypatch.setattr(_Compiler, "fold_key", counted)
        return counts

    def test_a_call_made_again_is_not_folded_again(self, bodies):
        src = f"{DOUBLE} (real a (double 3)) (real b (double 3)) (real c (double 4))"
        m = model(src)
        assert [m.get(n).value.value for n in "abc"] == [6, 6, 8]
        assert bodies["double"] == 2

    def test_the_same_value_of_another_type(self):
        src = "(func t (real x) (type-of x)) (int i 3 (const)) (real r 3 (const))"
        m = model(f"{src} (string a (t i)) (string b (t r))")
        assert m.get("a").value.value == "(int (const))"
        assert m.get("b").value.value == "(real (const))"

    def test_zero_and_minus_zero(self):
        src = "(func f (real x) $'{x}') (real z 0.0 (const)) (real n (- 0.0) (const))"
        m = model(f"{src} (string a (f z)) (string b (f n))")
        assert (m.get("a").value.value, m.get("b").value.value) == ("0.0", "-0.0")

    def test_a_name_a_motif_body_gives_another_meaning(self):
        # Inside the motif, pi in f's body is the motif's parameter.
        src = "(func f (real x) (* x pi)) (real a (f 2))"
        src += " (motif m (real pi 5 (const)) (circle c (r (f 2)))) (scene s (m one))"
        m = model(src)
        assert m.get("a").value.value == pytest.approx(6.283185307179586)
        circle = next(o for o in m.objects if o.name == "c")
        assert circle.attrs["r"].value == 10

    def test_a_fn_is_not_kept(self, bodies):
        # Each fn gets a new id, and an id is used again once a fold deletes its fn.
        model("(list ys (map [1 1 1] (fn x (* x 2))))")
        assert bodies[None] == 3
