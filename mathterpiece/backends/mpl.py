"""The matplotlib backend. It reads the JSON the compiler writes (mathterpiece.export), like any
other backend, and evaluates its resolved operations."""

import math
import random
import sys
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle as MplCircle
from matplotlib.patches import Ellipse as MplEllipse
from matplotlib.patches import Patch, PathPatch, Polygon, Rectangle
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D, Transform

from mathterpiece.colors import same
from mathterpiece.compiler import ARITHMETIC, COMPARISONS, WALKS, _value_problem
from mathterpiece.compiler import _fold as fold
from mathterpiece.export import ExportError, export
from mathterpiece.matrix import IDENTITY, Matrix, compose
from mathterpiece.model import PYTHON_FRAMES, RECURSION_LIMIT, Model, Obj, Text
from mathterpiece.stdlib import STDLIB, power, show, translate
from mathterpiece.stdlib import call as stdlib_call

# The other ways of reading a shape, and which of them are positions (converted between frames
# like x and y).
PROPERTIES = {
    "rect": {"center", "size", "from", "to"},
    "ellipse": {"center", "size"},
    "line": {"from", "to"},
    "triangle": {"center", "r"},
}
POINTS = {"center", "from", "to"}
SHAPES = {"circle", "rect", "ellipse", "line", "triangle"}
CONTAINERS = {"root", "group", "motif"}
# Objects whose expressions read positions in scene coordinates.
CONTROLS = {"slider", "button", "play", "toggle", "animation", "on-drag", "on-click"}


class EvalError(Exception):
    pass


# An object passed as a value, as in (dist a b).
@dataclass(frozen=True)
class _Ref:
    id: int


# Several values from a group attribute, spread into the call around them.
@dataclass(frozen=True)
class _Splice:
    values: tuple


