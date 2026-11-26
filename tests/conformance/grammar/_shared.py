"""What the conformance tests of docs/spec/grammar.md share: imports, sources and helpers."""

import pytest
from helpers import field, interp

from mathterpiece.nodes import (
    Bar,
    Brackets,
    ComplexLit,
    IntLit,
    ListLit,
    NoneLit,
    PointLit,
    RatioLit,
    RealLit,
    StrLit,
)

from ..support import (
    REJECTION,
    accepted,
    compile_error,
    form,
    forms,
    in_folder,
    items,
    mtpc,
    name,
    obj,
    rejected,
    syntax_error,
    value,
)

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


ANIMATION = "(animation (move k (to 1) (duration 1)))"

BODY_LET = xfail("mtp-ydd4.7.8", "a let is an error in some bodies that hold items")

ARGUMENT_LET = xfail("mtp-ydd4.7.9", "a let or a foreach among the arguments of a shape compiles")

GROUP_EXISTS_WHEN = xfail("mtp-ydd4.7.10", "a group keeps every exists-when until its end")

IMPORT_ORDER = xfail("mtp-ydd4.7.12", "every import is read before any other form")

D = name(".")


def dot(x, y):
    return form(D, x, y)


__all__ = [
    "pytest",
    "field",
    "interp",
    "Bar",
    "Brackets",
    "ComplexLit",
    "IntLit",
    "ListLit",
    "NoneLit",
    "PointLit",
    "RatioLit",
    "RealLit",
    "StrLit",
    "REJECTION",
    "accepted",
    "compile_error",
    "form",
    "forms",
    "in_folder",
    "items",
    "mtpc",
    "name",
    "obj",
    "rejected",
    "syntax_error",
    "value",
    "rule",
    "xfail",
    "ANIMATION",
    "BODY_LET",
    "ARGUMENT_LET",
    "GROUP_EXISTS_WHEN",
    "IMPORT_ORDER",
    "D",
    "dot",
]
