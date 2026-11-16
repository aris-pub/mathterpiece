"""The built-in functions (docs/reference.md "Functions"): what each takes and gives, how it is
folded when its inputs are known, its range, and where it is undefined (type-system.md 5.c)."""

import cmath
import math
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from mathterpiece import colors
from mathterpiece.types import COLOR, INT, POINT, REAL, TRANSFORM, Refine, Type

# Every number lies within -10^150 to 10^150 (Rule number-limit, docs/spec/evaluation.md). An int
# or a ratio is clamped to exactly 10^150, and a real to 1e150, the binary64 number nearest to it.
EXACT_LIMIT = 10**150
LIMIT = 1e150
# A function's whole range, for a number with no limit of its own.
WHOLE = (-LIMIT, LIMIT)
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


def clamp(v):
    """v with each of its numbers clamped to the number limit: an int, a ratio, a real, each part
    of a complex, and each number of a point or a list. A NaN has no exact value to clamp, so it
    is undefined."""
    if isinstance(v, bool):
        return v
    if isinstance(v, float):
        _check(not math.isnan(v))
        return min(max(v, -LIMIT), LIMIT)
    if isinstance(v, int):
        return min(max(v, -EXACT_LIMIT), EXACT_LIMIT)
    if isinstance(v, Fraction):
        return v if abs(v) <= EXACT_LIMIT else Fraction(EXACT_LIMIT if v > 0 else -EXACT_LIMIT)
    if isinstance(v, complex):
        return complex(clamp(v.real), clamp(v.imag))
    if isinstance(v, tuple):
        return tuple(clamp(x) for x in v)
    if isinstance(v, list):
        return [clamp(x) for x in v]
    return v


def finite(v) -> bool:
    if isinstance(v, float):
        return math.isfinite(v)
    if isinstance(v, complex):
        return cmath.isfinite(v)
    return True


def _ldexp(m: float, e: int) -> float:
    try:
        return math.ldexp(m, e)
    except OverflowError:
        return math.copysign(math.inf, m)


def scaled_product(vals: list):
    """The product of reals or complex numbers from left to right, with the binary exponent kept
    apart from the mantissas. A step of the plain product past the largest binary64 number gives
    an infinity, which no later factor can bring back within the number limit. Scaling by a power
    of 2 is exact, so while no step of the plain product overflows or underflows, the two are
    equal. web/src/builtins.ts computes it in the same steps."""
    if not any(isinstance(v, complex) for v in vals):
        m, e = 1.0, 0
        for v in vals:
            f, k = math.frexp(float(v))
            m, j = math.frexp(m * f)
            e += k + j
        return _ldexp(m, e)
    re, im, e = 1.0, 0.0, 0
    for v in vals:
        c = complex(v)
        _, k = math.frexp(max(abs(c.real), abs(c.imag)))
        a, b = math.ldexp(c.real, -k), math.ldexp(c.imag, -k)
        re, im = re * a - im * b, re * b + im * a
        _, j = math.frexp(max(abs(re), abs(im)))
        re, im, e = math.ldexp(re, -j), math.ldexp(im, -j), e + k + j
    return complex(_ldexp(re, e), _ldexp(im, e))


def product(vals: list):
    """The product of vals as an operation gives it: from left to right, and clamped once."""
    out = vals[0]
    for v in vals[1:]:
        out *= v
    if not finite(out):
        out = scaled_product(vals)
    return clamp(out)


def power(a, b):
    """a to the power b, before it is clamped. The caller has checked that a value exists."""
    if isinstance(a, complex) or isinstance(b, complex):
        try:
            return a**b
        except OverflowError:
            return _polar_power(complex(a), complex(b))
    negative = a < 0 and float(b).is_integer() and int(b) % 2 == 1
    if isinstance(a, (int, Fraction)) and isinstance(b, int) and abs(a) not in (0, 1):
        # An exact power past the limit by far has too many digits to work out, so its size is
        # found from logarithms first. 520 bits leaves room for their rounding above 10^150.
        if b * (math.log2(abs(a.numerator)) - math.log2(a.denominator)) > 520:
            return type(a)(-EXACT_LIMIT if negative else EXACT_LIMIT)
    try:
        return a**b
    except OverflowError:
        return -math.inf if negative else math.inf


