"""Every figure can be seen on a light page and on a dark page (mtp-wrxq). The author,
2026-11-16: all examples must work in light and dark mode: the spec, the docs, the landing page
and examples/. Each source is compiled, and each color that a shape, a text, a term or a scene's
background uses is checked against the background that it is drawn on, in each mode.

The author, 2026-11-22, chose which colors are worked out: fixed values, reads of colors that
nothing changes, every branch of an if, every item of a list of colors, a read of another
shape's attribute followed to that attribute, the arguments given to a motif instance, and mix,
lighten, darken and colormap calls whose arguments are known when compiling. A color worked out
in any other way is skipped, and test_colors_known_only_while_drawing lists the skipped ones.
The colors that a move gives an attribute are checked as well as its first value.

A scene's background is checked only when it is not paper, since paper matches the page on
purpose. Shapes are checked against their scene's background when it is not paper, and against
the page otherwise. A color with some transparency is checked as it looks drawn over that
background, with its alpha times the shape's opacities. A color that is none or that has zero
opacity, and a stroke of zero width, are not checked. Nor are colors drawn with an alpha below 0.5,
which are faint areas behind the marks (the author, 2026-11-23). A block of the docs that does not compile
on its own, such as an error example, is skipped."""

import itertools
import json
import re
from fractions import Fraction
from functools import cache
from pathlib import Path

import pytest
from helpers import doc

from mathterpiece import colors
from mathterpiece.builtins import BUILTINS
from mathterpiece.compiler import CompileError, _fold
from mathterpiece.parse import ParseError

ROOT = Path(__file__).parent.parent

LIGHT_PAGE = "#fafaf8ff"
DARK_PAGE = "#111518ff"
PAGES = {"light": LIGHT_PAGE, "dark": DARK_PAGE}

# WCAG 2.1 success criterion 1.4.11 (non-text contrast) asks for 3:1 between a graphical object
# that is needed to understand the content and the colors next to it. Shapes and lines in a
# figure are such objects, so the author chose this threshold for every color (2026-11-22).
THRESHOLD = 3.0

# A line, a polyline, a curve and an arc never draw their fill (docs/reference.md).
OPEN_SHAPES = {"line", "polyline", "curve", "arc"}
SHAPES = OPEN_SHAPES | {"circle", "ellipse", "rect", "polygon", "ring", "triangle", "text"}


def _sources() -> list[tuple[str, str, Path | None]]:
    found = []
    for p in sorted((ROOT / "examples").glob("*.mtp")):
        if p.stem != "house":
            found.append((f"examples/{p.name}", p.read_text(encoding="utf-8"), p))
    for p in sorted((ROOT / "site" / "figures").glob("*.mtp")):
        found.append((f"site/figures/{p.name}", p.read_text(encoding="utf-8"), p))
    docs = ROOT / "docs"
    for p in sorted(docs.rglob("*.mtp")):
        found.append((str(p.relative_to(ROOT)), p.read_text(encoding="utf-8"), p))
    # The same blocks that tests/test_grammar.py reads from the spec, from every page of docs/.
    fence = re.compile(r"^(`{3,})(\{mtp-example\}|mtp)[ \t]*\n(.*?)^\1[ \t]*$", re.M | re.S)
    for page in sorted(docs.rglob("*.md")):
        if any(part.startswith("_") for part in page.relative_to(docs).parts):
            continue
        text = page.read_text(encoding="utf-8")
        for k, m in enumerate(fence.finditer(text)):
            lines = m[3].splitlines()
            while lines and lines[0].startswith(":"):
                lines.pop(0)
            source = "\n".join(lines).replace("…", "")
            found.append((f"{page.relative_to(ROOT)}#{k}", source + "\n", None))
    return found


SOURCES = _sources()


class Unknown(Exception):
    """A value known only while drawing."""


def _key(v) -> str:
    return json.dumps(v, sort_keys=True, default=str)


def _distinct(values: list) -> list:
    out = {}
    for v in values:
        out.setdefault(_key(v), v)
    if len(out) > 512:
        raise Unknown
    return list(out.values())


