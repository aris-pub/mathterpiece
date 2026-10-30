import random

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import compile_model
from mathterpiece.parse import parse


# q.i is an int and a is a real; the buttons that write them keep them unknown until drawing,
# so the text is computed by the runtime rather than folded.
def shown(funcs, call):
    scene = (
        f"(scene 's' (group 'g' (circle _ (r 1)) (circle _ (r 2))) (counter 'q') (text 't' {call}))"
    )
    controls = (
        "(button 'b' (animation (at-once (q.i (transition (to 2) (duration 0)))"
        " (a (transition (to 3) (duration 0))))))"
    )
    m = compile_model(
        parse(
            f"(real 'a' 3) (motif 'counter' (params (i 2)) (circle 'c')) {funcs} {scene} {controls}"
        )
    )
    return Evaluator(m, random.Random(0)).value(m["t"], "value")


class TestLetTypesInFunctions:
    @pytest.mark.parametrize(
        "funcs, call, expected",
        [
            ("(func 'f' (params (n 0)) (let ((m (+ n 1))) $'{m}'))", "(f q.i)", "3"),
            ("(func 'f' (params (n 0)) (let ((m (+ n 1))) $'{m:d}'))", "(f q.i)", "3"),
            ("(func 'f' (params (x 0.0)) (let ((m (+ x 1))) $'{m}'))", "(f a)", "4.0"),
            ("(func 'f' (params (o)) (let ((m o.r)) $'{m}'))", "(f g[1])", "2.0"),
            ("(func 'f' (params (n 0)) (let ((b (> n 1))) $'{b}'))", "(f q.i)", "True"),
        ],
    )
    def test_shown_with_their_own_type(self, funcs, call, expected):
        assert shown(funcs, call) == expected

    def test_a_running_value(self):
        f = "(func 'f' (params (g)) (let ((n (count g p (> p.r 0)))) $'{n}'))"
        assert shown(f, "(f g)") == "2"
