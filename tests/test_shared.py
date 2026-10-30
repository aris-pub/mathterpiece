"""Cases both runtimes must agree on: each tests/shared/*.mtp is run here with matplotlib's
evaluator and in web/test/shared.test.ts with the web runtime, against the same expectations.

A case's comment lines are its steps, in order:
  ; expect NAME VALUE      the value of NAME (JSON: a number, true, false, or a "string")
  ; write TARGET VALUE     write VALUE to TARGET: NAME, NAME.ATTR or NAME[K].ATTR
  ; page                   the web runs it on a page (CSS resolves colors), in the browser tests
"""

import json
import random
import re
from pathlib import Path

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import compile_model
from mathterpiece.parse import parse

CASES = sorted((Path(__file__).parent / "shared").glob("*.mtp"))
STEP = re.compile(r"^; (expect|write) (\S+) (.+)$")


def steps(text: str) -> list[tuple[str, str, object]]:
    found = []
    for line in text.splitlines():
        if m := STEP.match(line):
            found.append((m[1], m[2], json.loads(m[3])))
    return found


def target(model, path: str):
    m = re.fullmatch(r"([\w-]+)(?:\[(-?\d+)\])?(?:\.([\w-]+))?", path)
    assert m, f"bad target {path!r}"
    obj = model[m[1]]
    if m[2] is not None:
        obj = obj.members[int(m[2])]
    return obj, m[3] or "value"


def run(path: Path) -> list[str]:
    text = path.read_text()
    model = compile_model(parse(text))
    ev = Evaluator(model, random.Random(0))
    wrong = []
    for kind, name, value in steps(text):
        obj, attr = target(model, name)
        if kind == "write":
            ev.write(obj, attr, value)
            continue
        got = ev.value(obj, attr)
        if not agrees(got, value):
            wrong.append(f"{name}: expected {value!r}, got {got!r}")
    return wrong


# Numbers agree to rounding; a bool only matches a bool, and a string only the same string.
def agrees(got, want) -> bool:
    if isinstance(want, bool) or isinstance(got, bool):
        return got is want
    if isinstance(want, int | float):
        return isinstance(got, int | float) and got == pytest.approx(want)
    return got == want


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.stem)
def test_case(case):
    assert steps(case.read_text()), "a case needs at least one step"
    assert run(case) == []


def test_a_wrong_expectation_fails(tmp_path):
    case = tmp_path / "wrong.mtp"
    case.write_text(
        "; expect v 2\n; write k 5\n; expect v 6\n(real 'k' 1) (real 'v' (+ k 1)) (scene _)"
    )
    assert run(case) == []
    case.write_text("; expect v 3\n(real 'k' 1) (real 'v' (+ k 1)) (scene _)")
    assert run(case) == ["v: expected 3, got 2.0"]
    case.write_text("; expect b 1\n(bool 'b' true) (scene _)")
    assert run(case) == ["b: expected 1, got True"]
