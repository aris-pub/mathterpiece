"""What the conformance tests of docs/spec/compiler-runtime.md share: imports, sources and
helpers."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from mtpc_check import errors as schema_errors

from mathterpiece.build import compiled
from mathterpiece.cli import main
from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.mtpc import SPEC_VERSION
from mathterpiece.parse import ParseError, parse

from ..support import (
    REJECTION,
    ROOT,
    SPEC,
    accepted,
    compile_error,
    in_folder,
    mtpc,
    obj,
    raw_mtpc,
    syntax_error,
)

RAND = "(import rand rand rand-int pick shuffle next-seed roll-dice) "

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


LABEL = xfail("mtp-ydd4.7.53", "an error carries no label of a rule")

STEPS = xfail("mtp-08wd.1", "each copy of a foreach is proved with the value of its variable")

FIGURE = "(real k 1 (>= 0) (<= 2))\n(scene s (circle c (r k)))\n(canvas v s)\n"


def run(*args: str):
    """Runs the mtp command, and gives its exit status."""
    try:
        main(list(args))
    except SystemExit as e:
        return e.code
    return 0


def _walk(x, found):
    if isinstance(x, list):
        if len(x) >= 3 and x[0] == "read" and isinstance(x[2], int):
            found["reads"].append((x[2], x[3]))
        if len(x) >= 3 and x[0] == "call" and isinstance(x[2], int):
            found["calls"].append(x[2])
        for y in x:
            _walk(y, found)
    elif isinstance(x, dict):
        for y in x.values():
            _walk(y, found)


def _bound_slots(d):
    for o in d["objects"]:
        slots = [o["value"]] if "value" in o else []
        slots += list(o.get("attrs", {}).values())
        for slot in slots:
            if isinstance(slot, dict) and "bound" in slot:
                yield o, slot


# house.mtp is not a figure, and ulam-spiral.mtp takes about 15 seconds to compile.
EXAMPLES = sorted(
    p for p in (ROOT / "examples").glob("*.mtp") if p.name not in ("house.mtp", "ulam-spiral.mtp")
)

LISTENERS = """(real k 0 (>= 0) (<= 1))
(point p [0 0])
(scene s (circle c (r 1)))
(canvas v s
  (on-click c (animation (move k (to 1) (duration 1))))
  (on-enter c (animation (move k (to 1) (duration 1))))
  (on-drag c c.pos)
  (on-show c (animation (at-once (move c.opacity (to 1) (duration 0))
                                 (move c.drawn (to 1) (duration 1)))))
  (on-pointermove c p)
  (on-pointermove p)
  (on-view (animation (move k (to 1) (duration 1)))))
(canvas w s)
"""


def _listener(d: dict, kind: str) -> dict:
    return next(o for o in d["objects"] if o["kind"] == kind)


# pytest.raises with a match argument checks the wording of an error.
WORDING = re.compile(r"raises\([^)]*match *=")


def _labels() -> set[str]:
    labels = set()
    for page in SPEC.glob("*.md"):
        labels |= set(re.findall(r"^```\{rule\} ([a-z0-9-]+)", page.read_text(), re.M))
    return labels


__all__ = [
    "json",
    "os",
    "re",
    "subprocess",
    "sys",
    "Path",
    "pytest",
    "schema_errors",
    "compiled",
    "main",
    "CompileError",
    "compile_source",
    "SPEC_VERSION",
    "ParseError",
    "parse",
    "REJECTION",
    "ROOT",
    "SPEC",
    "accepted",
    "compile_error",
    "in_folder",
    "mtpc",
    "obj",
    "raw_mtpc",
    "syntax_error",
    "RAND",
    "rule",
    "xfail",
    "LABEL",
    "STEPS",
    "FIGURE",
    "run",
    "_walk",
    "_bound_slots",
    "EXAMPLES",
    "LISTENERS",
    "_listener",
    "WORDING",
    "_labels",
]
