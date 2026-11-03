"""The built-in functions (docs/reference.md "Functions"): what each takes and gives, how it is
folded when its inputs are known, its range, and where it is undefined (type-system.md 5.c)."""

import math
import sys
from collections.abc import Callable
from dataclasses import dataclass

from mathterpiece import colors
from mathterpiece.types import COLOR, INT, POINT, REAL, TRANSFORM, Refine, Type

MAX_REAL = sys.float_info.max
# A function's whole range, for a number with no limit of its own: every number lies within
# ±10^150 (type-system.md, "What the compiler proves").
WHOLE = (-1e150, 1e150)
UNIT = Refine(REAL, ((">=", 0), ("<=", 1)))
Range = tuple[float, float]


class Undefined(Exception):
    """A built-in called where it is undefined."""


@dataclass(frozen=True)
class Builtin:
    params: tuple[Type, ...]
    result: Type
    fold: Callable
    # The result's range: a function of the inputs' ranges, or a fixed range.
    range: Callable | Range | None = WHOLE
    # Whether inputs within these ranges may reach a point where it is undefined.
    undefined: Callable | None = None


def _check(ok: bool) -> None:
    if not ok:
        raise Undefined


# math.sin(math.pi) is 1.2e-16, not 0, so right angles in degrees are looked up instead.
_RIGHT_ANGLE_SIN = {0: 0.0, 90: 1.0, 180: 0.0, 270: -1.0}


def sind(deg: float) -> float:
    return _RIGHT_ANGLE_SIN.get(deg % 360, math.sin(math.radians(deg)))


def cosd(deg: float) -> float:
    return sind(deg + 90)


def _ratio(a: float, b: float) -> float:
    _check(b != 0)
    return a / b


def _hits(r: Range, period: float, offset: float) -> bool:
    """Whether some offset + k * period lies in the range."""
    k = math.ceil((r[0] - offset) / period)
    return offset + k * period <= r[1]


def _outside(r: Range, lo: float, hi: float) -> bool:
    return r[0] < lo or r[1] > hi


def _inside_open(r: Range, lo: float, hi: float) -> bool:
    """Whether the range meets the open interval (lo, hi)."""
    return r[0] < hi and r[1] > lo


def _asin(x: float) -> float:
    _check(-1 <= x <= 1)
    return math.asin(x)


def _acos(x: float) -> float:
    _check(-1 <= x <= 1)
    return math.acos(x)


def _arc(x: float) -> float:
    _check(abs(x) >= 1)
    return 1 / x


D = math.degrees
HALF_PI = math.pi / 2


def _unary(fold, rng=WHOLE, undefined=None, result=REAL) -> Builtin:
    return Builtin((REAL,), result, fold, rng, undefined)


def _sqrt_range(rs):
    lo, hi = rs[0]
    return (math.sqrt(max(lo, 0)), math.sqrt(max(hi, 0)))


def _exp(x: float) -> float:
    try:
        return math.exp(x)
    except OverflowError:
        raise Undefined from None


def _sqrt(x: float) -> float:
    _check(x >= 0)
    return math.sqrt(x)


def _to_polar(p) -> tuple:
    x, y = p
    _check(x != 0 or y != 0)
    return (math.hypot(x, y), math.degrees(math.atan2(y, x)))


def _rotate(deg: float) -> tuple:
    c, s = cosd(deg), sind(deg)
    return (c, s, -s, c, 0, 0)


def compose(*ts) -> tuple:
    """Transforms as (a b c d e f), x' = a x + c y + e and y' = b x + d y + f, the first applied
    first."""
    a, b, c, d, e, f = 1, 0, 0, 1, 0, 0
    for a2, b2, c2, d2, e2, f2 in ts:
        a, b, c, d, e, f = (
            a2 * a + c2 * b,
            b2 * a + d2 * b,
            a2 * c + c2 * d,
            b2 * c + d2 * d,
            a2 * e + c2 * f + e2,
            b2 * e + d2 * f + f2,
        )
    return (a, b, c, d, e, f)


