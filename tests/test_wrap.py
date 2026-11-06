"""Values that wrap (mtp-y2d; docs/type-system.md, 5.b). The author, 2026-11-06: (wrap lo hi) is
a constraint on an int, a ratio or a real, never beside a comparison; a value entering a type that
wraps is brought into [lo, hi) instead of being refused: a literal, a bound value, a function's
argument and result, and every write while drawing; a move goes through the numbers as written,
each value it writes brought in. Modular arithmetic is built on top, with named types and
functions."""

from fractions import Fraction

import pytest
from helpers import doc, error, model
from mtpc_check import errors


def held(src, name="v"):
    return model(src).get(name).value


class TestDeclaring:
    @pytest.mark.parametrize(
        "src, want",
        [
            ("(real v 400 (wrap 0 360))", 40),
            ("(real v -30 (wrap 0 360))", 330),
            ("(real v 360 (wrap 0 360))", 0),
            ("(int v 13 (wrap 0 12))", 1),
            ("(ratio v 7/3 (wrap 0 1))", Fraction(1, 3)),
            ("(real v (wrap 1 13))", 12),
        ],
    )
    def test_a_value_is_brought_into_the_interval(self, src, want):
        assert held(src).value == want

    def test_as_a_named_type(self):
        assert held("(type angle real (wrap 0 360)) (angle v 725)").value == 5

    @pytest.mark.parametrize(
        "src, msg",
        [
            ("(real v 1 (wrap 0 360) (>= 0))", "takes no"),
            ("(real v 1 (wrap 0 1) (wrap 0 2))", "once"),
            ("(int v 1 (wrap 0 1.5))", "between two ints"),
            ("(complex v 1 (wrap 0 1))", "not complex"),
            ("(string v 'a' (wrap 0 1))", "not string"),
            ("(real v 1 (wrap 5 2))", "lo is below hi"),
            ("(real v 1 (wrap 0))", "two ends"),
        ],
    )
    def test_errors(self, src, msg):
        error(src, msg)


class TestWhereAValueIsBroughtIn:
    def test_a_bound_value(self):
        v = held("(real k 1) (real v (* 400 k) (wrap 0 360))")
        assert v.expr.op == "wrap" and v.expr.range == (0, 360)

    def test_a_bound_value_already_inside_is_left_alone(self):
        v = held("(real k 1 (>= 0) (<= 1)) (real v (* 100 k) (wrap 0 360))")
        assert v.expr.op != "wrap"

    def test_a_functions_result(self):
        src = "(type hour int (wrap 0 12)) (func[hour] later ((hour h) (int n)) (+ h n))"
        assert held(f"{src} (int v (later 9 5))").value == 2
        bound = held(f"{src} (int k 9) (int v (later k 5))")
        assert bound.expr.range == (0, 12)
        assert model(f"{src} (int k 9) (int v (later k 5))").functions[0].body.op == "wrap"

    def test_a_functions_argument(self):
        assert held("(type hour int (wrap 0 12)) (func f ((hour h)) h) (int v (f 15))").value == 3

    def test_its_range_proves_what_reads_it(self):
        # theta + 1 is at least 1, so 1 / (theta + 1) is never none.
        model("(real theta 40 (wrap 0 360)) (real v (/ 1 (+ theta 1)))")
        error("(real theta 40) (real v (/ 1 (+ theta 1)))", "may be none")

    def test_a_moves_ends_are_as_written(self):
        m = model("(real v 40 (wrap 0 360)) (animation a (move v (to (+ v 360)) (duration 1)))")
        (t,) = [o for o in m.objects if o.kind == "transition"]
        assert t.attrs["to"].expr.op != "wrap"


def test_the_compiled_model_passes_the_schema():
    d = doc("(real k 1) (real t 40 (wrap 0 360)) (real v (* 400 k) (wrap 0 360))")
    assert errors(d) == []
