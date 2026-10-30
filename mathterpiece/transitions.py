"""Transitions: pure trajectories through a value's states, as the compiler knows them.

A transition goes from a start to an end along a path, with an ease that decides how time runs
through it, over a duration in seconds. Any part may be left out; whatever uses the transition
fills in what it can and the compiler reports what is still missing where it is needed.
"""

from dataclasses import dataclass
from typing import Any

# An ease is a built-in name ('linear', 'ease-in', ...), ("step", c), or ("func", name).
type Ease = str | tuple[str, Any]
# A path is ("func", name): a function of the start, the end and the eased progress.
type Path = tuple[str, str]


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
