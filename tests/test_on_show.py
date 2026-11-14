"""on-show and on-hide (mtp-7i3j; the design in mtp-kqtk). Listeners written inside a canvas's
body: (on-show d1 animation) and (on-hide d1 animation), where the animation is an inline
(animation …) or a use of a choreo. While one plays, the canvas draws a stand-in in place of the
shape, and the animation moves the stand-in, never the scene. Hidden is drawn 0 and opacity 0,
so an on-show moves both to 1 and an on-hide both to 0: an animation that leaves either unmoved
is a compile error naming what is missing. A group passes its on-show or on-hide to its members,
and a member's own wins. A canvas gives a shape from one item at most."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import CompileError, compile_source

SCENE = (
    "(bool show false) (real k 0)"
    " (scene s (circle c (r 1) (stroke '#000000')) (text label 'hi') (circle bound-x (x k))"
    "  (group g (circle a) (circle b)))"
)
FADE = (
    "(choreo fade-in ((shape who) (real seconds 0.4))"
    " (at-once (move who.drawn (to 1) (duration 0)) (move who.opacity (to 1) (duration seconds))))"
    " (choreo fade-out ((shape who) (real seconds 0.4))"
    " (at-once (move who.drawn (to 0) (duration seconds))"
    " (move who.opacity (to 0) (duration seconds))))"
)
DRAW_ON = (
    "(animation (at-once (move c.drawn (to 1) (duration 1)) (move c.opacity (to 1) (duration 0))))"
)
BASE = SCENE + " " + FADE


def listeners(d: dict, kind: str) -> list[dict]:
    return [o for o in d["objects"] if o["kind"] == kind]


def test_on_show_with_an_inline_animation_compiles_inside_a_canvas():
    d = doc(BASE + f" (canvas v (when show c) (on-show c {DRAW_ON}))")
    [on] = listeners(d, "on-show")
    canvas = d["names"]["v"]
    assert on["shape"] == d["names"]["c"]
    assert on["in"] == [canvas]
    assert d["objects"][on["animation"]]["kind"] == "animation"
    assert errors(d) == []


def test_on_show_and_on_hide_with_a_use_of_a_choreo():
    d = doc(BASE + " (canvas v (when show c) (on-show c (fade-in c)) (on-hide c (fade-out c 1)))")
    [show] = listeners(d, "on-show")
    [hide] = listeners(d, "on-hide")
    assert show["shape"] == hide["shape"] == d["names"]["c"]
    steps = d["objects"][hide["animation"]]["steps"]
    assert steps[0] == "at-once"
    assert all(step[3] == 1 for step in steps[1:])
    assert errors(d) == []


def test_the_choreo_use_is_the_same_as_its_inline_animation():
    a = model(BASE + " (canvas v (when show c) (on-show c (fade-in c)))")
    b = model(
        BASE + " (canvas v (when show c) (on-show c (animation (at-once"
        " (move c.drawn (to 1) (duration 0)) (move c.opacity (to 1) (duration 0.4))))))"
    )
    assert [o.kind for o in a.objects] == [o.kind for o in b.objects]


def test_on_show_outside_a_canvas_is_an_error():
    error(BASE + " (on-show c (fade-in c))", r"inside the body of the view it acts in")
    error(
        BASE + " (formula f 'x') (display d f (on-show c (fade-in c)))",
        r"on-show .* inside a canvas",
    )
    error(BASE + " (readout r 'x' (on-show c (fade-in c)))", r"on-show .* inside a canvas")


def test_an_animation_that_leaves_drawn_unmoved_is_an_error():
    error(
        BASE
        + " (canvas v (when show c) (on-show c (animation (move c.opacity (to 1) (duration 1)))))",
        r"on-show c leaves c\.drawn unmoved",
    )


def test_an_animation_that_leaves_opacity_unmoved_is_an_error():
    error(
        BASE
        + " (canvas v (when show c) (on-hide c (animation (move c.drawn (to 0) (duration 1)))))",
        r"on-hide c leaves c\.opacity unmoved",
    )


def test_an_on_show_needs_an_animation():
    error(BASE + " (canvas v (when show c) (on-show c))", r"on-show c takes an animation")


def test_an_on_show_moves_only_its_stand_in():
    error(
        BASE + " (canvas v (when show c) (on-show c (animation (at-once (fade-in c)"
        " (move k (to 1) (duration 1))))))",
        r"on-show c moves only c's stand-in",
    )
    error(
        BASE + " (canvas v (when show c) label (on-show c (animation (at-once (fade-in c)"
        " (move label.x (to 1) (duration 1))))))",
        r"on-show c moves only c's stand-in",
    )


def test_an_on_show_takes_nothing_else():
    error(
        BASE + " (canvas v (when show c) (on-show c (fade-in c) (active show)))",
        r"on-show takes the shape and its animation",
    )


def test_one_on_show_per_shape_in_a_canvas():
    error(
        BASE + " (canvas v (when show c) (on-show c (fade-in c)) (on-show c (fade-in c 1)))",
        r"c has an on-show in v already",
    )


def test_the_canvas_must_be_able_to_show_the_shape():
    error(BASE + " (canvas v label (on-show c (fade-in c)))", r"never shows c")


def test_a_stand_in_may_move_an_attribute_bound_in_the_scene():
    # The stand-in's attributes follow the original's, bound ones too; the animation moves only
    # an offset from them, so it never writes the scene.
    d = doc(
        BASE + " (canvas v (when show bound-x) (on-show bound-x (animation (at-once"
        " (fade-in bound-x) (move bound-x.x (from -2) (duration 1))))))"
    )
    assert errors(d) == []
    error(BASE + " (button go (animation (move bound-x.x (to 1))))", r"bound")


def test_a_group_on_show_covers_every_member():
    d = doc(BASE + " (canvas v (when show g) (on-show g (fade-in g)) (on-show a (fade-in a 1)))")
    assert [o["shape"] for o in listeners(d, "on-show")] == [d["names"]["g"], d["names"]["a"]]
    assert errors(d) == []


def test_a_group_on_show_must_move_each_member():
    error(
        BASE + " (canvas v (when show g) (on-show g (animation (at-once (move g.drawn (to 1)"
        " (duration 0)) (move a.opacity (to 1) (duration 1))))))",
        r"on-show g leaves b\.opacity unmoved",
    )


def test_a_member_may_be_moved_by_its_groups_on_show():
    d = doc(
        BASE + " (canvas v (when show g) (on-show g (animation (at-once (move g.drawn (to 1)"
        " (duration 0)) (move a.opacity (to 1) (duration 1))"
        " (move b.opacity (to 1) (duration 2))))))"
    )
    assert errors(d) == []


def test_two_items_giving_one_shape_is_an_error():
    error(
        BASE + " (bool other false) (canvas v (when show c) (when other c))",
        r"v gives c from two items: write one \(when …\) with one condition",
    )
    error(BASE + " (canvas v c (when show c))", r"v gives c from two items")
    error(BASE + " (canvas v (if show c a) (when show [b c]))", r"v gives c from two")


def test_one_item_with_one_condition_is_fine():
    d = doc(BASE + " (bool other false) (canvas v (when (or show other) c))")
    assert errors(d) == []


def test_a_text_takes_on_show():
    d = doc(BASE + " (canvas v (when show label) (on-show label (fade-in label)))")
    assert errors(d) == []


# What other listeners take in place of an animation (the author, 2026-11-13): a single move is
# (animation (move …)), with no change in behavior, and giving both is the animation twice.
def compile_error(src: str) -> str:
    with pytest.raises(CompileError) as caught:
        compile_source(src)
    return str(caught.value)


def test_a_move_where_the_animation_goes_is_that_animation():
    move = "(move c.opacity (to 0) (duration 1))"
    for kind in ("on-show", "on-hide"):
        bare = compile_error(BASE + f" (canvas v (when show c) ({kind} c {move}))")
        inline = compile_error(BASE + f" (canvas v (when show c) ({kind} c (animation {move})))")
        assert bare == inline
        assert f"{kind} c leaves c.drawn unmoved" in bare


def test_a_move_and_an_animation_are_the_animation_twice():
    error(
        BASE + " (canvas v (when show c) (on-show c (move c.opacity (to 1) (duration 1))"
        f" {DRAW_ON}))",
        "'animation' is given twice",
    )
