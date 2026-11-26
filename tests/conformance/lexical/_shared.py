"""What the conformance tests of docs/spec/lexical.md share: imports, sources and helpers."""

from fractions import Fraction

import pytest
from helpers import field, interp
from hypothesis import strategies as st

from mathterpiece.cli import main
from mathterpiece.nodes import (
    BoolLit,
    ColorLit,
    ComplexLit,
    Form,
    IntLit,
    NoneLit,
    RatioLit,
    RealLit,
    StrLit,
)

from ..support import (
    accepted,
    compile_error,
    examples,
    form,
    forms,
    items,
    name,
    syntax_error,
)

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


KEYWORD_NAMES = xfail("mtp-ydd4.7.35", "the compiler forbids only a few names, not every keyword")

NAMES_OK = [
    "theta",
    "show-tan",
    "x2",
    "a-",
    "none?",
    "the-true-value",
    "truex",
    "p.empty?",
    "found?.x",
    "ball.on-floor?",
    "Ab",
]

KEYWORDS = (
    "import type interface namespace palette colormap scene formula motif variant func "
    "transition animation choreo "
    "circle rect ellipse line triangle polyline polygon curve arc ring text group row column "
    "primitive let foreach exists-when term doc "
    "name if when cond else and or fn type-of as "
    "move wait set at-once in-order "
    "canvas readout display slider button play stepper toggle "
    "on-drag on-click on-release on-dragstart on-dragend on-enter on-leave on-pointermove "
    "on-show on-hide on-view on-ready on-live on-quiet"
).split()

# The keywords that today's compiler already forbids as the name of a variable.
FORBIDDEN_TODAY = {
    "scene", "animation", "transition", "move", "in-order", "at-once", "when", "else", "doc",
    "set", "primitive",
}  # fmt: skip

NOT_KEYWORDS = "x r size gap step fill duration like defaults loop const length wrap".split()

LITERAL_WORDS = ("true", "false", "none")

NAME_PARTS = st.from_regex(r"[A-Za-z][A-Za-z0-9-]{0,8}\??", fullmatch=True).filter(
    lambda part: part not in LITERAL_WORDS
)

QUALIFIED_NAMES = st.lists(NAME_PARTS, min_size=1, max_size=3).map(".".join)

SIGNS = st.sampled_from(["", "+", "-"])

# Leading zeros are allowed, so that 007 is a number too.
DIGITS = st.builds(lambda zeros, n: "0" * zeros + str(n), st.integers(0, 2), st.integers(0, 10**20))

# The exponent stays small enough that every real lies far inside the binary64 numbers.
EXPONENTS = st.builds(
    lambda e, sign, n: f"{e}{sign}{n}", st.sampled_from("eE"), SIGNS, st.integers(0, 280)
)


@st.composite
def unsigned_reals(draw, plain: bool = False) -> str:
    """The text of a real with no sign. A real needs a point or an exponent, and when plain is
    true the text may also be digits alone, as each part of a complex number may."""
    whole = draw(DIGITS)
    kind = draw(st.sampled_from(["point", "point only", "fraction only", "digits"]))
    text = {
        "point": f"{whole}.{draw(DIGITS)}",
        "point only": f"{whole}.",
        "fraction only": f".{draw(DIGITS)}",
        "digits": whole,
    }[kind]
    if (kind == "digits" and not plain) or draw(st.booleans()):
        text += draw(EXPONENTS)
    return text


INTS = st.builds(lambda sign, digits: sign + digits, SIGNS, DIGITS)
REALS = st.builds(lambda sign, text: sign + text, SIGNS, unsigned_reals())
NUMBERS = st.one_of(
    INTS,
    REALS,
    st.builds(lambda n, d: f"{n}/{d}", INTS, st.integers(1, 10**6)),
    st.builds(lambda sign, text: f"{sign}{text}i", SIGNS, unsigned_reals(plain=True)),
)
# Every kind of word: a name, a number, an operator, a bool literal and none.
WORDS = st.one_of(
    QUALIFIED_NAMES,
    NUMBERS,
    st.sampled_from("+ - * / ^ < <= > >= = != .".split()),
    st.sampled_from(LITERAL_WORDS),
)

__all__ = [
    "Fraction",
    "pytest",
    "field",
    "interp",
    "main",
    "BoolLit",
    "ColorLit",
    "ComplexLit",
    "Form",
    "IntLit",
    "NoneLit",
    "RatioLit",
    "RealLit",
    "StrLit",
    "accepted",
    "compile_error",
    "examples",
    "form",
    "forms",
    "items",
    "name",
    "syntax_error",
    "rule",
    "xfail",
    "KEYWORD_NAMES",
    "NAMES_OK",
    "KEYWORDS",
    "FORBIDDEN_TODAY",
    "NOT_KEYWORDS",
    "st",
    "LITERAL_WORDS",
    "NAME_PARTS",
    "QUALIFIED_NAMES",
    "SIGNS",
    "DIGITS",
    "unsigned_reals",
    "INTS",
    "REALS",
    "NUMBERS",
    "WORDS",
]
