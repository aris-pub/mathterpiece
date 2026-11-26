"""What the conformance tests of docs/spec/core.md share: imports, sources and helpers."""

import itertools

import pytest

from ..support import (
    accepted,
    compile_error,
    in_folder,
    mtpc,
    rejected,
    same_meaning,
    value,
)


def typ(src, name):
    attribute = accepted(src).get(name).value
    return attribute.expr.type if attribute.bound else attribute.type


rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


LOCAL_PART = xfail("mtp-ydd4.7.5", "each part after the first of a name is read as an attribute")

WAIT = xfail("mtp-ydd4.7.21", "wait makes no transition object, while its rewrite does")

PALETTE_TYPE = xfail("mtp-ydd4.7.22", "a palette has the type palette, not namespace")

COND_ELSE = xfail("mtp-ydd4.7.46", "(cond (else V)) is marked const, while V is not")

POS_RANDOM = xfail(
    "mtp-ydd4.7.25", "pos compiles its point once, so a random call in it is one site"
)

CHOREO_ARGUMENT = xfail("mtp-08wd.5", "an argument of a choreo must be known when compiling")

MEMBER_BY_NAME = xfail("mtp-ydd4.7.19", "a member of a namespace is read as a key, not by its name")

ANIMATION_STEP = xfail("mtp-ydd4.7.26", "an animation's body does not accept the head animation")

POINTER_EVENTS = xfail("mtp-327t", "pointer-events on a container is a default for its members")

PARAMETRIC = xfail("mtp-of7a", "parametric is read as (parametric N (for T LO HI) E ...)")

DRAG_SHIFT = xfail("mtp-67wi", "a group is dragged by its translate, not its shift")

RANGE = xfail("mtp-z8i1", "range accepts (range n) and needs a gap or a num")

BOUNDED_LIST = xfail("mtp-ydd4.7.37", "a foreach over a list whose length is not known is an error")

STEP_EASE = xfail("mtp-ydd4.7.40", "step and step-ease are read only as the value of an ease")

SCENE = "(scene s (circle p (r 1)) (group g (circle q (r 2))))\n"

RAND = "(import rand rand rand-int pick shuffle next-seed roll-dice) "

FREE = "(bool a true) (bool b true) (bool c false)\n"

__all__ = [
    "itertools",
    "pytest",
    "accepted",
    "compile_error",
    "in_folder",
    "mtpc",
    "rejected",
    "same_meaning",
    "value",
    "typ",
    "rule",
    "xfail",
    "LOCAL_PART",
    "WAIT",
    "PALETTE_TYPE",
    "COND_ELSE",
    "POS_RANDOM",
    "CHOREO_ARGUMENT",
    "MEMBER_BY_NAME",
    "ANIMATION_STEP",
    "POINTER_EVENTS",
    "PARAMETRIC",
    "DRAG_SHIFT",
    "RANGE",
    "BOUNDED_LIST",
    "STEP_EASE",
    "SCENE",
    "RAND",
    "FREE",
]
