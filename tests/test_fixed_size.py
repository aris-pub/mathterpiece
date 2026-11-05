"""A fixed-size group (mtp-ggs): (group g (translate p) (fixed-size true) members…) measures its
members in screen pixels around its position, on every canvas and at every zoom. Only the scale
changes. Its box is its position, of no size, and a drag moves it by its translate. The author,
2026-11-05: a setting on group, not a new shape, so any shape can be a handle; a bool, to be
reviewed with the units system (mtp-syd)."""

from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.types import POINT, REAL

HANDLE = (
    "(group grip (translate [1 2]) (fixed-size true) (circle_ (r 6)) (rect_ (width 4) (height 12)))"
)


def test_it_is_written_on_the_group():
    d = doc(f"(scene s {HANDLE}) (canvas v s)")
    grip = next(o for o in d["objects"] if o.get("name") == "grip")
    assert grip["fixed-size"] is True
    assert errors(d) == []


def test_false_is_a_group_as_any_other():
    d = doc("(scene s (group g (fixed-size false) (circle_ (r 1)))) (canvas v s)")
    assert "fixed-size" not in next(o for o in d["objects"] if o.get("name") == "g")


def test_its_position_is_one_point_that_follows_its_translate():
    m = model(f"(scene s {HANDLE} (circle c (pos grip.pos) (r 1)) (real gx grip.x))")
    grip = m.id("grip")
    x = m.get("c").attrs["x"].expr
    assert {(grip, "translate"), (grip, "transform")} <= x.deps
    assert m.get("gx").value.expr.type == REAL


def test_a_plain_group_still_gives_its_members_positions():
    m = model("(scene s (group g (circle a (pos [1 0])) (circle b)) (point p (top-right g)))")
    assert m.get("p").value.expr.type == POINT


def test_things_are_placed_against_its_position_even_with_a_text_inside():
    # A text's box is not known, but a fixed-size group's box never reads its members.
    m = model(
        "(scene s (group tag (translate [1 2]) (fixed-size true) (text_ 'a'))"
        " (point p (top-right tag 0.2)))"
    )
    assert (m.id("tag"), "translate") in m.get("p").value.expr.deps


def test_a_drag_moves_it_by_its_translate():
    d = doc(f"(scene s {HANDLE}) (canvas v s) (on-drag grip grip.pos)")
    assert errors(d) == []


def test_given_twice_is_an_error():
    error(
        "(scene s (group g (fixed-size true) (fixed-size true) (circle_ (r 1))))",
        "'fixed-size' is given twice",
    )


def test_it_is_known_when_compiling():
    error(
        "(bool b true) (scene s (group g (fixed-size b) (circle_ (r 1))))",
        r"\(fixed-size true\) or \(fixed-size false\)",
    )


def test_one_inside_another_is_an_error():
    error(
        "(scene s (group a (fixed-size true) (group b (fixed-size true) (circle_ (r 1)))))",
        "already measured in screen pixels",
    )


def test_a_drag_on_a_member_is_an_error():
    error(
        "(scene s (group g (fixed-size true) (circle c (r 6)))) (on-drag c c.pos)",
        "drag the group instead",
    )


def test_a_drag_with_a_bound_translate_is_an_error():
    error(
        "(scene s (circle p (r 1)) (group g (translate p.pos) (fixed-size true) (circle_ (r 6))))"
        " (on-drag g g.pos)",
        "translate is bound",
    )


def fixed(m, name):
    return bool(m.get(name).data.get("fixed-size"))


def test_a_containers_defaults_give_it_to_the_groups_among_its_members():
    m = model(
        "(scene s (group corners (defaults (fill 'black') (fixed-size true))"
        " (group a (translate [0 0]) (circle_ (r 9)))"
        " (group b (translate [1 0]) (circle_ (r 9)))"
        " (circle other (r 1))))"
    )
    assert fixed(m, "a") and fixed(m, "b")
    assert not fixed(m, "corners")


def test_it_goes_no_further_down_than_the_groups_that_take_it():
    # The group inside a takes nothing, so its members are not in pixels twice.
    m = model(
        "(scene s (group corners (defaults (fixed-size true))"
        " (group a (group inner (circle_ (r 9))))))"
    )
    assert fixed(m, "a") and not fixed(m, "inner")


def test_a_members_own_setting_wins():
    m = model(
        "(scene s (group corners (defaults (fixed-size true))"
        " (group a (fixed-size false) (group inner (circle_ (r 9))))))"
    )
    assert not fixed(m, "a") and fixed(m, "inner")


def test_in_defaults_it_is_known_when_compiling_too():
    error(
        "(bool b true) (scene s (group g (defaults (fixed-size b)) (group a (circle_ (r 1)))))",
        r"\(fixed-size true\) or \(fixed-size false\)",
    )


def test_a_drag_with_a_const_translate_is_an_error():
    # A translate worked out when compiling is free but const, so no writer may write it.
    error(
        "(scene s (group g (translate (+ [1 0] [0 1])) (fixed-size true) (circle_ (r 6))))"
        " (on-drag g g.pos)",
        "g.translate is const",
    )


def test_a_const_point_by_name_leaves_it_free_to_drag():
    d = doc(
        "(point at (+ [1 0] [0 1]) (const))"
        " (scene s (group g (translate at) (fixed-size true) (circle_ (r 6)))) (canvas v s)"
        " (on-drag g g.pos)"
    )
    assert errors(d) == []