class Values:
    """Works out the values that an expression of a .mtpc can take while it is drawn, as far as
    the author's rules allow, or raises Unknown."""

    def __init__(self, d: dict):
        self.objects = d["objects"]
        self.functions = d.get("functions", [])
        self.memo: dict = {}
        self.written = self._written()

    def _written(self) -> set:
        """The variables and attributes that a move, a drag or a toggle changes. A read of one of
        them is known only while drawing."""
        out = set()

        def walk(x):
            if isinstance(x, list):
                if len(x) >= 2 and x[0] == "move" and isinstance(x[1], list):
                    out.add(tuple(x[1]))
                for v in x:
                    walk(v)
            elif isinstance(x, dict):
                t = x.get("target")
                if isinstance(t, list) and len(t) == 2:
                    out.add(tuple(t))
                for v in x.values():
                    walk(v)

        walk(self.objects)
        return out

    def moved_to(self, ident: int, attr: str) -> list:
        """The expressions that moves give as the new value of an attribute."""
        found = []

        def walk(x):
            if isinstance(x, list):
                if len(x) >= 3 and x[0] == "move" and x[1] == [ident, attr]:
                    found.append(self.objects[x[2]].get("to"))
                for v in x:
                    walk(v)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)

        for o in self.objects:
            if o["kind"] == "animation":
                walk(o.get("steps"))
        return found

    def of_value(self, v: dict | None, env: dict | None = None) -> list:
        if v is None:
            raise Unknown
        if "free" in v:
            return [v["free"]]
        if "bound" in v:
            return self.of(v["bound"], env or {})
        raise Unknown

    def read(self, ident: int, attr: str | None) -> list:
        if (ident, attr) in self.written:
            raise Unknown
        k = (ident, attr)
        if k in self.memo:
            if self.memo[k] is None:
                raise Unknown
            return self.memo[k]
        self.memo[k] = None
        o = self.objects[ident]
        v = o.get("value") if attr is None else o.get("attrs", {}).get(attr)
        out = self.of_value(v)
        self.memo[k] = out
        return out

    def of(self, e, env: dict) -> list:
        if not isinstance(e, list) or not e or not isinstance(e[0], str):
            raise Unknown
        op = e[0]
        if op == "lit":
            t, v = e[1], e[2]
            if (t == "ratio" or (isinstance(t, dict) and t.get("refine") == "ratio")) and v:
                return [Fraction(v[0], v[1])]
            return [v]
        if op == "read":
            return self.read(e[2], e[3])
        if op == "local":
            v = env.get(e[2])
            if v is None:
                raise Unknown
            return v
        if op == "if":
            try:
                cond = self.of(e[2], env)
            except Unknown:
                cond = [True, False]
            out = []
            if any(c is True for c in cond):
                out += self.of(e[3], env)
            if any(c is not True for c in cond):
                out += self.of(e[4], env)
            return _distinct(out)
        if op == "let":
            inner = dict(env)
            for name, x in e[2]:
                try:
                    inner[name] = self.of(x, inner)
                except Unknown:
                    inner[name] = None
            return self.of(e[3], inner)
        if op == "part":
            lists = self.of(e[2], env)
            if isinstance(e[3], str):
                raise Unknown
            try:
                keys = self.of(e[3], env)
            except Unknown:
                keys = None
            out = []
            for xs in lists:
                if not isinstance(xs, list):
                    raise Unknown
                if keys is None:
                    out += xs
                else:
                    out += [xs[k] for k in keys if isinstance(k, int) and 0 <= k < len(xs)]
            return _distinct(out)
        if op == "call":
            f = self.functions[e[2]]
            names = [p["name"] for p in f["params"]]
            out = []
            for args in itertools.product(*(self.of(a, env) for a in e[3:])):
                out += self.of(f["body"], dict(zip(names, ([a] for a in args), strict=True)))
            return _distinct(out)
        if op == "builtin":
            name = e[2]
            out = []
            for args in itertools.product(*(self.of(a, env) for a in e[3:])):
                out.append(_builtin(name, list(args)))
            return _distinct(out)
        if op in ("and", "or"):
            sets = [self.of(a, env) for a in e[2:]]
            if any(len(s) != 1 for s in sets):
                raise Unknown
            vals = [s[0] for s in sets]
            return [all(vals) if op == "and" else any(vals)]
        raise Unknown


