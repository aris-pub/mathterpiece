"""What the conformance tests of docs/spec/lexical.md share: imports, sources and helpers."""

from fractions import Fraction

import pytest
from helpers import field, interp

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
]
