"""Choreos (mtp-h972). The author, 2026-11-11: (choreo name parameters item…) declares a kind of
animation, as a motif declares a kind of shape. Each use, (fade-in d1), with its arguments in
order, declares an animation in place, wherever an animation may be written. Its arguments are
known when compiling, so the compiler writes each use out as an ordinary animation. A choreo that
uses itself, directly or through other choreos, is refused. The choreo replaces the motif of
animations (mtp-iy7), whose tests these were."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.mtpc import write

SCENE = "(real k 0) (string label 'start') (scene s (circle c (r 1)) (circle d (r 2)))"
FADE = (
    "(choreo fade-in ((shape who) (real seconds 0.4)) (move who.opacity (to 1) (duration seconds)))"
)
STOP = (
    "(choreo stop ((real to-k 0) (string text '') (real seconds 8))"
    " (at-once (defaults (duration seconds)) (move k (to to-k)) (move label (to text))))"
)
BASE = SCENE + " " + FADE + " " + STOP


def same(a: str, b: str) -> None:
    assert write(compile_source(a)) == write(compile_source(b))


def test_a_use_in_a_button_is_the_hand_written_animation():
    same(
        BASE + " (button b (animation (fade-in c)))",
        BASE + " (button b (animation (move c.opacity (to 1) (duration 0.4))))",
    )


def test_a_use_may_stand_as_the_animation_itself():
    same(BASE + " (button b (fade-in c))", BASE + " (button b (animation (fade-in c)))")
    same(
        BASE + " (canvas v s (on-click c (fade-in d 2)))",
        BASE + " (canvas v s (on-click c (animation (fade-in d 2))))",
    )


def test_a_use_stands_among_the_optional_arguments():
    same(
        BASE + " (button b (fade-in c) (label 'go') (<= c.opacity 1))",
        BASE + " (button b (label 'go') (animation (fade-in c)) (<= c.opacity 1))",
    )


def test_the_mtpc_holds_no_trace_of_the_choreo():
    d = doc(BASE + " (button b (fade-in c))")
    assert "fade-in" not in str(d)
    assert errors(d) == []


def test_arguments_in_order_and_defaults():
    same(
        BASE + " (play p (animation (stop 120 'a third' 10)))",
        BASE + " (play p (animation (at-once (defaults (duration 10))"
        " (move k (to 120)) (move label (to 'a third')))))",
    )
    same(
        BASE + " (play p (animation (stop 90)))",
        BASE + " (play p (animation (at-once (defaults (duration 8))"
        " (move k (to 90)) (move label (to '')))))",
    )


def test_a_named_animation_made_from_one_use():
    m = model(BASE + " (animation third (stop 120 'a third' 10)) (play p (animation third))")
    assert m.get("third").attrs["duration"].value == 10
    same(
        BASE + " (animation third (stop 120 'a third' 10))",
        BASE + " (animation third (at-once (defaults (duration 10))"
        " (move k (to 120)) (move label (to 'a third'))))",
    )


def test_each_use_in_a_stepper_is_one_step():
    same(
        BASE + " (stepper st (animation (fade-in c) (stop 1 'one' 2)))",
        BASE + " (stepper st (animation (move c.opacity (to 1) (duration 0.4))"
        " (at-once (defaults (duration 2)) (move k (to 1)) (move label (to 'one')))))",
    )


def test_a_use_of_several_items_is_one_step_as_a_named_animation_is():
    two = "(choreo both ((shape a) (shape b)) (fade-in a) (fade-in b))"
    same(
        BASE + f" {two} (stepper st (animation (both c d) (wait 1)))",
        BASE + " (stepper st (animation (in-order (move c.opacity (to 1) (duration 0.4))"
        " (move d.opacity (to 1) (duration 0.4))) (wait 1)))",
    )


def test_a_use_alone_gives_its_steps():
    tour = "(choreo tour () (move k (to 1) (duration 1)) (move k (to 0) (duration 1)))"
    same(
        BASE + f" {tour} (play p (animation (tour)))",
        BASE + " (play p (animation (move k (to 1) (duration 1)) (move k (to 0) (duration 1))))",
    )
    same(BASE + f" {tour} (play p (tour))", BASE + f" {tour} (play p (animation (tour)))")


def test_nested_uses_pass_their_parameters_on():
    pair = "(choreo pair ((shape a) (shape b) (real t 1)) (at-once (fade-in a t) (fade-in b t)))"
    same(
        BASE + f" {pair} (button go (pair c d 3))",
        BASE + " (button go (animation (at-once (move c.opacity (to 1) (duration 3))"
        " (move d.opacity (to 1) (duration 3)))))",
    )


def test_a_parameter_given_a_variable_is_its_target():
    bump = "(choreo bump ((real x) (real to 1)) (move x (to to) (duration 1)))"
    same(
        SCENE + f" {bump} (button b (bump k 5))",
        SCENE + " (button b (animation (move k (to 5) (duration 1))))",
    )
    same(
        SCENE + f" {bump} (button b (bump c.r))",
        SCENE + " (button b (animation (move c.r (to 1) (duration 1))))",
    )


def test_a_variable_given_as_a_value_is_read_when_the_move_starts():
    same(
        BASE + " (real j 0) (button b (stop j))",
        BASE + " (real j 0) (button b (animation (at-once (defaults (duration 8))"
        " (move k (to j)) (move label (to '')))))",
    )


def test_eases_and_functions_as_arguments():
    src = (
        "(func[real] sq ((real t)) (* t t)) (real k 0)"
        " (choreo go ((real to-k 1) (func[(real (>= 0) (<= 1)) real] curve sq))"
        " (move k (to to-k) (duration 1) (ease curve)))"
    )
    same(
        src + " (button b (go 2))",
        src + " (button b (animation (move k (to 2) (duration 1) (ease sq))))",
    )


def test_constants_and_known_values_as_arguments():
    same(
        BASE + " (list xs [1 2] (const)) (button b (stop xs[1] $'at {(* 2 3)}'))",
        BASE + " (list xs [1 2] (const)) (button b (animation (at-once (defaults (duration 8))"
        " (move k (to xs[1])) (move label (to 'at 6')))))",
    )


def test_a_choreo_with_a_loop_and_defaults():
    pulse = (
        "(choreo pulse ((shape who)) (defaults (duration 0.5)) (loop 2)"
        " (move who.opacity (to 0)) (move who.opacity (to 1)))"
    )
    m = model(BASE + f" {pulse} (animation a (pulse c))")
    assert m.get("a").attrs["duration"].value == 2


def test_a_choreo_keeps_its_doc_in_the_compiler():
    m = model(SCENE + " (choreo fade ((shape who)) doc@'Fades in.' (move who.opacity (to 1)))")
    assert m.docs[("choreo", "fade")] == "Fades in."


def test_uses_in_a_foreach():
    same(
        BASE + " (play p (animation (foreach w [c d] (fade-in w))))",
        BASE + " (play p (animation (fade-in c) (fade-in d)))",
    )


MAYBE = "(bool show true) (scene s (circle|none gone (r 1)) (exists-when gone show))"


def test_a_shape_that_may_not_exist_is_an_argument_as_in_the_inline_move():
    # mtp-0eha: a use is the inline animation, and a function's plain parameter takes an
    # argument that may be none too (type-system.md 5.c).
    fade = "(choreo fade-out ((shape x)) (move x.opacity (to 0) (duration 1)))"
    same(
        MAYBE + f" {fade} (play p (animation (fade-out gone))) (canvas v s)",
        MAYBE + " (play p (animation (move gone.opacity (to 0) (duration 1)))) (canvas v s)",
    )


def test_a_value_that_may_be_none_is_an_argument_as_in_the_inline_move():
    bump = "(choreo bump ((real x) (real to 1)) (move x (to to) (duration 1)))"
    same(
        "(real|none m 2)" + f" {bump} (button b (bump m))",
        "(real|none m 2) (button b (animation (move m (to 1) (duration 1))))",
    )


def test_an_argument_that_may_be_none_is_refused_where_the_inline_move_refuses_it():
    error(
        "(real|none m 2) (real k 0)"
        " (choreo bump ((real to 1)) (move k (to to) (duration 1))) (button b (bump m))",
        "may be none",
    )
    error(
        "(real|none m 2) (real k 0) (button b (animation (move k (to m) (duration 1))))",
        "may be none",
    )


def test_the_examples_pass_the_schema():
    assert (
        errors(doc(BASE + " (animation third (stop 120)) (play p (animation third (fade-in c)))"))
        == []
    )


@pytest.mark.parametrize(
    "src, msg",
    [
        # Arguments.
        (BASE + " (button b (fade-in))", "fade-in takes 1 to 2 arguments, got 0"),
        (BASE + " (button b (fade-in c 1 2))", "fade-in takes 1 to 2 arguments, got 3"),
        (BASE + " (button b (stop 1 2 3 4))", "stop takes up to 3 arguments, got 4"),
        (BASE + " (button b (fade-in 3))", "expected shape"),
        (BASE + " (button b (stop 'one'))", "expected real"),
        (BASE + " (button b (stop (* 2 k)))", "known when compiling"),
        (BASE + " (button b (fade-in c (seconds 2)))", "written in order, without names"),
        # Where a use may be written.
        (BASE + " (fade-in c)", "declares an animation"),
        (BASE + " (real v (fade-in c))", "declares an animation"),
        ("(real k 0) (choreo f () (wait 1)) (scene t (f))", "declares an animation"),
        ("(real k 0) (choreo f () (wait 1)) (scene t (group g (f)))", "declares an animation"),
        (
            "(real k 0) (choreo f () (wait 1)) (motif m () (f)) (scene t (m a))",
            "declares an animation",
        ),
        ("(real k 0) (choreo f () (wait 1)) (foreach i 2 (f))", "declares an animation"),
        (BASE + " (canvas v s (fade-in c))", "a canvas plays no animation"),
        (BASE + " (slider sl (fade-in c))", "a slider plays no animation"),
        (BASE + " (button b (fade-in c) (animation (wait 1)))", "'animation' is given twice"),
        # Names that are not choreos.
        (BASE + " (button b (animation (fade c)))", "'fade' is not a choreo"),
        (BASE + " (play p (animation (wait 1) (fade c)))", "'fade' is not a choreo"),
        (BASE + " (button b (fade c))", "'fade' is not a choreo"),
        # Declarations.
        (SCENE + " (choreo f ((real x)))", "a choreo holds what an animation's body holds"),
        (SCENE + " (choreo move () (wait 1))", "'move' is reserved"),
        (SCENE + " (choreo wait () (wait 1))", "'wait' is already a form"),
        (SCENE + " (choreo f () (wait 1)) (choreo f () (wait 1))", "already declared"),
        (BASE + " (choreo f () (circle e))", "an animation holds moves"),
        # A choreo that uses itself.
        (SCENE + " (choreo f () (wait 1) (f))", "the choreo 'f' uses itself"),
        (
            SCENE + " (choreo f ((shape a)) (g a)) (choreo g ((shape a)) (f a))",
            "the choreo 'g' uses itself, through 'f'",
        ),
        (
            SCENE + " (choreo f () (at-once (g))) (choreo g () (in-order (h))) (choreo h () (f))",
            "the choreo 'h' uses itself, through 'f' and 'g'",
        ),
        # A motif makes shapes only.
        (
            "(real k 0) (motif m () (animation (move k (to 1))))",
            "a motif makes shapes; for a template of animations, use choreo",
        ),
    ],
)
def test_errors(src, msg):
    error(src, msg)


def test_a_choreo_uses_only_choreos_declared_before_it():
    error(
        SCENE + " (choreo f ((shape a)) (g a)) (choreo g ((shape a)) (fade a))"
        " (choreo fade ((shape a)) (move a.opacity (to 1))) (button b (f c))",
        "'g' is declared after 'f'",
    )


def test_a_trial_shows_a_body_error_with_no_use():
    error(SCENE + " (choreo f ((real t 1)) (move nope (to t)))", "unknown name 'nope'")