def _builtin(name: str, args: list):
    if name in BUILTINS:
        try:
            return BUILTINS[name].fold(*args)
        except Exception as err:
            raise Unknown from err
    if name in ("min", "max") and all(isinstance(a, (int, float, Fraction)) for a in args):
        return (min if name == "min" else max)(args)
    if name == "not" and len(args) == 1:
        return not args[0]
    if name in ("+", "-", "*", "/", "^", "mod", "=", "!=", "<", "<=", ">", ">="):
        try:
            return _fold(name, args)
        except Exception as err:
            raise Unknown from err
    raise Unknown


def _luminance(rgba: str) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(int(rgba[k : k + 2], 16) / 255) for k in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _over(rgba: str, alpha: float, background: str) -> str:
    """A color with this alpha drawn over an opaque background, as the page shows it."""
    mixed = [
        int(rgba[k : k + 2], 16) * alpha + int(background[k : k + 2], 16) * (1 - alpha)
        for k in (1, 3, 5)
    ]
    return "#" + "".join(f"{round(c):02x}" for c in mixed) + "ff"


def contrast(a: str, b: str) -> float:
    lo, hi = sorted((_luminance(a), _luminance(b)))
    return (hi + 0.05) / (lo + 0.05)


def _alpha(rgba: str) -> float:
    return int(rgba[7:9], 16) / 255


def _opacity(values: Values, o: dict, attrs: tuple[str, ...]) -> float:
    """The largest opacity that the shape can be drawn with. An opacity known only while drawing
    counts as 1, so the color is checked as it looks when the shape is fully shown."""
    out = 1.0
    for a in attrs:
        if a not in o.get("attrs", {}):
            continue
        try:
            vs = [float(v) for v in values.of_value(o["attrs"][a])]
        except (Unknown, TypeError):
            continue
        out *= max(vs)
    return out


def _colors(values: Values, ident: int, attr: str) -> list:
    """The colors that an attribute can take, its first value and each value that a move gives
    it, or raises Unknown."""
    o = values.objects[ident]
    out = values.of_value(o["attrs"][attr])
    for to in values.moved_to(ident, attr):
        out += values.of_value(to)
    return _distinct(out)


# A color drawn with an alpha below this is a faint area behind the marks, not a mark that must
# be seen, so it is not checked (the author, 2026-11-23). WCAG's 3:1 is for marks that carry
# meaning.
FAINT = 0.5

# examples/house.mtp's paper. A background with this value is paper even when it does not read
# the token, as in a spec block that writes the color out.
PAPER = "light-dark(#ffffffff, #13181bff)"


def _is_paper(values: Values, v: dict) -> bool:
    if v.get("free") == PAPER:
        return True
    e = v.get("bound")
    if not (isinstance(e, list) and e[0] == "read" and e[3] is None):
        return False
    o = values.objects[e[2]]
    named = (o.get("name") or "").split(".")[-1]
    return named == "paper" or o.get("value", {}).get("free") == PAPER


def _drawn_on(values: Values) -> dict[int, list[dict[str, str]]]:
    """For each shape, the backgrounds that it can be drawn on, by mode: its scene's background
    when that is not paper, and the page otherwise."""
    objects = values.objects
    on: dict[int, list[dict[str, str]]] = {}
    for o in objects:
        if o["kind"] != "scene":
            continue
        bg = o.get("attrs", {}).get("background")
        backgrounds = [dict(PAGES)]
        if bg is not None and not _is_paper(values, bg):
            try:
                found = [c for c in values.of_value(bg) if c is not None]
            except Unknown:
                found = []
            if found:
                backgrounds = [
                    {m: _over(_rgba(c, m), _alpha(_rgba(c, m)), p) for m, p in PAGES.items()}
                    for c in found
                ]
        stack = list(o.get("members", []))
        while stack:
            i = stack.pop()
            on[i] = backgrounds
            stack += objects[i].get("members", [])
    return on


