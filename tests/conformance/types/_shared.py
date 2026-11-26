"""What the conformance tests of docs/spec/types.md share: imports, sources and helpers."""

import pytest

from ..support import accepted, compile_error, same_meaning

rule = pytest.mark.rule

UNIT = pytest.mark.xfail(strict=True, reason="mtp-vc5g: unit is declared in the file types")

EASE = pytest.mark.xfail(strict=True, reason="mtp-6kta: ease is not a type")

UNION = pytest.mark.xfail(strict=True, reason="mtp-mo3r: a type joins only with none")

BEZIER = pytest.mark.xfail(strict=True, reason="mtp-qnws: the shape bezier is named curve")

TYPES_REDESIGN = pytest.mark.xfail(
    strict=True, reason="mtp-rk1i: the type calculus is not in the compiler"
)


def xfail(bead: str | None, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}" if bead else why)


TYPE_FORMS = xfail(None, "the compiler does not read (type-apply ...) written out")

DEFAULT_UPPER = xfail(None, "a type that holds only (<= c) has no default value")

COLOR_OF = xfail("mtp-ivdt", "there is no color-of")

KNOWN_IF = xfail(None, "an if whose branches have one known length has no known length")

CHOICES = xfail("mtp-ydd4.7.42", "the choices are checked only for a value known when compiling")

MOVEMENT_INTERFACES = xfail(None, "zero-duration and instant are not types")

VARIANT_PARAMETER = xfail("mtp-ydd4.7.61", "a variant parameter that its shape does not read")

FUNCTION_VALUES = xfail("mtp-ydd4.7.43", "a list of functions and a function result that is one")

RECURSION = xfail("mtp-127y", "a function that calls itself may leave out its result type")

FACTORIAL = "((int n)) (if (= n 0) 1 (* n (f (- n 1)))))"

__all__ = [
    "pytest",
    "accepted",
    "compile_error",
    "same_meaning",
    "rule",
    "UNIT",
    "EASE",
    "UNION",
    "BEZIER",
    "TYPES_REDESIGN",
    "xfail",
    "TYPE_FORMS",
    "DEFAULT_UPPER",
    "COLOR_OF",
    "KNOWN_IF",
    "CHOICES",
    "MOVEMENT_INTERFACES",
    "VARIANT_PARAMETER",
    "FUNCTION_VALUES",
    "RECURSION",
    "FACTORIAL",
]