class Runtime:
    """Evaluates a JSON document: values by object id and attribute, and what writes change."""

    def __init__(self, doc: dict, rng: random.Random | None = None):
        self.doc = doc
        self.objects: list[dict] = doc["objects"]
        self.rng = rng or random.Random()
        self.cache: dict[tuple[int, str], Any] = {}
        self.active: set[tuple[int, str]] = set()
        self.written: dict[tuple[int, str], Any] = {}
        self.frames: dict[int, Matrix] = {}
        self.depth = 0
        sys.setrecursionlimit(max(sys.getrecursionlimit(), PYTHON_FRAMES))

    def kind(self, i: int) -> str:
        return self.objects[i]["kind"]

    def parent(self, i: int) -> int | None:
        return self.objects[i].get("parent")

    # The container whose coordinates object i's expressions read positions in.
    def reading_frame(self, i: int) -> int | None:
        obj = self.objects[i]
        if obj["kind"] == "value":
            return obj["frame"]
        if obj["kind"] == "state" or obj["kind"] in CONTROLS:
            return None
        return obj.get("parent")

    # A control's write. Everything computed is dropped, since anything might depend on it.
    def write(self, i: int, attr: str, value: Any):
        # A position is its x and y, as on the web.
        if attr == "pos":
            self.write(i, "x", value[0])
            self.write(i, "y", value[1])
            return
        self.written[(i, attr)] = value
        self.cache.clear()
        self.frames.clear()

    def value(self, i: int, attr: str) -> Any:
        key = (i, attr)
        if key in self.written:
            return self.written[key]
        if key in self.cache:
            return self.cache[key]
        if key in self.active:
            name = self.objects[i]["name"] or "an anonymous object"
            raise EvalError(f"cycle through {name}.{attr}")
        obj = self.objects[i]
        # A toggle with a target is that value.
        if obj["kind"] == "toggle" and attr == "value" and obj.get("target"):
            target, part = obj["target"]
            # On a group's attribute, it holds only when every member's does.
            members = self.objects[target].get("members") if self.kind(target) == "group" else None
            if members is not None:
                return all(self.value(m, part) for m in members)
            return self.value(target, part)
        raw = obj["params"][attr] if attr in obj.get("params", {}) else obj["attrs"][attr]
        self.active.add(key)
        try:
            result = self.eval(raw, self.reading_frame(i), {})
        finally:
            self.active.discard(key)
        if attr == "transform" and isinstance(result, tuple):
            a, b, c, d, e, f = result
            result = Matrix(((a, b, c), (d, e, f), (0, 0, 1)))
        self.cache[key] = result
        return result

    # The items a loop walks: a group's members, or a list's items.
    def items(self, value: Any) -> list:
        if isinstance(value, _Ref):
            members = self.objects[value.id].get("members")
            if members is None:
                raise EvalError("a loop walks a group or a list")
            return [_Ref(m) for m in members]
        return list(value)

    def walk(self, op: str, args: list, frame: int | None, env: dict) -> Any:
        if op == "walk-sort":
            direction, collection, name, key = args
            items = self.items(self.eval(collection, frame, env))
            keys = [self.eval(key, frame, env | {name: item}) for item in items]
            pairs = sorted(
                zip(items, keys, strict=True), key=lambda p: p[1], reverse=direction == "desc"
            )
            return tuple(item for item, _ in pairs)
        if op == "walk-reduce":
            collection, name, running, start, body = args
            value = self.eval(start, frame, env)
            for item in self.items(self.eval(collection, frame, env)):
                value = self.eval(body, frame, env | {name: item, running: value})
            return value
        collection, name, body = args
        items = self.items(self.eval(collection, frame, env))
        each = (self.eval(body, frame, env | {name: item}) for item in items)
        if op == "walk-any":
            return any(each)
        if op == "walk-all":
            return all(each)
        return tuple(v if isinstance(v, bool) else float(v) for v in each)

    def eval(self, e: Any, frame: int | None, env: dict) -> Any:
        if not isinstance(e, list):
            return e
        if not e or not isinstance(e[0], str):
            return tuple(e)
        op, args = e[0], e[1:]
        if op == "read":
            target = args[0]
            dynamic = not isinstance(target, int)
            if dynamic:
                ref = self.eval(target, frame, env)
                assert isinstance(ref, _Ref)
                target = ref.id
            convert = len(args) == 3 or dynamic
            into = args[2] if len(args) == 3 else frame
            return self.read(target, args[1], into, convert)
        if op == "param":
            return self.value(args[0], args[1])
        if op == "holds":
            return self.holds(args[0])
        if op == "arg":
            return env[args[0]]
        if op in WALKS:
            return self.walk(op, args, frame, env)
        if op == "part":
            base = self.eval(args[0], frame, env)
            if isinstance(base, _Ref):
                base = self.items(base)
            index = args[1] if isinstance(args[1], int) else int(self.eval(args[1], frame, env))
            if not -len(base) <= index < len(base):
                raise EvalError(f"a list of {len(base)} has no part {index}")
            return base[index]
        if op == "obj":
            return _Ref(args[0])
        if op == "splice":
            return _Splice(tuple(self.eval(a, frame, env) for a in args))
        if op == "list":
            items = (self.eval(a, frame, env) for a in args)
            return tuple(v if isinstance(v, bool) else float(v) for v in items)
        if op == "complex":
            return complex(args[0], args[1])
        if op == "inf":
            return math.inf
        if op == "-inf":
            return -math.inf
        if op == "str":
            return "".join(a if isinstance(a, str) else self.eval(a, frame, env) for a in args)
        if op == "show":
            value = self.eval(args[0], frame, env)
            spec = args[2] if len(args) > 2 else None
            if isinstance(value, _Splice):
                return " ".join(_show(v, args[1], spec) for v in value.values)
            return _show(value, args[1], spec)
        if op == "and":
            return all(self.eval(a, frame, env) for a in args)
        if op == "or":
            return any(self.eval(a, frame, env) for a in args)
        if op == "if":
            test, then, other = args
            return self.eval(then if self.eval(test, frame, env) else other, frame, env)
        if op == "not":
            return not self.eval(args[0], frame, env)
        if op == "cond":
            for test, result in args:
                if test is True or self.eval(test, frame, env):
                    return self.eval(result, frame, env)
            raise EvalError("no cond clause held")
        if op == "let":
            pairs, body = args
            inner = dict(env)
            for name, value in pairs:
                inner[name] = self.eval(value, frame, inner)
            return self.eval(body, frame, inner)
        call = op == "call"
        name = args[0] if call else op
        values: list[Any] = []
        for a in args[1:] if call else args:
            value = self.eval(a, frame, env)
            values.extend(value.values if isinstance(value, _Splice) else [value])
        if call and name in self.doc["functions"]:
            return self.call_function(name, values, frame)
        try:
            return self.apply(name, values)
        except (ZeroDivisionError, ValueError) as err:
            raise EvalError(str(err) or "division by zero") from None

    def call_function(self, key: str, args: list[Any], frame: int | None) -> Any:
        if self.depth >= RECURSION_LIMIT:
            raise EvalError(f"recursion is deeper than {RECURSION_LIMIT} calls")
        fn = self.doc["functions"][key]
        env = {
            name: args[i] if i < len(args) else default
            for i, (name, default) in enumerate(fn["params"])
        }
        self.depth += 1
        try:
            return self.eval(fn["body"], frame, env)
        finally:
            self.depth -= 1

    def apply(self, op: str, args: list[Any]) -> Any:
        if op in ARITHMETIC:
            return fold(op, args)
        if op == "^":
            result = power(*args)
            if isinstance(result, complex):
                raise EvalError("the result of ^ is not a real number")
            return result
        if op == "abs":
            return abs(args[0])
        if op == "mod":
            if args[1] == 0:
                raise EvalError("mod by zero")
            return args[0] % args[1]
        if op in COMPARISONS:
            return COMPARISONS[op](*args)
        if op in ("color=", "color!="):
            return same(*args) == (op == "color=")
        if op == "transform":
            return compose(*args)
        if op in ("sort-asc", "sort-desc"):
            return tuple(sorted(args[0], reverse=op == "sort-desc"))
        if op == "reverse":
            return tuple(reversed(args[0]))
        if op == "any":
            return any(args[0])
        if op == "all":
            return all(args[0])
        if op == "sort-by":
            pairs = list(zip(args[1::2], args[2::2], strict=True))
            pairs.sort(key=lambda pair: pair[1], reverse=args[0] == "desc")
            return tuple(member for member, _ in pairs)
        if op in STDLIB:
            fn = STDLIB[op]
            kinds = [
                "point"
                if isinstance(a, (_Ref, tuple))
                else "color"
                if isinstance(a, str)
                else "real"
                for a in args
            ]
            sig = fn.find(kinds)
            assert sig is not None
            values = [self.point(a.id) if isinstance(a, _Ref) else a for a in args]
            return stdlib_call(fn, sig, values, self.rng)
        raise EvalError(f"unknown function {op!r}")

    # attr of object i, given in the coordinates of container `into` when convert is set and the
    # attribute is a position.
    def read(self, i: int, attr: str, into: int | None, convert: bool) -> Any:
        kind = self.kind(i)
        here = self.parent(i)
        if attr in ("x", "y") and (not convert or here == into):
            return self.value(i, attr)
        properties = PROPERTIES.get(kind, set())
        positional = attr in ("x", "y", "pos") or (attr in POINTS and attr in properties)
        if not positional:
            return self.property(i, attr) if attr in properties else self.value(i, attr)
        if attr in ("x", "y", "pos"):
            point = self.value(i, "x"), self.value(i, "y")
        else:
            point = self.property(i, attr)
        if convert:
            point = self.convert(point, here, into)
        return point if attr not in ("x", "y") else point[0 if attr == "x" else 1]

    def convert(self, point: tuple, here: int | None, there: int | None) -> tuple:
        if here == there:
            return tuple(point)
        scene = self.frame(here).apply(*point)
        try:
            return self.frame(there).inverse().apply(*scene)
        except ValueError as err:
            raise EvalError(str(err)) from None

    # The other ways of reading a shape, computed from what it stores, in its parent's coordinates.
    def property(self, i: int, name: str) -> Any:
        kind = self.kind(i)

        def v(attr):
            return self.value(i, attr)

        if kind == "rect":
            if name == "from":
                return v("x"), v("y")
            if name == "size":
                return v("width"), v("height")
            share = 0.5 if name == "center" else 1
            return v("x") + share * v("width"), v("y") + share * v("height")
        if kind == "ellipse":
            return (v("x"), v("y")) if name == "center" else (2 * v("rx"), 2 * v("ry"))
        if kind == "line":
            end = (v("x1"), v("y1")) if name == "from" else (v("x2"), v("y2"))
            return v("x") + end[0], v("y") + end[1]
        corners = [v("a"), v("b"), v("c")]
        mid = (sum(p[0] for p in corners) / 3, sum(p[1] for p in corners) / 3)
        if name == "center":
            return v("x") + mid[0], v("y") + mid[1]
        return math.dist(mid, corners[0])

    # Maps the coordinates of a container's members to scene coordinates. A motif's own x and y
    # sit outside its transform, as in Unity or Godot.
    def frame(self, container: int | None) -> Matrix:
        if container is None:
            return IDENTITY
        if container not in self.frames:
            local = self.value(container, "transform")
            if self.kind(container) == "motif":
                local = translate(self.value(container, "x"), self.value(container, "y")) @ local
            self.frames[container] = self.frame(self.parent(container)) @ local
        return self.frames[container]

    def point(self, i: int) -> tuple[Any, Any]:
        return self.frame(self.parent(i)).apply(self.value(i, "x"), self.value(i, "y"))

    # Places a shape drawn around the origin: its own transform, then its x and y, then the
    # transforms of everything it sits in.
    def shape(self, i: int) -> Matrix:
        at = translate(self.value(i, "x"), self.value(i, "y"))
        return self.frame(self.parent(i)) @ at @ self.value(i, "transform")

    # Opacity multiplies down the tree of motifs, unlike the other style attributes.
    def opacity(self, i: int) -> float:
        result = self.value(i, "opacity")
        p = self.parent(i)
        while p is not None:
            if self.kind(p) == "motif":
                result *= self.value(p, "opacity")
            p = self.parent(p)
        return result

    # Whether all of a state's conditions hold. Numbers compared by = count as equal within a
    # small tolerance, so that a state still counts after a drag or an animation.
    def holds(self, state: int) -> bool:
        for cond in self.objects[state]["conditions"]:
            if isinstance(cond, list) and cond and cond[0] == "=" and len(cond) == 3:
                if not _close(self.eval(cond[1], None, {}), self.eval(cond[2], None, {})):
                    return False
            elif not self.eval(cond, None, {}):
                return False
        return True