def _rgba(color: str, mode: str) -> str:
    c = colors.light(color) if mode == "light" else colors.dark(color)
    return colors.parse_color(c) or c


@cache
def _compiled(index: int):
    """The checks of one source: (cases, skipped), or the error of a block that does not compile
    on its own, such as an error example or a part of a source."""
    name, src, path = SOURCES[index]
    try:
        d = doc(src, path)
    except (CompileError, ParseError) as e:
        return str(e).splitlines()[0]
    values = Values(d)
    on = _drawn_on(values)
    cases: dict[str, tuple[float, list[str]]] = {}
    skipped: list[str] = []

    def check(ident, attr, backgrounds, opacity):
        o = values.objects[ident]
        label = f"{o.get('name') or o['kind'] + str(ident)}.{attr}"
        try:
            found = _colors(values, ident, attr)
        except Unknown:
            skipped.append(label)
            return
        for color in found:
            if not isinstance(color, str) or color == "none":
                continue
            for bg in backgrounds:
                for mode in PAGES:
                    rgba = _rgba(color, mode)
                    alpha = _alpha(rgba) * opacity
                    if alpha < FAINT:
                        continue
                    case = f"{name}:{mode}:{rgba}:on:{bg[mode]}"
                    ratio = contrast(_over(rgba, alpha, bg[mode]), bg[mode])
                    used = f"{label}@{alpha:.2g}" if alpha < 1 else label
                    old = cases.get(case, (ratio, []))
                    cases[case] = (min(old[0], ratio), [*old[1], used])

    for i, o in enumerate(values.objects):
        kind = o["kind"]
        attrs = o.get("attrs", {})
        if kind == "scene":
            bg = attrs.get("background")
            if bg is not None and not _is_paper(values, bg):
                check(i, "background", [dict(PAGES)], 1.0)
            continue
        backgrounds = on.get(i, [dict(PAGES)])
        if kind == "term" and "fill" in attrs:
            check(i, "fill", backgrounds, _opacity(values, o, ("opacity",)))
        if kind not in SHAPES:
            continue
        if kind not in OPEN_SHAPES and "fill" in attrs:
            check(i, "fill", backgrounds, _opacity(values, o, ("opacity", "fill-opacity")))
        if "stroke" in attrs and _opacity(values, o, ("stroke-width",)) > 0:
            check(i, "stroke", backgrounds, _opacity(values, o, ("opacity", "stroke-opacity")))
    return cases, skipped


def _all_cases():
    out = []
    for index in range(len(SOURCES)):
        got = _compiled(index)
        if isinstance(got, str):
            continue
        for case, (ratio, labels) in sorted(got[0].items()):
            out.append((case, ratio, labels))
    return out


# The cases below 3:1 when this test was written (2026-11-22), with their ratios. The author
# chooses the colors, so each is an expected failure until the color is changed. The marks are
# strict, so a case that passes fails until it is taken off the list.
KNOWN_FAILURES: dict[str, float] = json.loads(
    (Path(__file__).parent / "light_dark_failures.json").read_text(encoding="utf-8")
)

CASES = _all_cases()


@pytest.mark.parametrize(
    ("case", "ratio", "labels"),
    [
        pytest.param(
            c,
            r,
            labels,
            id=c,
            marks=[pytest.mark.xfail(strict=True, reason=f"{KNOWN_FAILURES[c]:.2f}:1, below 3:1")]
            if c in KNOWN_FAILURES
            else [],
        )
        for c, r, labels in CASES
    ],
)
def test_the_color_can_be_seen_on_its_background(case, ratio, labels):
    assert ratio >= THRESHOLD, f"{case} is {ratio:.2f}:1, below 3:1, used by {sorted(set(labels))}"


@pytest.mark.parametrize("index", range(len(SOURCES)), ids=[s[0] for s in SOURCES])
def test_colors_known_only_while_drawing(index):
    got = _compiled(index)
    if isinstance(got, str):
        pytest.skip(f"does not compile on its own: {got}")
    skipped = sorted(set(got[1]))
    if skipped:
        pytest.skip(f"{len(skipped)} colors known only while drawing, not checked: {skipped}")
