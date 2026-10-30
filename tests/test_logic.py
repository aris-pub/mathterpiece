import random

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Free
from mathterpiece.parse import parse

POINTS = (
    "(scene 's' (circle 'x' (pos [0 0]))"
    " (group 'points' (circle _ (pos [3 4]) (r 1)) (circle _ (pos [6 8]) (r 2))"
    " (circle _ (pos [1 0]) (r 3))))"
)


def model(src):
    return compile_model(parse(f"(real 'k' 2) (real 'n' 0) {POINTS} {src}"))


def value(src, name="v"):
    m = model(src)
    return Evaluator(m, random.Random(0)).value(m[name], "value")


def folded(src):
    return compile_model(parse(f"{src} (scene _)"))["v"].value  # ty: ignore[unresolved-attribute]


class TestWhileDrawing:
    @pytest.mark.parametrize(
        "expr, expected",
        [
            ("(and (> k 1) (< k 3))", True),
            ("(and (> k 1) (< k 2))", False),
            ("(and (> k 1) (> k 0) (< k 5))", True),
            ("(or (> k 5) (< k 3))", True),
            ("(or (> k 5) (< k 0) (= k 9))", False),
            ("(not (> k 1))", False),
            ("(not (not (> k 1)))", True),
        ],
    )
    def test_values(self, expr, expected):
        assert value(f"(bool 'v' {expr})") is expected

    def test_and_stops_at_the_first_false(self):
        assert value("(bool 'v' (and (!= n 0) (> (/ 1 n) 2)))") is False

    def test_or_stops_at_the_first_true(self):
        assert value("(bool 'v' (or (= n 0) (> (/ 1 n) 2)))") is True

    def test_in_a_condition(self):
        assert value("(real 'v' (if (and (> k 0) (not (= k 1))) 10 20))") == 10


class TestFolding:
    @pytest.mark.parametrize(
        "expr, expected",
        [
            ("(and true true)", True),
            ("(and true false)", False),
            ("(or false true)", True),
            ("(not true)", False),
        ],
    )
    def test_known_values_fold(self, expr, expected):
        assert folded(f"(bool 'v' {expr})") == Free(expected)

    # As with if, an error certain at compile time is reported even where it would be skipped.
    @pytest.mark.parametrize(
        "src", ["(bool 'v' (and false (> (/ 1 0) 2)))", "(real 'v' (if false (/ 1 0) 2))"]
    )
    def test_a_certain_error_is_reported(self, src):
        with pytest.raises(CompileError, match="division by zero"):
            folded(src)


class TestErrors:
    @pytest.mark.parametrize(
        "expr, match",
        [
            ("(and (> k 1))", "and takes two or more conditions"),
            ("(or (> k 1))", "or takes two or more conditions"),
            ("(not (> k 1) (> k 2))", "not takes one condition"),
            ("(and k (> k 1))", "the arguments of and must be bools"),
            ("(not k)", "the argument of not must be a bool"),
        ],
    )
    def test_invalid(self, expr, match):
        with pytest.raises(CompileError, match=match):
            model(f"(bool 'v' {expr})")

    @pytest.mark.parametrize("word", ["and", "or", "not"])
    def test_reserved(self, word):
        with pytest.raises(CompileError, match="part of the language"):
            compile_model(parse(f"(real '{word}' 1) (scene _)"))