class Evaluator:
    """A Runtime for a compiled model, addressed by the model's objects instead of ids."""

    def __init__(self, model: Model, rng: random.Random | None = None):
        try:
            doc, ids = export(model)
        except ExportError as err:
            raise EvalError(str(err)) from None
        self.runtime = Runtime(doc, rng)
        self.ids = ids
        self.objects = {ids[id(o)]: o for o in _all_objects(model) if id(o) in ids}

    def id(self, obj: Obj) -> int:
        return self.ids[id(obj)]

    def value(self, obj: Obj, attr: str) -> Any:
        return self.runtime.value(self.id(obj), attr)

    def write(self, obj: Obj, attr: str, value: Any):
        self.runtime.write(self.id(obj), attr, value)

    def point(self, obj: Obj) -> tuple[Any, Any]:
        return self.runtime.point(self.id(obj))

    def holds(self, state: Obj) -> bool:
        return self.runtime.holds(self.id(state))


def _all_objects(model: Model) -> list[Obj]:
    out: list[Obj] = []
    stack: list[Obj] = list(model)
    while stack:
        obj = stack.pop()
        out.append(obj)
        members = getattr(obj, "members", None)
        if isinstance(members, list):
            stack.extend(members)
    return out


# Numbers are floats while drawing, so the type from the compiler says how to show them: by the
# format spec, as in Python's f-strings, or Python's default without one.
def _show(value: Any, kind: str, spec: str | None = None) -> str:
    number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "int" and number:
        value = int(round(value))
    elif kind in ("real", "ratio") and number:
        value = float(value)
    if spec:
        try:
            return format(value, spec)
        except (ValueError, TypeError) as err:
            raise EvalError(str(err)) from None
    return show(value)


