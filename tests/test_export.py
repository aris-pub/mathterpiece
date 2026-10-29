import json
from pathlib import Path

import pytest
from helpers import with_scene

from mathterpiece.compiler import compile_model
from mathterpiece.export import to_json
from mathterpiece.parse import parse

EXAMPLES = Path(__file__).parent.parent / "examples"


def exported(src):
    return to_json(compile_model(with_scene(src)))


def obj(doc, name):
    return doc["objects"][doc["names"][name]]


def ref(doc, name):
    return doc["names"][name]


class TestShape:
    def test_top_level(self):
        doc = exported("(circle 'c')")
        assert doc["mtp"] == 1
        assert set(doc) == {"mtp", "objects", "functions", "names", "depends"}

    def test_ids_are_list_positions(self):
        doc = exported("(circle 'c')")
        assert all(o["id"] == i for i, o in enumerate(doc["objects"]))

    def test_serializable(self):
        doc = exported("(real 'k' 2) (circle 'c' (r k) (pos [1 2]))")
        assert json.loads(json.dumps(doc)) == doc

    def test_tree(self):
        doc = exported("(group 'g' (circle 'a') (circle 'b'))")
        g = obj(doc, "g")
        assert g["members"] == [ref(doc, "a"), ref(doc, "b")]
        assert obj(doc, "a")["parent"] == ref(doc, "g")

    def test_canvas_shows(self):
        doc = exported("(circle 'c') (canvas 'cnv' c)")
        assert obj(doc, "cnv")["shows"] == [ref(doc, "c")]


class TestValues:
    def test_plain_values(self):
        c = obj(exported("(circle 'c' (r 2) (fill 'red') (pos [1 2]))"), "c")
        assert (c["attrs"]["r"], c["attrs"]["fill"], c["attrs"]["x"]) == (2.0, "red", 1.0)

    def test_transform_as_six_numbers(self):
        g = obj(exported("(group 'g' (transform (translate 3 4)))"), "g")
        assert g["attrs"]["transform"] == [1.0, 0.0, 3.0, 0.0, 1.0, 4.0]

    def test_point_values(self):
        t = obj(exported("(triangle 't' (a [0 0]) (b [2 0]) (c [0 2]))"), "t")
        assert t["attrs"]["b"] == [2.0, 0.0]


class TestExpressions:
    def test_read(self):
        doc = exported("(real 'k' 2) (circle 'c' (r (* 2 k)))")
        assert obj(doc, "c")["attrs"]["r"] == ["*", 2.0, ["read", ref(doc, "k"), "value"]]

    def test_self(self):
        doc = exported("(circle 'c' (x 3) (r self.x))")
        assert obj(doc, "c")["attrs"]["r"] == ["read", ref(doc, "c"), "x"]

    def test_motif_parameter_and_sibling(self):
        doc = exported(
            "(real 'k' 2.0) (motif 'dot' (params (r 1.0)) (circle 'c' (r r)) (circle 'e' (x c.x)))"
            " (dot 'd' (r k))"
        )
        assert obj(doc, "d")["params"] == {"r": ["read", ref(doc, "k"), "value"]}
        assert obj(doc, "d.c")["attrs"]["r"] == ["param", ref(doc, "d"), "r"]
        assert obj(doc, "d.e")["attrs"]["x"] == ["read", ref(doc, "d.c"), "x"]

    def test_reading_into_another_frame_says_which(self):
        doc = exported("(motif 'dot' (circle 'c' (x 1))) (dot 'd' (x 3)) (real 'v' d.c.x)")
        assert obj(doc, "v")["attrs"]["value"] == ["read", ref(doc, "d.c"), "x", None]

    def test_inherited_style_reads_the_motif(self):
        doc = exported("(motif 'dot' (circle 'c')) (dot 'd' (fill 'red'))")
        assert obj(doc, "d.c")["attrs"]["fill"] == ["read", ref(doc, "d"), "fill"]

    def test_object_arguments(self):
        doc = exported("(circle 'a') (circle 'b') (real 'v' (dist a b))")
        v = obj(doc, "v")["attrs"]["value"]
        assert v == ["call", "dist", ["obj", ref(doc, "a")], ["obj", ref(doc, "b")]]

    def test_group_attributes_splice(self):
        doc = exported("(group 'g' (circle 'a' (r 1)) (circle 'b' (r 2))) (real 's' (+ g.r))")
        reads = [["read", ref(doc, "a"), "r"], ["read", ref(doc, "b"), "r"]]
        assert obj(doc, "s")["attrs"]["value"] == ["+", ["splice", *reads]]

    def test_lists(self):
        doc = exported("(real 'k') (circle 'c' (pos [k 1]))")
        local = obj(doc, "c")["attrs"]["x"]
        assert local[0] == "part"
        hidden = doc["objects"][local[1][1]]
        assert hidden["attrs"]["value"] == ["list", ["read", ref(doc, "k"), "value"], 1.0]

    def test_complex(self):
        doc = exported("(real 'k') (real 'v' (abs (* k 3-4i)))")
        assert obj(doc, "v")["attrs"]["value"] == [
            "abs",
            ["*", ["read", ref(doc, "k"), "value"], ["complex", 3.0, -4.0]],
        ]

    def test_strings_show_types(self):
        doc = exported(
            "(motif 'm' (params (n 3) (s 1.0)) (circle 'c')) (m 'd')"
            " (text 't' $'n={d.n} s={d.s}') (slider 'p' d.n) (slider 'q' d.s)"
        )
        assert obj(doc, "t")["attrs"]["value"] == [
            "str",
            "n=",
            ["show", ["param", ref(doc, "d"), "n"], "int"],
            " s=",
            ["show", ["param", ref(doc, "d"), "s"], "real"],
        ]

    def test_conditionals(self):
        doc = exported("(real 'k') (text 't' (if (< k 1) 'a' 'b'))")
        k = ["read", ref(doc, "k"), "value"]
        assert obj(doc, "t")["attrs"]["value"] == ["if", ["<", k, 1.0], "a", "b"]


