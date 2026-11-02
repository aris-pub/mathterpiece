"""Every error example in docs/, with its message and its attribute (line:column). Messages say
what is wrong and what to do."""

import pytest

from mathterpiece.compiler import CompileError, compile_source

CASES = [
    # type-system.md section 3: only a literal converts.
    (
        "(string s 'red')\n(scene sc (circle d (fill s)))",
        "2:27",
        "expected color|none, got string: only a literal string becomes a color",
    ),
    # type-system.md 5.b and 5.c: a bound value that may break its constraint.
    (
        "(real k 1)\n(scene sc (circle c (r (* 2 k))))",
        "2:24",
        "c's r may break (>= 0): constrain what it reads so this can be proved, or declare c"
        " as circle|none",
    ),
    # type-system.md 5.c: a drawing-essential attribute that may be none.
    (
        "(real theta)\n(real|none crossing (secd theta))\n"
        "(scene sc (circle p) (line tan (from p.pos) (to [crossing 0])))",
        "3:49",
        "tan's to may be none: give it a default with (or? value default), or declare tan as"
        " line|none",
    ),
    # type-system.md 5.c: undefined at known inputs.
    ("(real|none v (secd 90))", "1:14", "secd is undefined at 90"),
    ("(real|none v (tand 90))", "1:14", "tand is undefined at 90"),
    ("(real|none v (asin 2))", "1:14", "asin is undefined at 2"),
    ("(real|none v (log 0))", "1:14", "log is undefined at 0"),
    ("(real|none v (sqrt -1))", "1:14", "sqrt is undefined at -1"),
    ("(real x 1 (const))\n(real|none v (/ x 0))", "2:14", "division by zero"),
    # type-system.md 5.d: a value that is not one of the choices.
    (
        "(type side string (one-of 'left' 'right'))\n(side t 'up')",
        "2:9",
        "'up' is not a side: a side is one of 'left', 'right'",
    ),
    # type-system.md 5.e: a variant's fixed attribute.
    (
        "(variant bar ((real p 0)) (rect _ (width 0.8)))\n(scene sc (bar b2 (width 2)))",
        "2:19",
        "a bar's width is fixed",
    ),
    # type-system.md 6: an interface lists only what it has.
    ("(func area (shape o) (* pi o.r o.r))", "1:28", "a shape has no attribute 'r'"),
    # type-system.md 8: no spreading on the scene.
    ("(scene s (circle c))\n(real k s.r)", "2:9", "a scene has no attribute 'r'"),
    # type-system.md "What the compiler proves" and "Known lengths".
    ("(real k 1e151)", "1:9", "1e+151 is beyond ±10^150, the limit of every number"),
    ("(list xs [1 2] (const))\n(real k xs[2])", "2:9", "position 2 is out of range"),
    # syntax.md section 7: self outside a motif's body.
    ("(scene s (circle c (r self.r)))", "1:23", "self is used only in a motif's body"),
    # reference.md "Defaults": no value to leave out.
    (
        "(real k (<= -1))",
        "1:1",
        "k needs a value: 0 breaks (<= -1), and there is no lower bound to use instead",
    ),
    # reference.md "Defaults": a transition with no duration.
    (
        "(real k)\n(animation a (transit _ k (to 1)))",
        "2:14",
        "this transit needs a duration (or a default-duration around it)",
    ),
    # reference.md "Writes and conditions": a condition that is not a limit.
    (
        "(real k)\n(real j)\n(button b (animation (transit _ k (to 1) (duration 1))) (> j 1))",
        "3:57",
        "a condition compares an attribute this writer writes with a limit that does not depend on"
        " it, such as (>= k 0)",
    ),
    # reference.md "Controls": a toggle's value with a target.
    ("(bool b)\n(toggle t b (value true))", "2:20", "a toggle with a target shows its"),
    # reference.md "Numbers": rand inside a function.
    ("(func f (real x) (+ x (rand)))", "1:23", "rand inside a function is a compile error"),
]


@pytest.mark.parametrize("src, attribute, message", CASES, ids=[c[2][:40] for c in CASES])
def test_the_error_and_where_it_is(src, attribute, message):
    with pytest.raises(CompileError) as exc:
        compile_source(src)
    assert message in exc.value.msg
    assert f"{exc.value.pos.line}:{exc.value.pos.col}" == attribute
