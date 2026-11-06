"""Motifs of animations (mtp-iy7). The author, 2026-11-06: a motif whose body is one
(animation …) is a template of animations, as a motif of shapes is of shapes; a function never
declares. The motif's name is a type that refines animation; an instance's arguments may be
read, never written; a body is shapes, or one animation, never both."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.types import ANIMATION, fits

BASE = (
    "(real k 0) (string label 'start') (scene s (circle c (r 1)))"
    " (motif stop ((real to-k 0) (string text '') (real seconds 8))"
    "   (animation (at-once (defaults (duration seconds))"
    "     (move k (to to-k)) (move label (to text)))))"
)


def test_an_instance_is_an_animation_of_the_motifs_type():
    m = model(BASE + " (stop third (to-k 120) (text 'a third') (seconds 10))")
    third = m.get("third")
    assert third.kind == "animation" and str(third.type) == "stop"
    assert fits(third.type, ANIMATION)
    assert third.attrs["duration"].value == 10


def test_defaults_and_like():
    m = model(BASE + " (stop a (to-k 90) (seconds 4)) (stop b (like a) (to-k 45))")
    assert m.get("b").attrs["duration"].value == 4


def test_its_arguments_are_read_never_written():
    m = model(BASE + " (stop third (to-k 120)) (real v third.to-k)")
    assert m.get("v").value.value == 120


def test_used_without_a_name_in_an_animation():
    m = model(BASE + " (animation tour (in-order (stop_ (to-k 1) (seconds 2)) (wait 1)))")
    assert m.get("tour").attrs["duration"].value == 3


def test_a_shape_parameter():
    m = model(
        "(scene s (circle c)) (motif fade ((shape who) (real seconds 1))"
        " (animation (move who.opacity (to 0) (duration seconds))))"
        " (fade out (who c) (seconds 2))"
    )
    assert m.get("out").attrs["duration"].value == 2


def test_the_compiled_model_passes_the_schema():
    assert errors(doc(BASE + " (stop third (to-k 120)) (play p (animation third))")) == []


@pytest.mark.parametrize(
    "src, msg",
    [
        (
            "(motif m () (circle c) (animation (wait 1)))",
            "a motif's body is shapes, or one \\(animation …\\), never both",
        ),
        ("(motif m ((real duration 1)) (animation (wait duration)))", "already has 'duration'"),
        (BASE + " (stop third (nope 1))", "a stop takes no argument"),
        (BASE + " (stop third (seconds 1) (like third))", "comes first"),
    ],
)
def test_errors(src, msg):
    error(src, msg)