def _polar_power(x: complex, y: complex) -> complex:
    """x to the power y from |x| and the angle of x, as web/src/builtins.ts computes it, for a
    result past the largest binary64 number. Each part is found from its logarithm, so a part
    that is exactly 0 stays 0."""
    lnr = math.log(abs(x))
    theta = math.atan2(x.imag, x.real)
    lnm = y.real * lnr - y.imag * theta
    angle = y.imag * lnr + y.real * theta

    def part(t: float) -> float:
        if t == 0:
            return 0.0
        try:
            return math.copysign(math.exp(lnm + math.log(abs(t))), t)
        except OverflowError:
            return math.copysign(math.inf, t)

    return complex(part(math.cos(angle)), part(math.sin(angle)))


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
        return LIMIT


def _exp_range(rs):
    """exp grows with its input, so the ends of the input's range give the result's (the
    author, 2026-11-03)."""
    lo, hi = rs[0]
    return (clamp(_exp(lo)), clamp(_exp(hi)))


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


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


# More items than this is undefined: a figure has no use for them, and a page would hang.
RANGE_LIMIT = 1_000_000


def range_by_gap(start, stop, gap) -> list:
    """From start, a gap apart, up to stop and not including it (mtp-966). Item k is computed as
    start + k gap, so rounding does not add up along the list."""
    _check(gap != 0)

    def before(x) -> bool:
        return x < stop if gap > 0 else x > stop

    n = max(0, math.ceil((stop - start) / gap))
    _check(n <= RANGE_LIMIT)
    while n > 0 and not before(start + (n - 1) * gap):
        n -= 1
    while before(start + n * gap):
        n += 1
    return [start + k * gap for k in range(n)]


def range_by_count(start, stop, n) -> list:
    """n items from start to stop, both included, evenly apart (mtp-966)."""
    _check(0 <= n <= RANGE_LIMIT)
    if n == 1:
        return [start]
    return [stop if k == n - 1 else start + k * (stop - start) / (n - 1) for k in range(n)]


BUILTINS: dict[str, Builtin] = {
    "sqrt": _unary(_sqrt, _sqrt_range, lambda rs: rs[0][0] < 0),
    # sign never falls as its input grows, so the ends of the input's range give the result's.
    "sign": _unary(_sign, lambda rs: (_sign(rs[0][0]), _sign(rs[0][1])), result=INT),
    "floor": _unary(
        math.floor, lambda rs: (math.floor(rs[0][0]), math.floor(rs[0][1])), result=INT
    ),
    "ceil": _unary(math.ceil, lambda rs: (math.ceil(rs[0][0]), math.ceil(rs[0][1])), result=INT),
    "exp": _unary(_exp, _exp_range),
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
    # dist has no upper limit of its own, so its range stops at the number limit.
    "dist": Builtin((POINT, POINT), REAL, lambda p, q: math.dist(p, q), (0.0, WHOLE[1])),
    "rotate": Builtin((REAL,), TRANSFORM, _rotate, None),
    "translate": Builtin((REAL, REAL), TRANSFORM, lambda dx, dy: (1, 0, 0, 1, dx, dy), None),
    "mix": Builtin((COLOR, COLOR, UNIT), COLOR, colors.mix, None),
    "lighten": Builtin((COLOR, UNIT), COLOR, lambda c, t: colors.mix(c, "#ffffffff", t), None),
    "darken": Builtin((COLOR, UNIT), COLOR, lambda c, t: colors.mix(c, "#000000ff", t), None),
    "light-dark": Builtin((COLOR, COLOR), COLOR, colors.light_dark, None),
}

# Built-ins whose arguments vary in number or type, handled by the compiler itself.
SPECIAL_BUILTINS = {
    "round", "log", "min", "max", "lerp", "scale", "transform", "range",
    "rand", "rand-int", "pick", "shuffle", "next-seed",
}  # fmt: skip
CONSTANTS = {
    "pi": math.pi,
    "tau": math.tau,
    "euler": math.e,
}
