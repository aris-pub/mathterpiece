"""Transitions: pure trajectories through a value's states, as the compiler knows them.

A transition goes from a start to an end along a path, with an ease that decides how time runs
through it, over a duration in seconds. Any part may be left out; whatever uses the transition
fills in what it can and the compiler reports what is still missing where it is needed.
"""

from dataclasses import dataclass
from typing import Any

from mathterpiece.nodes import Node

# An ease is a built-in name ('linear', 'ease-in', ...), ("step", c), or ("func", name).
type Ease = str | tuple[str, Any]
# A path is ("func", name): a function of the start, the end and the eased progress.
type Path = tuple[str, str]


# An end that reads the scene: evaluated once, when the transition starts.
@dataclass(frozen=True)
class Expr:
    node: Node


@dataclass(frozen=True)
class Single:
    frm: Any = None
    to: Any = None
    duration: float | None = None
    ease: Ease | None = None
    path: Path | None = None
    # The type of the values it moves through, known from its ends; None if it has none.
    elem: str | None = None


# Stays where it is for a duration: the trajectory that changes nothing.
@dataclass(frozen=True)
class Wait:
    duration: float


# Its parts glued end to end. default_duration and default_ease fill in parts without their own;
# ease warps time across the whole sequence.
@dataclass(frozen=True)
class Sequence:
    parts: tuple["Transition", ...]
    ease: Ease | None = None
    default_duration: float | None = None
    default_ease: Ease | None = None
    elem: str | None = None


type Transition = Single | Wait | Sequence


def reads_scene(t: Transition) -> bool:
    if isinstance(t, Single):
        return isinstance(t.frm, Expr) or isinstance(t.to, Expr)
    if isinstance(t, Sequence):
        return any(reads_scene(p) for p in t.parts)
    return False