BUILTINS: dict[str, Builtin] = {
    "sqrt": _unary(_sqrt, _sqrt_range, lambda rs: rs[0][0] < 0),
    "floor": _unary(
        math.floor, lambda rs: (math.floor(rs[0][0]), math.floor(rs[0][1])), result=INT
    ),
    "ceil": _unary(math.ceil, lambda rs: (math.ceil(rs[0][0]), math.ceil(rs[0][1])), result=INT),
    "exp": _unary(_exp, (0.0, MAX_REAL), lambda rs: rs[0][1] > math.log(MAX_REAL)),
    "sin": _unary(math.sin, (-1.0, 1.0)),
    "cos": _unary(math.cos, (-1.0, 1.0)),
    "tan": _unary(math.tan),
    "sec": _unary(lambda x: _ratio(1, math.cos(x))),
    "csc": _unary(lambda x: _ratio(1, math.sin(x)), WHOLE, lambda rs: rs[0][0] <= 0 <= rs[0][1]),
    "cot": _unary(
        lambda x: _ratio(math.cos(x), math.sin(x)), WHOLE, lambda rs: rs[0][0] <= 0 <= rs[0][1]
    ),
    "sind": _unary(sind, (-1.0, 1.0)),
    "cosd": _unary(cosd, (-1.0, 1.0)),
    "tand": _unary(lambda x: _ratio(sind(x), cosd(x)), WHOLE, lambda rs: _hits(rs[0], 180, 90)),
    "secd": _unary(lambda x: _ratio(1, cosd(x)), WHOLE, lambda rs: _hits(rs[0], 180, 90)),
    "cscd": _unary(lambda x: _ratio(1, sind(x)), WHOLE, lambda rs: _hits(rs[0], 180, 0)),
    "cotd": _unary(lambda x: _ratio(cosd(x), sind(x)), WHOLE, lambda rs: _hits(rs[0], 180, 0)),
    "asin": _unary(_asin, (-HALF_PI, HALF_PI), lambda rs: _outside(rs[0], -1, 1)),
    "acos": _unary(_acos, (0.0, math.pi), lambda rs: _outside(rs[0], -1, 1)),
    "atan": _unary(math.atan, (-HALF_PI, HALF_PI)),
    "acot": _unary(lambda x: HALF_PI - math.atan(x), (0.0, math.pi)),
    "asec": _unary(
        lambda x: math.acos(_arc(x)), (0.0, math.pi), lambda rs: _inside_open(rs[0], -1, 1)
    ),
    "acsc": _unary(
        lambda x: math.asin(_arc(x)), (-HALF_PI, HALF_PI), lambda rs: _inside_open(rs[0], -1, 1)
    ),
    "asind": _unary(lambda x: D(_asin(x)), (-90.0, 90.0), lambda rs: _outside(rs[0], -1, 1)),
    "acosd": _unary(lambda x: D(_acos(x)), (0.0, 180.0), lambda rs: _outside(rs[0], -1, 1)),
    "atand": _unary(lambda x: D(math.atan(x)), (-90.0, 90.0)),
    "acotd": _unary(lambda x: 90 - D(math.atan(x)), (0.0, 180.0)),
    "asecd": _unary(
        lambda x: D(math.acos(_arc(x))), (0.0, 180.0), lambda rs: _inside_open(rs[0], -1, 1)
    ),
    "acscd": _unary(
        lambda x: D(math.asin(_arc(x))), (-90.0, 90.0), lambda rs: _inside_open(rs[0], -1, 1)
    ),
    "rad": _unary(math.degrees),
    "turn": _unary(lambda x: 360 * x),
    "deg": _unary(lambda x: x),
    "to-rad": _unary(math.radians),
    "to-turn": _unary(lambda x: x / 360),
    "polar": Builtin((REAL, REAL), POINT, lambda r, a: (r * cosd(a), r * sind(a)), None),
    "to-polar": Builtin((POINT,), POINT, _to_polar, None, lambda rs: True),
    "dist": Builtin((POINT, POINT), REAL, lambda p, q: math.dist(p, q), (0.0, MAX_REAL)),
    "rotate": Builtin((REAL,), TRANSFORM, _rotate, None),
    "translate": Builtin((REAL, REAL), TRANSFORM, lambda dx, dy: (1, 0, 0, 1, dx, dy), None),
    "mix": Builtin((COLOR, COLOR, UNIT), COLOR, colors.mix, None),
    "lighten": Builtin((COLOR, UNIT), COLOR, lambda c, t: colors.mix(c, "#ffffffff", t), None),
    "darken": Builtin((COLOR, UNIT), COLOR, lambda c, t: colors.mix(c, "#000000ff", t), None),
}

# Built-ins whose arguments vary in number or type, handled by the compiler itself.
SPECIAL_BUILTINS = {"round", "log", "min", "max", "lerp", "rand", "scale", "transform"}
CONSTANTS = {
    "pi": math.pi,
    "π": math.pi,
    "tau": math.tau,
    "τ": math.tau,
    "euler": math.e,
    "infty": math.inf,
    "∞": math.inf,
}
