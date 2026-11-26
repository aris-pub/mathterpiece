"""What the conformance tests of docs/spec/imports.md share: imports, sources and helpers."""

import tempfile
from pathlib import Path

import pytest

from mathterpiece.compiler import CompileError

from ..support import REJECTION, ROOT, accepted, compile_error, in_folder

rule = pytest.mark.rule


def xfail(bead: str | None, why: str, condition: bool = True):
    reason = f"{bead}: {why}" if bead else why
    return pytest.mark.xfail(condition, strict=True, reason=reason)


def _case_blind() -> bool:
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "probe.mtp").write_text("", encoding="utf-8")
        return (Path(folder) / "PROBE.mtp").exists()


IMPORT_DOT = xfail("mtp-ydd4.7.47", "after (import F), (. F N) is an unknown name")

IMPORT_CASE = xfail(
    "mtp-ydd4.7.57",
    "on a file system that does not tell upper and lower case apart, the import finds the file",
    _case_blind(),
)

QUALIFIED = xfail(None, "after (import F N), F.N is an unknown name")

BOUND_IN_FILE = xfail(None, "a file to import may not hold a bound variable")

FREE_COLOR = xfail(None, "a file to import may hold a free color variable")


def rejected_in(folder: Path, files: dict[str, str], main: str) -> None:
    """Writes the files into the folder, and a later step than the parse step rejects main."""
    with pytest.raises(CompileError):
        in_folder(folder, files, main)


__all__ = [
    "tempfile",
    "Path",
    "pytest",
    "CompileError",
    "REJECTION",
    "ROOT",
    "accepted",
    "compile_error",
    "in_folder",
    "rule",
    "xfail",
    "_case_blind",
    "IMPORT_DOT",
    "IMPORT_CASE",
    "QUALIFIED",
    "BOUND_IN_FILE",
    "FREE_COLOR",
    "rejected_in",
]