class TestFunctions:
    def test_stored_with_defaults(self):
        doc = exported("(const 'g' 2.0) (func 'f' (params (x 0.0) (o)) (* g x))")
        assert doc["functions"]["f"] == {
            "params": [["x", 0.0], ["o", None]],
            "body": ["*", 2.0, ["arg", "x"]],
        }

    def test_calls(self):
        doc = exported("(real 'k') (func 'sq' (params (x 0.0)) (* x x)) (real 'v' (sq k))")
        assert obj(doc, "v")["attrs"]["value"] == ["call", "sq", ["read", ref(doc, "k"), "value"]]

    def test_let_in_a_body(self):
        doc = exported("(func 'f' (params (x 0.0)) (let ((y (* x 2))) (+ y x)))")
        assert doc["functions"]["f"]["body"] == [
            "let",
            [["y", ["*", ["arg", "x"], 2.0]]],
            ["+", ["arg", "y"], ["arg", "x"]],
        ]

    def test_object_parameter_parts(self):
        doc = exported("(func 'radius-of' (params (o)) o.r)")
        assert doc["functions"]["radius-of"]["body"] == ["read", ["arg", "o"], "r"]

    def test_hiding_a_library_function(self):
        doc = exported("(func 'dist' (params (x 0.0)) x)")
        assert set(doc["functions"]) == {"dist (user)"}


class TestControlsAndStates:
    def test_slider(self):
        doc = exported("(circle 'c') (slider 's' c.r (min 0) (max 5))")
        s = obj(doc, "s")
        assert (s["kind"], s["target"], s["type"]) == ("slider", [ref(doc, "c"), "r"], "real")
        assert (s["attrs"]["min"], s["attrs"]["max"], s["attrs"]["step"]) == (0.0, 5.0, None)

    def test_state_and_button(self):
        doc = exported("(real 'k' 1) (state 'big' (= k 3)) (button 'b' big (duration 2))")
        big = obj(doc, "big")
        assert big["moves"] == [[ref(doc, "k"), "value", 3.0]]
        assert big["conditions"] == [["=", ["read", ref(doc, "k"), "value"], 3.0]]
        b = obj(doc, "b")
        assert (b["state"], b["attrs"]["duration"], b["attrs"]["ease"]) == (
            ref(doc, "big"),
            2.0,
            "linear",
        )

    def test_unreachable_state_has_no_moves(self):
        big = obj(exported("(real 'k' 1) (state 'big' (< k 3))"), "big")
        assert big["moves"] is None

    def test_button_shorthand_has_an_anonymous_state(self):
        doc = exported("(circle 'c') (button 'b' c.fill 'red')")
        state = doc["objects"][obj(doc, "b")["state"]]
        assert (state["kind"], state["name"]) == ("state", None)

    def test_play(self):
        doc = exported(
            "(real 'k' 1) (state 'a' (= k 1)) (state 'z' (= k 3))"
            " (play 'p' (from a) (wait 1) (to z (duration 2) (ease 'ease-in')))"
        )
        p = obj(doc, "p")
        assert p["start"] == ref(doc, "a")
        assert p["steps"] == [["wait", 1.0], ["to", ref(doc, "z"), 2.0, "ease-in"]]


class TestDepends:
    def test_dependents(self):
        doc = exported("(real 'k' 1) (circle 'a' (r k)) (circle 'b' (r (* 2 a.r)))")
        k, a, b = ref(doc, "k"), ref(doc, "a"), ref(doc, "b")
        assert doc["depends"][f"{k}.value"] == [f"{a}.r"]
        assert doc["depends"][f"{a}.r"] == [f"{b}.r"]

    def test_parameters(self):
        doc = exported(
            "(real 'k' 1.0) (motif 'm' (params (r 1.0)) (circle 'c' (r r))) (m 'd' (r k))"
        )
        d = ref(doc, "d")
        assert f"{ref(doc, 'd.c')}.r" in doc["depends"][f"{d}.r"]


@pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.mtp")), ids=lambda p: p.name)
def test_examples_export(example):
    doc = to_json(compile_model(parse(example.read_text())))
    assert json.loads(json.dumps(doc)) == doc
