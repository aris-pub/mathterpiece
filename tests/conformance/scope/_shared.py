"""What the conformance tests of docs/spec/scope.md share: imports, sources and helpers."""

import pytest

from mathterpiece.compiler import CompileError

from ..support import accepted, compile_error, in_folder, mtpc, obj, value

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


AS_NAME = xfail("mtp-t8in", "the compiler has no (as N), and binds self and pointer itself")

LET_TWICE = xfail("mtp-ydd4.7.41", "the names of one let may be the same")

DRAG = "(real a 1 (>= 0) (<= 4)) (scene s (circle p (pos [a 0]) (r 0.2))) "

DOT = "(scene s (dot d))"

__all__ = [
    "pytest",
    "CompileError",
    "accepted",
    "compile_error",
    "in_folder",
    "mtpc",
    "obj",
    "value",
    "rule",
    "xfail",
    "AS_NAME",
    "LET_TWICE",
    "DRAG",
    "DOT",
]
