"""Writing the .mtpc (docs/mtpc.md): every shared case and every example gives a document the
schema accepts, the same bytes every time, and the parts the runtime needs."""

import json
from pathlib import Path

import pytest
from helpers import doc
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.mtpc import write

SHARED = sorted((Path(__file__).parent / "shared").glob("*.mtp"))
EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.mtp"))
FIGURES = [p for p in EXAMPLES if p.stem != "house"]


@pytest.mark.parametrize("path", SHARED, ids=[p.stem for p in SHARED])
def test_every_shared_case_passes_the_schema(path):
    assert errors(doc(path.read_text())) == []


@pytest.mark.parametrize("path", FIGURES, ids=[p.stem for p in FIGURES])
def test_the_example_compiles_to_a_valid_mtpc(path):
    assert errors(doc(path.read_text(), path)) == []


# The author, 2026-11-04: the colors and fonts the examples share live in examples/house.mtp,
# which each example imports; it is not a figure, so the dev page does not list it.
HOUSE_COLORS = ["paper", "ink", "soft", "terracotta", "teal", "saffron", "plum"]
HOUSE_FONTS = ["variable", "number", "code"]


def test_the_house_file_holds_the_shared_colors_and_fonts():
    src = (EXAMPLES[0].parent / "house.mtp").read_text()
    assert "(scene" not in src
    d = doc(src)
    for n in HOUSE_COLORS + HOUSE_FONTS:
        assert n in d["names"]


@pytest.mark.parametrize("path", FIGURES, ids=[p.stem for p in FIGURES])
def test_an_example_does_not_redeclare_a_house_token(path):
    src = path.read_text()
    if "(import house" not in src:
        return
    for n in HOUSE_COLORS:
        assert f"(color {n} " not in src
    for n in HOUSE_FONTS:
        assert f"(font {n} " not in src


def test_the_examples_that_use_the_house_style_import_it():
    users = [p.stem for p in FIGURES if "(import house" in p.read_text()]
    assert sorted(users) == sorted(
        [
            "bubbles",
            "dials",
            "ease-race",
            "koch-snowflake",
            "lens",
            "lissajous",
            "times-tables",
            "triangle-lines",
            "ulam-spiral",
        ]
    )


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


def test_free_and_bound_values():
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
        " (scene s (dot d)) (real k) (real v (f k))"
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


class TestOnlyWhatIsUsed:
    # mtp-j2o: the .mtpc holds only the functions and types the figure uses (mtpc.md, "Top level").
    def test_a_function_never_called_while_drawing_is_left_out(self):
        d = doc(
            "(func twice (real x) (* 2 x)) (func unused (real x) x) (real k) (real v (twice k))"
        )
        assert len(d["functions"]) == 1
        v = d["objects"][d["names"]["v"]]["value"]["bound"]
        assert v[0] == "call" and v[2] == 0

    def test_a_function_only_folded_is_left_out(self):
        d = doc("(func twice (real x) (* 2 x)) (real v (twice 3))")
        assert d["functions"] == []

    def test_functions_reached_through_others_are_kept_and_renumbered(self):
        d = doc(
            "(func unused (real x) x) (func inner (real x) (+ x 1)) (func outer (real x) (inner x))"
            " (real k) (real v (outer k))"
        )
        assert len(d["functions"]) == 2
        v = d["objects"][d["names"]["v"]]["value"]["bound"]
        outer = d["functions"][v[2]]
        assert (
            outer["body"][0] == "call" and d["functions"][outer["body"][2]]["body"][0] == "builtin"
        )

    def test_a_function_used_as_an_ease_is_kept(self):
        d = doc(
            "(func unused (real x) x) (func sq (real x) (* x x)) (real k)"
            " (animation a (move k (to 1) (duration 1) (ease sq)))"
        )
        assert len(d["functions"]) == 1
        assert errors(d) == []

    def test_a_type_never_used_is_left_out(self):
        d = doc("(type side string (one-of 'l' 'r')) (type unused int (>= 0)) (side s 'l')")
        assert [t["name"] for t in d["types"]] == ["side"]
