import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import Any


def exact(x) -> bool:
    return isinstance(x, (int, Fraction)) and not isinstance(x, bool)


def divide(a, b):
    if b == 0:
        raise ZeroDivisionError
    return Fraction(a) / b if exact(a) and exact(b) else a / b


def power(base, exp):
    if isinstance(exp, int) and exact(base):
        return Fraction(base) ** exp if exp < 0 else base**exp
    return base**exp


def _sqrt(x: float) -> float:
    if x < 0:
        raise ValueError("sqrt of a negative number")
    return math.sqrt(x)


@dataclass(frozen=True)
class Signature:
    # Each parameter is "real" (a number that widens to real) or "point" (an object with x, y).
    params: tuple[str, ...]
    result: str
    impl: Callable[..., Any]


@dataclass(frozen=True)
class Function:
    signatures: tuple[Signature, ...]
    # Impure functions are never folded at compile time, and their impl takes the rng first.
    pure: bool = True

    def find(self, kinds: list[str]) -> Signature | None:
        return next((s for s in self.signatures if list(s.params) == kinds), None)


STDLIB: dict[str, Function] = {
    "dist": Function(
        (
            Signature(("point", "point"), "real", lambda a, b: math.dist(a, b)),
            Signature(("real",) * 4, "real", lambda x1, y1, x2, y2: math.dist((x1, y1), (x2, y2))),
        )
    ),
    "sqrt": Function((Signature(("real",), "real", _sqrt),)),
    "rand": Function(
        (
            Signature((), "real", lambda rng: rng.random()),
            Signature(("real", "real"), "real", lambda rng, a, b: rng.uniform(a, b)),
        ),
        pure=False,
    ),
}


def call(fn: Function, sig: Signature, args: list, rng: random.Random | None = None):
    values = [
        tuple(map(float, a)) if kind == "point" else float(a)
        for kind, a in zip(sig.params, args, strict=True)
    ]
    return sig.impl(rng, *values) if not fn.pure else sig.impl(*values)