def _close(a: Any, b: Any) -> bool:
    if isinstance(a, tuple) and isinstance(b, tuple):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b


def render(model: Model, rng: random.Random | None = None) -> list[tuple[Figure, Axes]]:
    return render_json(export(model)[0], rng)


def render_json(doc: dict, rng: random.Random | None = None) -> list[tuple[Figure, Axes]]:
    rt = Runtime(doc, rng)
    figures: list[tuple[Figure, Axes]] = []
    for obj in doc["objects"]:
        if obj["kind"] != "canvas":
            continue
        fig, ax = plt.subplots()
        strokes: list[tuple[Patch, float]] = []
        _draw_canvas(obj["id"], ax, rt, strokes)
        _stroke_in_scene_units(fig, ax, strokes)
        figures.append((fig, ax))
    return figures


def _draw_canvas(view: int, ax: Axes, rt: Runtime, strokes: list):
    x, y = rt.value(view, "view-x"), rt.value(view, "view-y")
    width, height = rt.value(view, "view-width"), rt.value(view, "view-height")
    ax.set_xlim(x, x + width)
    ax.set_ylim(y, y + height)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_frame_on(False)
    center = translate(x + width / 2, y + height / 2)
    to_center = translate(-(x + width / 2), -(y + height / 2))
    matrix = compose(to_center, rt.value(view, "transform"), center)
    to_view = _affine(matrix) + ax.transData
    # The scene's background fills the figure, as it fills the SVG element on the web.
    root = next((o["id"] for o in rt.objects if o["kind"] == "root"), None)
    background = "none" if root is None else rt.value(root, "background")
    if background != "none":
        try:
            fill = to_rgba(background)
        except ValueError:
            raise EvalError(f"{background!r} is not a color") from None
        ax.set_facecolor(fill)
        ax.figure.set_facecolor(fill)
    # What the canvas shows only while its when holds is drawn as it stands when drawn.
    whens = rt.objects[view].get("when") or []
    for k, member in enumerate(rt.objects[view]["shows"]):
        when = whens[k] if k < len(whens) else None
        if when is not None and not rt.eval(when, None, {}):
            continue
        _draw(member, ax, rt, to_view, strokes, _scale(matrix))


