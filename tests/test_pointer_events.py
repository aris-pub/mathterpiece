"""(pointer-events bool): with false, the pointer passes through a shape to whatever is drawn
under it, as CSS's pointer-events: none. On a group it reaches the members, as in CSS, and a
member that gives its own value keeps it (the author, 2026-11-06)."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors


def value(m, name):
    return m.objects[m.id(name)].attrs["pointer-events"].value


def test_a_shape_catches_the_pointer_by_default():
    assert value(model("(scene s (circle c (r 1)))"), "c") is True


@pytest.mark.parametrize(
    "shape", ["(circle c (r 1)", "(text c 'hi'", "(line c (to [1 1])", "(arc c (r 1)"]
)
def test_any_shape_takes_it(shape):
    assert value(model(f"(scene s {shape} (pointer-events false)))"), "c") is False


def test_a_groups_reaches_its_members():
    m = model(
        "(scene s (group g (pointer-events false) (circle a (r 1))"
        " (circle b (r 1) (pointer-events true)) (group h (circle c (r 1)))))"
    )
    assert [value(m, n) for n in "abc"] == [False, True, False]


def test_an_instances_reaches_its_members():
    m = model("(motif m () (circle dot (r 1))) (scene s (m inst (pointer-events false)))")
    assert value(m, "inst.dot") is False


def test_it_may_come_from_defaults():
    m = model("(scene s (group g (defaults (pointer-events false)) (circle a (r 1))))")
    assert value(m, "a") is False


def test_it_is_a_bool():
    error("(scene s (circle c (r 1) (pointer-events 'none')))", "bool")


def test_given_twice_on_a_group_is_an_error():
    error(
        "(scene s (group g (pointer-events false) (defaults (pointer-events true))"
        " (circle a (r 1))))",
        "'pointer-events' is given twice",
    )


def test_it_may_change():
    m = model("(bool through false) (scene s (circle c (r 1) (pointer-events (not through))))")
    assert m.objects[m.id("c")].attrs["pointer-events"].bound


def test_the_compiled_file():
    d = doc("(scene s (group g (pointer-events false) (circle a (r 1)))) (canvas v s)")
    assert errors(d) == []
