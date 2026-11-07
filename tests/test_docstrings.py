"""Docstrings: (doc 'text') is an optional argument every declaration takes. It is plain text,
known when compiling, for the illustrator and the author; it is written into the compiled model
for objects and functions, and the inventory page shows it. The author, 2026-11-05: written as
(doc …), never as a string at a fixed place; on every declaration; separate from a reader's
description (mtp-fl20). The author, 2026-11-06: written doc@'text', which the reader makes
(doc 'text'), and which mtp fmt writes in place of it, 2 in like the body."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.parse import ParseError, parse


def obj_doc(d, name):
    return next(o for o in d["objects"] if o.get("name") == name).get("doc")


@pytest.mark.parametrize(
    "src, name",
    [
        ("(real k 1 (doc 'D.'))", "k"),
        ("(scene s (real inner 2 (doc 'D.')))", "inner"),
        ("(scene s (circle c (r 1) (doc 'D.')))", "c"),
        ("(scene s (group g (doc 'D.') (circle_ (r 1))))", "g"),
        ("(motif m () (circle_ (r 1))) (scene s (m inst (doc 'D.')))", "inst"),
        ("(scene s (circle c (r 1))) (canvas v s (doc 'D.'))", "v"),
        ("(real k 1) (slider sl (move k (from 0) (to 2)) (doc 'D.'))", "sl"),
        ("(font note (size 14) (doc 'D.'))", "note"),
        ("(color ink '#000000' (doc 'D.'))", "ink"),
        ("(namespace theme (doc 'D.') (real gap 0.4))", "theme"),
        ("(palette brand (doc 'D.') (ink '#1f2a44'))", "brand"),
        ("(real k 0) (transition slide k (to 1) (duration 1) (doc 'D.'))", "slide"),
        ("(real k 0) (animation go (move k (to 1) (duration 1)) (doc 'D.'))", "go"),
    ],
)
def test_an_objects_doc_is_written_on_it(src, name):
    d = doc(src)
    assert obj_doc(d, name) == "D."
    assert errors(d) == []


def test_a_namespaces_member_takes_its_own():
    d = doc("(namespace theme (real gap 0.4 (doc 'The gap.')))")
    assert obj_doc(d, "theme.gap") == "The gap."


def test_a_listener_has_no_name_and_still_takes_one():
    d = doc("(scene s (circle c (r 1))) (canvas v s) (on-drag c c.pos (doc 'D.'))")
    assert next(o for o in d["objects"] if o["kind"] == "on-drag")["doc"] == "D."


ANIM = "(animation (move k (to 1) (duration 1)))"


@pytest.mark.parametrize(
    "decl, kind",
    [
        (f"(on-click c {ANIM} (doc 'D.'))", "on-click"),
        (f"(on-release c {ANIM} (doc 'D.'))", "on-release"),
        (f"(on-dragend c {ANIM} (doc 'D.'))", "on-dragend"),
        (f"(on-view v {ANIM} (doc 'D.'))", "on-view"),
        (f"(button go {ANIM} (doc 'D.'))", "button"),
        (f"(play go {ANIM} (doc 'D.'))", "play"),
        ("(toggle t none (label 't') (doc 'D.'))", "toggle"),
        ("(readout says $'{k}' (doc 'D.'))", "readout"),
    ],
)
def test_a_component_with_its_own_animation_keeps_the_doc(decl, kind):
    d = doc(f"(real k 0) (scene s (circle c (r 1))) (canvas v s) {decl}")
    assert [o.get("doc") for o in d["objects"] if o["kind"] == kind] == ["D."]
    assert [o for o in d["objects"] if o["kind"] != kind and o.get("doc")] == []


def test_a_canvas_that_fades_its_members_keeps_the_doc():
    d = doc("(scene s (circle c (r 1))) (canvas v (toggle-duration 0.4) (doc 'D.') s)")
    assert [(o["kind"], o["doc"]) for o in d["objects"] if o.get("doc")] == [("canvas", "D.")]


def test_an_anonymous_shape_takes_one():
    d = doc("(scene s (circle_ (r 1) (doc 'D.')))")
    assert next(o for o in d["objects"] if o["kind"] == "circle")["doc"] == "D."


@pytest.mark.parametrize(
    "src, key",
    [
        ("(func f ((real x)) (doc 'D.') (* 2 x))", ("func", "f")),
        ("(type unit real (>= 0) (<= 1) (doc 'D.'))", ("type", "unit")),
        ("(motif m () (doc 'D.') (circle_ (r 1)))", ("motif", "m")),
        ("(interface inky (color ink) (doc 'D.'))", ("interface", "inky")),
        ("(colormap heat ['navy' 'white'] (doc 'D.'))", ("func", "heat")),
    ],
)
def test_what_is_not_an_object_keeps_its_doc_in_the_compiler(src, key):
    assert model(src).docs[key] == "D."


def test_a_function_written_into_the_file_carries_its_doc():
    d = doc(
        "(func f ((real x)) (doc 'Twice x.') (* 2 x)) (real k 1)"
        " (scene s (circle c (r (abs (f k)))))"
    )
    assert [f.get("doc") for f in d["functions"]] == ["Twice x."]
    assert errors(d) == []


def test_it_changes_nothing_else():
    without = doc("(real k 1 (>= 0)) (scene s (circle c (r k))) (canvas v s)")
    given = doc("(real k 1 (>= 0) (doc 'D.')) (scene s (circle c (r k))) (canvas v s)")
    for o in given["objects"]:
        o.pop("doc", None)
    assert given == without


def test_given_twice_is_an_error():
    error("(real k 1 (doc 'a') (doc 'b'))", "'doc' is given twice")


def test_it_is_plain_text():
    error("(real j 2) (real k 1 (doc $'k is {j}'))", r"a doc is plain text")


def test_doc_is_reserved():
    error("(real doc 1)", "'doc' is reserved")


class TestDocAt:
    @pytest.mark.parametrize(
        "src",
        [
            "(real k 1 doc@'D.')",
            "(scene s (group g doc@'D.' (circle_ (r 1))))",
            "(motif m () doc@'D.' (circle_ (r 1))) (scene s (m inst))",
            "(func f ((real x)) doc@'D.' x) (real k) (real v (f k))",
        ],
    )
    def test_doc_at_is_doc(self, src):
        assert doc(src) == doc(src.replace("doc@'D.'", "(doc 'D.')"))

    @pytest.mark.parametrize(
        "src, msg",
        [
            ("(real k 1 doc@x)", "doc@ is followed by its text in single quotes: doc@'text'"),
            ("(real k 1 doc@$'x')", "doc@ is followed by its text in single quotes: doc@'text'"),
            (
                "(real k 1 note@'x')",
                "'@' only follows doc and free, as in doc@'text' and free@(f x)",
            ),
            ("(real a@b 1)", "'@' only follows doc and free, as in doc@'text' and free@(f x)"),
        ],
    )
    def test_at_follows_only_doc_and_takes_a_plain_string(self, src, msg):
        with pytest.raises(ParseError) as exc:
            parse(src)
        assert exc.value.msg == msg