# matplotlib line widths are in points, but stroke-width is in scene units as in SVG, so widths
# are set from how many points one scene unit covers, again whenever the window is resized. The
# transform's scale counts too; for a stretch that differs by direction this is an average.
def _stroke_in_scene_units(fig: Figure, ax: Axes, strokes: list):
    _update_strokes(fig, ax, strokes)
    fig.canvas.mpl_connect("resize_event", lambda _event: _update_strokes(fig, ax, strokes))


def _update_strokes(fig: Figure, ax: Axes, strokes: list):
    ax.apply_aspect()
    (x0, _), (x1, _) = ax.transData.transform([(0, 0), (1, 0)])
    points = (x1 - x0) * 72 / fig.dpi
    for artist, width in strokes:
        artist.set_linewidth(width * points)


# view_scale is how much the canvas transform scales lengths, for stroke widths.
def _draw(i: int, ax: Axes, rt: Runtime, to_view: Transform, strokes: list, view_scale: float):
    kind = rt.kind(i)
    if kind in CONTAINERS:
        for member in rt.objects[i]["members"]:
            _draw(member, ax, rt, to_view, strokes, view_scale)
    elif kind in SHAPES:
        shape = rt.shape(i)
        patch = _outline(i, rt)
        patch.set_facecolor("none" if kind == "line" else _paint(rt, i, "fill"))
        patch.set_edgecolor(_paint(rt, i, "stroke"))
        patch.set_transform(_affine(shape) + to_view)
        strokes.append((patch, rt.value(i, "stroke-width") * _scale(shape) * view_scale))
        ax.add_patch(patch)
    elif kind == "text":
        # Glyph outlines in scene units, so the canvas transform turns and scales the letters
        # the way an SVG transform does.
        shape = rt.shape(i)
        value = rt.value(i, "value")
        # Values computed while drawing are checked here, as known ones were when compiling.
        for attr in ("halign", "valign", "font-style", "font-weight"):
            problem = _value_problem(Text, attr, rt.value(i, attr))
            if problem:
                raise EvalError(problem)
        family = rt.value(i, "font-family")
        font = FontProperties(
            family=family or None,
            style=rt.value(i, "font-style"),
            weight=rt.value(i, "font-weight"),
        )
        glyphs = TextPath((0, 0), value, size=rt.value(i, "font-size"), prop=font)
        # matplotlib has no alignment for glyph outlines, so the text is moved by its own box,
        # which is close to what a browser does (it aligns by the font's metrics instead).
        box = glyphs.get_extents()
        dx = {"start": 0.0, "middle": -(box.x0 + box.x1) / 2, "end": -box.x1}[rt.value(i, "halign")]
        dy = {"bottom": 0.0, "middle": -(box.y0 + box.y1) / 2, "top": -box.y1}[
            rt.value(i, "valign")
        ]
        text = PathPatch(
            glyphs,
            facecolor=_paint(rt, i, "fill"),
            edgecolor=_paint(rt, i, "stroke"),
            transform=Affine2D().translate(dx, dy) + _affine(shape) + to_view,
            label=value,
        )
        strokes.append((text, rt.value(i, "stroke-width") * _scale(shape) * view_scale))
        ax.add_patch(text)


