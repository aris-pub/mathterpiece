"""Writing the .mtpc (docs/mtpc.md): every shared case gives a document the schema accepts, the
same bytes every time, and the parts the runtime needs."""

import json
from pathlib import Path

import pytest
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.mtpc import write

SHARED = sorted((Path(__file__).parent / "shared").glob("*.mtp"))


def doc(src):
    return json.loads(write(compile_source(src)))


@pytest.mark.parametrize("path", SHARED, ids=[p.stem for p in SHARED])
def test_every_shared_case_passes_the_schema(path):
    assert errors(json.loads(write(compile_source(path.read_text())))) == []


@pytest.mark.parametrize("path", SHARED, ids=[p.stem for p in SHARED])
def test_same_source_same_bytes(path):
    src = path.read_text()
    assert write(compile_source(src)) == write(compile_source(src))


def test_the_byte_form():
    text = write(compile_source("(real k 1)"))
    assert text.endswith("}\n") and ": " not in text and ", " not in text
    assert (
        text
        == json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    )


def test_places():
    d = doc("(real k 1) (real j (* 2 k)) (real c (+ 1 2))")
    k, j, c = (d["objects"][d["names"][n]]["value"] for n in "kjc")
    assert k == {"type": "real", "free": 1}
    assert j["bound"] == [
        "builtin",
        "real",
        "*",
        ["lit", "int", 2],
        ["read", "real", d["names"]["k"], None, None],
    ]
    assert j["deps"] == [[d["names"]["k"], None]]
    assert c == {"type": {"refine": "real", "constraints": [["const"]]}, "free": 3}


def test_values_by_type():
    d = doc("(ratio r 1/3) (color c 'red') (point p [1 2]) (real|none n none)")
    v = {n: d["objects"][d["names"][n]] for n in "rcpn"}
    assert v["r"]["value"]["free"] == [1, 3]
    assert v["c"]["value"]["free"] == "#ff0000ff" and v["c"]["token"] is True
    assert v["p"]["value"]["free"] == [1, 2]
    assert v["n"]["value"] == {"type": {"union": ["real", "none"]}, "free": None}


def test_types_and_functions():
    d = doc(
        "(type unit real (>= 0) (<= 1)) (motif dot ((unit t 0.5)) (circle c)) (func f (real x) x)"
    )
    assert d["types"][0] == {
        "name": "unit",
        "kind": "type",
        "type": {"refine": "real", "constraints": [[">=", 0], ["<=", 1]]},
    }
    assert d["types"][1] == {
        "name": "dot",
        "kind": "motif",
        "params": [{"name": "t", "type": {"named": "unit"}, "default": 0.5}],
    }
    assert d["functions"][0] == {
        "params": [{"name": "x", "type": "real"}],
        "result": "real",
        "body": ["local", "real", "x"],
    }
