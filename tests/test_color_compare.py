import random

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Free
from mathterpiece.parse import parse

# k is written by a button, so it stays unknown until drawing.
SCENE = "(scene 's' (circle 'dot' (fill 'red')) (circle 'blue-dot' (fill 'blue')))"
CONTROL = "(button 'b' (animation (k (transition (to 0) (duration 0)))))"


def value(src, after=""):
    m = compile_model(parse(f"(real 'k' 0) {src} {SCENE} {CONTROL} {after}"))
    return Evaluator(m, random.Random(0)).value(m["v"], "value")


def stored(src):
    doc = to_json(compile_model(parse(f"(real 'k' 0) {src} {SCENE} {CONTROL}")))
    return doc["objects"][doc["names"]["v"]]["attrs"]["value"]


class TestThroughFunctions:
    def test_an_object_parameters_fill(self):
        f = "(func 'is-red' (params (o)) (= o.fill 'red'))"
        assert value(f, "(bool 'v' (is-red dot))") is True
        assert value(f, "(bool 'v' (is-red blue-dot))") is False

    def test_a_functions_color_result(self):
        f = "(func 'tint' (params (t 0.0)) (mix 'red' 'red' t))"
        assert value(f"{f} (bool 'v' (= (tint k) 'red'))") is True

    def test_a_let_holding_a_color_in_a_function(self):
        f = "(func 'f' (params (t 0.0)) (let ((c (mix 'red' 'red' t))) (= c 'red')))"
        assert value(f"{f} (bool 'v' (f k))") is True

    def test_written_as_a_color_comparison(self):
        f = "(func 'tint' (params (t 0.0)) (mix 'red' 'red' t))"
        assert stored(f"{f} (bool 'v' (= (tint k) 'red'))")[0] == "color="


class TestFolded:
    @pytest.mark.parametrize(
        "expr, expected",
        [
            ("(= (mix 'red' 'red' 0) 'red')", True),
            ("(!= (mix 'red' 'red' 0) 'red')", False),
            ("(= (mix 'red' 'blue' 0) 'blue')", False),
        ],
    )
    def test_compares_colors_not_strings(self, expr, expected):
        m = compile_model(parse(f"(bool 'v' {expr}) (scene _)"))
        assert m["v"].value == Free(expected)  # ty: ignore[unresolved-attribute]


class TestColorStringsInFunctions:
    @pytest.mark.parametrize(
        "func",
        [
            "(func 'f' (params (t 0.0)) (mix 'notacolor' 'red' t))",
            "(func 'f' (params (t 0.0)) (lighten 'notacolor' t))",
        ],
    )
    def test_checked_at_compile_time(self, func):
        with pytest.raises(CompileError, match="is not a color"):
            compile_model(parse(f"{func} (scene 's' (circle 'c')) (bool 'v' (= 1 1))"))

    def test_also_when_the_function_is_called(self):
        src = (
            "(func 'f' (params (o)) (= o.fill 'notacolor'))"
            " (scene 's' (circle 'c')) (bool 'v' (f c))"
        )
        with pytest.raises(CompileError, match="is not a color"):
            compile_model(parse(src))
