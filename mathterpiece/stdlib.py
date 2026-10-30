import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from mathterpiece import colors
from mathterpiece.matrix import Matrix


def exact(x) -> bool:
    return isinstance(x, (int, Fraction)) and not isinstance(x, bool)


def divide(a, b):
    if b == 0:
        raise ZeroDivisionError
    return Fraction(a) / b if exact(a) and exact(b) else a / b


# Lists are points (or any run of numbers): arithmetic on them works element by element.
def add(a, b):
    if isinstance(a, tuple):
        return tuple(x + y for x, y in zip(a, b, strict=True))
    return a + b


def subtract(a, b):
    if isinstance(a, tuple):
        return tuple(x - y for x, y in zip(a, b, strict=True))
    return a - b


def negate(a):
    return tuple(-x for x in a) if isinstance(a, tuple) else -a


def multiply(a, b):
    if isinstance(a, tuple):
        return tuple(x * b for x in a)
    if isinstance(b, tuple):
        return tuple(a * y for y in b)
    return a * b


def divide_any(a, b):
    if isinstance(a, tuple):
        return tuple(divide(x, b) for x in a)
    return divide(a, b)


def show(value) -> str:
    if isinstance(value, tuple):
        return "(" + ", ".join(str(x) for x in value) + ")"
    return str(value)


def power(base, exp):
    if isinstance(exp, int) and exact(base):
        return Fraction(base) ** exp if exp < 0 else base**exp
    return base**exp


def _sqrt(x: float) -> float:
    if x < 0:
        raise ValueError("sqrt of a negative number")
    return math.sqrt(x)


# math.sin(math.pi) is 1.2e-16, not 0, so right angles in degrees are looked up instead.
_RIGHT_ANGLE_SIN = {0: 0.0, 90: 1.0, 180: 0.0, 270: -1.0}


def _sind(deg: float) -> float:
    return _RIGHT_ANGLE_SIN.get(deg % 360, math.sin(math.radians(deg)))


def _cosd(deg: float) -> float:
    return _sind(deg + 90)


def _tand(deg: float) -> float:
    if deg % 180 == 90:
        raise ValueError("tand is undefined at 90 degrees plus a multiple of 180")
    return 0.0 if deg % 180 == 0 else math.tan(math.radians(deg))


def _rotate(deg: float) -> Matrix:
    c, s = _cosd(deg), _sind(deg)
    return Matrix(((c, -s, 0), (s, c, 0), (0, 0, 1)))


def _scale(sx: float, sy: float | None = None) -> Matrix:
    return Matrix(((sx, 0, 0), (0, sx if sy is None else sy, 0), (0, 0, 1)))


def translate(dx: float, dy: float) -> Matrix:
    return Matrix(((1, 0, dx), (0, 1, dy), (0, 0, 1)))


def _polar(r: float, deg: float) -> tuple[float, float]:
    return r * _cosd(deg), r * _sind(deg)


def _to_polar(p: tuple[float, ...]) -> tuple[float, float]:
    if len(p) != 2:
        raise ValueError("to-polar takes a point of two numbers")
    x, y = p
    if x == 0 and y == 0:
        raise ValueError("to-polar has no angle at the origin")
    return math.hypot(x, y), math.degrees(math.atan2(y, x))


def _real(fn: Callable[[float], float]) -> "Function":
    return Function((Signature(("real",), "real", fn),))


@dataclass(frozen=True)
class Signature:
    # Each parameter is "real" (a number that widens to real), "point" (an object with x, y, or a
    # list of numbers) or "color" (a color, or a string naming one). A "point" result has as many
    # numbers as the point arguments.
    params: tuple[str, ...]
    result: str
    impl: Callable[..., Any]


@dataclass(frozen=True)
class Function:
    signatures: tuple[Signature, ...]
    # Impure functions are never folded at compile time, and their impl takes the rng first.
    pure: bool = True
    # A variadic function's one signature takes any number (at least one) of its one parameter.
    variadic: bool = False

    def find(self, kinds: list[str]) -> Signature | None:
        if self.variadic:
            sig = self.signatures[0]
            return sig if kinds and all(k == sig.params[0] for k in kinds) else None
        return next((s for s in self.signatures if list(s.params) == kinds), None)


STDLIB: dict[str, Function] = {
    "dist": Function(
        (
            Signature(("point", "point"), "real", lambda a, b: math.dist(a, b)),
            Signature(("real",) * 4, "real", lambda x1, y1, x2, y2: math.dist((x1, y1), (x2, y2))),
        )
    ),
    "sqrt": _real(_sqrt),
    "mix": Function((Signature(("color", "color", "real"), "paint", colors.mix),)),
    "lighten": Function(
        (Signature(("color", "real"), "paint", lambda c, t: colors.mix(c, "white", t)),)
    ),
    "darken": Function(
        (Signature(("color", "real"), "paint", lambda c, t: colors.mix(c, "black", t)),)
    ),
    "max": Function((Signature(("real",), "real", lambda *xs: float(max(xs))),), variadic=True),
    "min": Function((Signature(("real",), "real", lambda *xs: float(min(xs))),), variadic=True),
    "rad": _real(math.degrees),
    "deg": _real(lambda x: x),
    "turn": _real(lambda x: 360 * x),
    "to-rad": _real(math.radians),
    "to-turn": _real(lambda x: x / 360),
    "sin": _real(math.sin),
    "cos": _real(math.cos),
    "tan": _real(math.tan),
    "asin": _real(math.asin),
    "acos": _real(math.acos),
    "atan": _real(math.atan),
    "sind": _real(_sind),
    "cosd": _real(_cosd),
    "tand": _real(_tand),
    "asind": _real(lambda x: math.degrees(math.asin(x))),
    "acosd": _real(lambda x: math.degrees(math.acos(x))),
    "atand": _real(lambda x: math.degrees(math.atan(x))),
    "lerp": Function(
        (
            Signature(("real",) * 3, "real", lambda a, b, t: a + (b - a) * t),
            Signature(
                ("point", "point", "real"),
                "point",
                lambda a, b, t: tuple(x + (y - x) * t for x, y in zip(a, b, strict=True)),
            ),
        )
    ),
    "polar": Function((Signature(("real", "real"), "list2", _polar),)),
    "to-polar": Function((Signature(("point",), "list2", _to_polar),)),
    "rotate": Function((Signature(("real",), "transform", _rotate),)),
    "scale": Function(
        (
            Signature(("real",), "transform", _scale),
            Signature(("real", "real"), "transform", _scale),
        )
    ),
    "translate": Function((Signature(("real", "real"), "transform", translate),)),
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
        tuple(map(float, a)) if kind == "point" else a if kind == "color" else float(a)
        for kind, a in zip(sig.params * len(args) if fn.variadic else sig.params, args, strict=True)
    ]
    return sig.impl(rng, *values) if not fn.pure else sig.impl(*values)
