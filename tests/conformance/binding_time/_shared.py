"""What the conformance tests of docs/spec/binding-time.md share: imports, sources and helpers."""

import pytest

from ..support import accepted, compile_error, free, is_bound, mtpc, obj, same_meaning, value

rule = pytest.mark.rule


def xfail(bead: str | None, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}" if bead else why)


OBJECT_ARGUMENT = xfail(None, "a call with an object as its argument is not folded")

RANDOM_NAMES = xfail(None, "the compiler names choice pick, and shuffled shuffle")

PAGE_READ = xfail(None, "a variable at the top level may read a control")

SLIDER = "(slider sz (animation (move size (from 0) (to 2) (duration 0))))"

__all__ = [
    "pytest",
    "accepted",
    "compile_error",
    "free",
    "is_bound",
    "mtpc",
    "obj",
    "same_meaning",
    "value",
    "rule",
    "xfail",
    "OBJECT_ARGUMENT",
    "RANDOM_NAMES",
    "PAGE_READ",
    "SLIDER",
]