# Each shape drawn around its own origin; rt.shape places it.
def _outline(i: int, rt: Runtime) -> Patch:
    kind = rt.kind(i)

    def v(attr):
        return rt.value(i, attr)

    if kind == "circle":
        return MplCircle((0, 0), v("r"))
    if kind == "rect":
        if v("rx") > 0 and v("ry") > 0:
            return PathPatch(_rounded(v("width"), v("height"), v("rx"), v("ry")))
        return Rectangle((0, 0), v("width"), v("height"))
    if kind == "ellipse":
        return MplEllipse((0, 0), 2 * v("rx"), 2 * v("ry"))
    if kind == "line":
        return PathPatch(Path([(v("x1"), v("y1")), (v("x2"), v("y2"))]))
    return Polygon([v("a"), v("b"), v("c")], closed=True)


# A rectangle with elliptical corners, as SVG draws rx and ry: each radius at most half the side.
def _rounded(width: float, height: float, rx: float, ry: float) -> Path:
    rx, ry = min(rx, width / 2), min(ry, height / 2)
    # A quarter ellipse as one cubic Bezier curve, the usual close fit.
    k = 0.5522847498
    w, h = width, height
    vertices = [
        (rx, 0),
        (w - rx, 0),
        (w - rx + k * rx, 0),
        (w, ry - k * ry),
        (w, ry),
        (w, h - ry),
        (w, h - ry + k * ry),
        (w - rx + k * rx, h),
        (w - rx, h),
        (rx, h),
        (rx - k * rx, h),
        (0, h - ry + k * ry),
        (0, h - ry),
        (0, ry),
        (0, ry - k * ry),
        (rx - k * rx, 0),
        (rx, 0),
        (rx, 0),
    ]
    codes = [Path.MOVETO, Path.LINETO, *[Path.CURVE4] * 3, Path.LINETO, *[Path.CURVE4] * 3]
    codes += [Path.LINETO, *[Path.CURVE4] * 3, Path.LINETO, *[Path.CURVE4] * 3, Path.CLOSEPOLY]
    return Path(vertices, codes)


def _affine(matrix: Matrix) -> Affine2D:
    (a, b, c), (d, e, f), _ = matrix.rows
    return Affine2D.from_values(a, d, b, e, c, f)


# How much a matrix scales lengths; for a stretch that differs by direction, an average.
def _scale(matrix: Matrix) -> float:
    (a, b, _), (d, e, _), _ = matrix.rows
    return math.sqrt(abs(a * e - b * d))


def _paint(rt: Runtime, i: int, attr: str):
    color = rt.value(i, attr)
    if color == "none":
        return "none"
    try:
        r, g, b, a = to_rgba(color)
    except ValueError:
        raise EvalError(f"{color!r} is not a color") from None
    return r, g, b, a * rt.value(i, f"{attr}-opacity") * rt.opacity(i)
