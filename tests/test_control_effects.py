"""A slider, a button, a play and a stepper take their movement, EFFECT, as a positional argument
right after their name (the author, 2026-11-23)."""

import json
from pathlib import Path

import pytest
from helpers import doc, error

K = "(real k 0 (>= 0) (<= 10))"
# The .mtpc that each control compiled to when it took its movement in (animation …), recorded
# before the change, with the source that it was compiled from.
BEFORE = json.loads((Path(__file__).parent / "control_effects.json").read_text())
NEW = {
    "slider": f"{K} (slider s (move k (from 0) (to 1) (duration 0)) (label 'k'))",
    "button": f"{K} (button b (move k (to 1) (duration 2)) (label 'go'))",
    "play": f"{K} (play p (in-order (move k (to 1) (duration 1)) (move k (to 0) (duration 1)))"
    " (buttons true))",
    "stepper": f"{K} (stepper s (in-order (move k (to 1) (duration 1)) (wait 1)) (label 'n'))",
    "named": f"{K} (animation a (move k (to 1) (duration 1))) (button b a)",
}


@pytest.mark.parametrize("kind", NEW)
def test_a_positional_effect_compiles_as_the_animation_did(kind):
    assert doc(NEW[kind]) == BEFORE[kind]["mtpc"]


@pytest.mark.parametrize(
    "src, shown",
    [
        (
            f"{K} (slider s (animation (move k (from 0) (to 1) (duration 0))))",
            r"\(slider s \(move k \(from 0\) \(to 1\) \(duration 0\)\)",
        ),
        (f"{K} (button b (animation (move k (to 1) (duration 2))))", r"\(button b \(move "),
        (f"{K} (play p (animation (move k (to 1) (duration 2))))", r"\(play p \(move "),
        (f"{K} (stepper s (animation (move k (to 1) (duration 2))))", r"\(stepper s \(move "),
        (
            f"{K} (button b (label 'go') (animation (move k (to 1) (duration 2))))",
            r"\(button b \(move ",
        ),
    ],
)
def test_animation_on_a_control_is_an_error_that_shows_the_new_form(src, shown):
    error(src, shown)


@pytest.mark.parametrize(
    "src",
    [
        f"{K} (slider s (label 'k'))",
        f"{K} (slider s)",
        f"{K} (button b (label 'go'))",
        f"{K} (button b)",
        f"{K} (play p (buttons true))",
        f"{K} (stepper s (label 'n'))",
    ],
)
def test_a_control_without_an_effect_is_an_error(src):
    error(src, "right after its name")


@pytest.mark.parametrize(
    "src",
    [
        f"{K} (button b (label 'go') (move k (to 1) (duration 2)))",
        f"{K} (play p (buttons true) (move k (to 1) (duration 2)))",
        f"{K} (slider s (label 'k') (move k (from 0) (to 1) (duration 0)))",
    ],
)
def test_the_effect_comes_right_after_the_name(src):
    error(src, "right after its name")


@pytest.mark.parametrize(
    "effect",
    [
        "(move k (to 1) (duration 2))",
        "(wait 1)",
        "(in-order (move k (to 1) (duration 1)) (wait 1))",
        "(at-once (move k (to 1) (duration 1)) (move j (to 1) (duration 1)))",
        "a",
        "(pulse)",
    ],
)
@pytest.mark.parametrize("kind", ["button", "play", "stepper"])
def test_each_movement_is_an_effect(kind, effect):
    src = (
        f"{K} (real j 0) (animation a (move k (to 1) (duration 1)))"
        " (choreo pulse () (move k (to 2) (duration 1)))"
        f" (scene sc (circle c (r k))) ({kind} x {effect})"
    )
    d = doc(src)
    (x,) = [o for o in d["objects"] if o["kind"] == kind]
    assert d["objects"][x["animation"]]["kind"] == "animation"


def test_a_slider_effect_is_one_instant_move():
    error(f"{K} (slider s (move k (from 0) (to 1) (duration 1)))", r"\(duration 0\)")
    error(f"{K} (slider s (wait 1))", "one instant move")
