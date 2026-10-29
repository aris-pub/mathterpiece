import math
import random
from typing import Any, get_args

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import Circle as MplCircle
from matplotlib.patches import Ellipse as MplEllipse
from matplotlib.patches import Patch, PathPatch, Polygon, Rectangle
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D, Transform

from mathterpiece.compiler import ARITHMETIC, AXES, COMPARISONS, PROPERTIES
from mathterpiece.compiler import _fold as fold
from mathterpiece.matrix import IDENTITY, Matrix, compose
from mathterpiece.model import (
    Bound,
    Canvas,
    Circle,
    Ellipse,
    Group,
    Inherit,
    Line,
    Local,
    Model,
    Motif,
    Obj,
    Real,
    Rect,
    Text,
    Triangle,
    Visual,
    attributes,
    local_names,
)
from mathterpiece.nodes import (
    BoolLit,
    ComplexLit,
    Form,
    InterpStrLit,
    IntLit,
    ListLit,
    Name,
    Node,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.stdlib import STDLIB, power, show, translate
from mathterpiece.stdlib import call as stdlib_call

LITERALS = (IntLit, RatioLit, RealLit, ComplexLit, BoolLit, StrLit)


# Properties that are positions, so reading them from another frame converts them like x and y.
POINT_PROPERTIES = {
    cls: {n for n in props if n != "size"} - {"r"} for cls, props in PROPERTIES.items()
}


class EvalError(Exception):
    pass


class Evaluator:
    def __init__(self, model: Model, rng: random.Random | None = None):
        self.model = model
        self.rng = rng or random.Random()
        self.cache: dict[tuple[int, str], Any] = {}
        self.active: set[tuple[int, str]] = set()
        # The innermost motif around each object, whose body the object's expressions live in.
        self.enclosing: dict[int, Motif | None] = {}
        # The group or motif each object sits in, whose coordinates its x and y are given in.
        self.parent: dict[int, Group | Motif | None] = {}
        self.locals: dict[int, dict[str, Obj]] = {}
        self.frames: dict[int, Matrix] = {}
        stack: list[tuple[Obj, Motif | None, Group | Motif | None]] = [
            (o, None, None) for o in model.objects
        ]
        while stack:
            obj, around, parent = stack.pop()
            self.enclosing[id(obj)] = around
            self.parent[id(obj)] = parent
            if isinstance(obj, Motif):
                self.locals[id(obj)] = local_names(obj)
                stack.extend((m, obj, obj) for m in obj.members)
            elif isinstance(obj, Group):
                stack.extend((m, around, obj) for m in obj.members)

    def value(self, obj: Obj, attr: str) -> Any:
        key = (id(obj), attr)
        if key in self.cache:
            return self.cache[key]
        if key in self.active:
            raise EvalError(f"cycle through {obj.name or 'an anonymous object'}.{attr}")
        is_param = isinstance(obj, Motif) and attr in obj.params
        if isinstance(obj, Motif) and is_param:
            param = obj.params[attr]
        else:
            param = getattr(obj, attributes(type(obj))[attr].name)
        if isinstance(param, Bound):
            self.active.add(key)
            try:
                result = self.eval(param.expr, obj)
            finally:
                self.active.discard(key)
            if not is_param:
                (declared,) = get_args(attributes(type(obj))[attr].type)
                result = float(result) if declared is float else result
        elif isinstance(param, Inherit):
            around = self.enclosing.get(id(obj))
            field = attributes(type(obj))[attr]
            result = self.value(around, attr) if around is not None else field.default.value
        else:
            result = param.value
        self.cache[key] = result
        return result

    # Maps the coordinates of a container's members to scene coordinates. A motif's own x and y
    # sit outside its transform, as in Unity or Godot.
    def frame(self, container: Obj | None) -> Matrix:
        if container is None:
            return IDENTITY
        if id(container) not in self.frames:
            local = self.value(container, "transform")
            if isinstance(container, Motif):
                local = translate(self.value(container, "x"), self.value(container, "y")) @ local
            self.frames[id(container)] = self.frame(self.parent.get(id(container))) @ local
        return self.frames[id(container)]

    # The container whose coordinates an expression owned by obj reads x and y in.
    def reading_frame(self, obj: Obj) -> Obj | None:
        if not isinstance(obj, Local):
            return self.parent.get(id(obj))
        if obj.owner is None:
            return None
        return obj.owner if obj.inside else self.parent.get(id(obj.owner))

    # x and y read by an expression are given in the coordinates the reader itself is placed in.
    def read(self, obj: Obj, attr: str, reader: Obj) -> Any:
        same_frame = self.parent.get(id(obj)) is self.reading_frame(reader)
        if attr in ("x", "y") and same_frame:
            return self.value(obj, attr)
        if attr in ("x", "y", "pos") or attr in POINT_PROPERTIES.get(type(obj), ()):
            if attr in ("x", "y", "pos"):
                point = self.value(obj, "x"), self.value(obj, "y")
            else:
                point = self.property(obj, attr)
            point = self.convert(point, self.parent.get(id(obj)), self.reading_frame(reader))
            return point if attr not in ("x", "y") else point[0 if attr == "x" else 1]
        if attr in PROPERTIES.get(type(obj), {}):
            return self.property(obj, attr)
        return self.value(obj, attr)

    # A point given in the coordinates of one container, in the coordinates of another.
    def convert(self, point: tuple, here: Obj | None, there: Obj | None) -> tuple:
        if here is there:
            return tuple(point)
        scene = self.frame(here).apply(*point)
        try:
            return self.frame(there).inverse().apply(*scene)
        except ValueError as e:
            raise EvalError(str(e)) from None

    # The other ways of reading a shape, computed from what it stores, in its parent's coordinates.
    def property(self, obj: Obj, name: str) -> Any:
        v = lambda attr: self.value(obj, attr)  # noqa: E731
        if isinstance(obj, Rect):
            if name == "from":
                return v("x"), v("y")
            if name == "size":
                return v("width"), v("height")
            share = 0.5 if name == "center" else 1
            return v("x") + share * v("width"), v("y") + share * v("height")
        if isinstance(obj, Ellipse):
            return (v("x"), v("y")) if name == "center" else (2 * v("rx"), 2 * v("ry"))
        if isinstance(obj, Line):
            end = (v("x1"), v("y1")) if name == "from" else (v("x2"), v("y2"))
            return v("x") + end[0], v("y") + end[1]
        assert isinstance(obj, Triangle)
        corners = [v("a"), v("b"), v("c")]
        mid = (sum(p[0] for p in corners) / 3, sum(p[1] for p in corners) / 3)
        if name == "center":
            return v("x") + mid[0], v("y") + mid[1]
        return math.dist(mid, corners[0])

    def eval(self, node: Node, owner: Obj) -> Any:
        if isinstance(node, LITERALS):
            return node.value
        if isinstance(node, InterpStrLit):
            return "".join(self.text(part, owner) for part in node.parts)
        if isinstance(node, Name):
            return self.name(node, owner)
        if isinstance(node, ListLit):
            return tuple(float(self.eval(item, owner)) for item in node.items)
        assert isinstance(node, Form)
        return self.call(node, owner)

    def text(self, part: str | Name, owner: Obj) -> str:
        if isinstance(part, str):
            return part
        value = self.name(part, owner)
        return " ".join(show(v) for v in value) if isinstance(value, list) else show(value)

    # A part of a list value: x, y, z, or an index.
    def take(self, value: Any, parts: list, owner: Obj) -> Any:
        for part in parts:
            value = value[AXES[part] if isinstance(part, str) else int(self.eval(part, owner))]
        return value

    # Who self is for an expression owned by obj, and which motif body its names resolve in. A let
    # value borrows both from the object that owns it.
    def context(self, obj: Obj) -> tuple[Obj | None, Motif | None]:
        if not isinstance(obj, Local):
            return obj, self.enclosing.get(id(obj))
        owner = obj.owner
        if owner is None:
            return None, None
        if obj.inside:
            assert isinstance(owner, Motif)
            return None, owner
        return owner, self.enclosing.get(id(owner))

    def name(self, node: Name, owner: Obj) -> Any:
        first, *rest = node.parts
        assert isinstance(first, str)
        me, around = self.context(owner)
        if first == "self":
            assert me is not None
            obj = me
        elif around is not None and first in around.params:
            return self.take(self.value(around, first), rest, owner)
        elif around is not None and first in self.locals[id(around)]:
            obj = self.locals[id(around)][first]
        elif first in self.model:
            obj = self.model[first]
        else:
            raise EvalError(f"undefined name {first!r}")
        for i, part in enumerate(rest):
            if isinstance(obj, (Real, Local)):
                return self.take(self.value(obj, "value"), rest[i:], owner)
            if isinstance(part, str):
                if isinstance(obj, Motif) and part in obj.params:
                    return self.take(self.value(obj, part), rest[i + 1 :], owner)
                if isinstance(obj, Motif) and part in self.locals[id(obj)]:
                    obj = self.locals[id(obj)][part]
                    continue
                if isinstance(obj, Group) and part not in attributes(type(obj)):
                    return [self.read(member, part, owner) for member in obj.members]
                return self.take(self.read(obj, part, owner), rest[i + 1 :], owner)
            assert isinstance(obj, Group)
            obj = obj.members[self.eval(part, owner)]
        return self.value(obj, "value") if isinstance(obj, (Real, Local)) else obj

    def call(self, node: Form, owner: Obj) -> Any:
        head = node.items[0]
        assert isinstance(head, Name)
        op = head.parts[0]
        if op == "if":
            test, then, other = node.items[1:]
            return self.eval(then if self.eval(test, owner) else other, owner)
        if op == "cond":
            for clause in node.items[1:]:
                assert isinstance(clause, Form)
                test, result = clause.items
                if (isinstance(test, Name) and test.parts == ("else",)) or self.eval(test, owner):
                    return self.eval(result, owner)
        args: list[Any] = []
        for arg in node.items[1:]:
            value = self.eval(arg, owner)
            args.extend(value if isinstance(value, list) else [value])
        try:
            return self.apply(op, args)
        except (ZeroDivisionError, ValueError) as e:
            raise EvalError(str(e) or "division by zero") from None

    def point(self, obj: Obj) -> tuple[Any, Any]:
        return self.frame(self.parent.get(id(obj))).apply(
            self.value(obj, "x"), self.value(obj, "y")
        )

    # Places a shape drawn around the origin: its own transform, then its x and y, then the
    # transforms of everything it sits in.
    def shape(self, obj: Obj) -> Matrix:
        at = translate(self.value(obj, "x"), self.value(obj, "y"))
        return self.frame(self.parent.get(id(obj))) @ at @ self.value(obj, "transform")

    # Opacity multiplies down the tree, unlike the other style attributes.
    def opacity(self, obj: Obj) -> float:
        around = self.enclosing.get(id(obj))
        outer = self.opacity(around) if around is not None else 1.0
        return outer * self.value(obj, "opacity")

    def apply(self, op: Any, args: list[Any]) -> Any:
        if op in ARITHMETIC:
            return fold(op, args)
        if op == "^":
            result = power(*args)
            if isinstance(result, complex):
                raise EvalError("the result of ^ is not a real number")
            return result
        if op in COMPARISONS:
            return COMPARISONS[op](*args)
        if op == "mod":
            if args[1] == 0:
                raise EvalError("mod by zero")
            return args[0] % args[1]
        if op == "transform":
            return compose(*args)
        if op in STDLIB:
            fn = STDLIB[op]
            kinds = ["point" if isinstance(a, (Obj, tuple)) else "real" for a in args]
            sig = fn.find(kinds)
            assert sig is not None
            values = [self.point(a) if isinstance(a, Obj) else a for a in args]
            return stdlib_call(fn, sig, values, self.rng)
        raise EvalError(f"unknown function {op!r}")


def render(model: Model, rng: random.Random | None = None) -> list[tuple[Figure, Axes]]:
    ev = Evaluator(model, rng)
    figures = []
    for view in model.views:
        assert isinstance(view, Canvas)
        fig, ax = plt.subplots()
        x, y = ev.value(view, "view-x"), ev.value(view, "view-y")
        width, height = ev.value(view, "view-width"), ev.value(view, "view-height")
        ax.set_xlim(x, x + width)
        ax.set_ylim(y, y + height)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)
        center = translate(x + width / 2, y + height / 2)
        to_center = translate(-(x + width / 2), -(y + height / 2))
        matrix = compose(to_center, ev.value(view, "transform"), center)
        to_view = _affine(matrix) + ax.transData
        strokes: list[tuple[Patch, float]] = []
        for member in view.members:
            _draw(member, ax, ev, to_view, strokes)
        _stroke_in_scene_units(fig, ax, strokes, _scale(matrix))
        figures.append((fig, ax))
    return figures


# matplotlib line widths are in points, but stroke-width is in scene units as in SVG, so widths
# are set from how many points one scene unit covers, again whenever the window is resized. The
# transform's scale counts too; for a stretch that differs by direction this is an average.
def _stroke_in_scene_units(fig: Figure, ax: Axes, strokes: list, scale: float):
    def update(event=None):
        ax.apply_aspect()
        (x0, _), (x1, _) = ax.transData.transform([(0, 0), (1, 0)])
        points = (x1 - x0) * 72 / fig.dpi * scale
        for artist, width in strokes:
            artist.set_linewidth(width * points)

    update()
    fig.canvas.mpl_connect("resize_event", update)


def _draw(obj: Visual, ax: Axes, ev: Evaluator, to_view: Transform, strokes: list):
    if isinstance(obj, (Group, Motif)):
        for member in obj.members:
            _draw(member, ax, ev, to_view, strokes)
    elif isinstance(obj, (Circle, Rect, Ellipse, Line, Triangle)):
        shape = ev.shape(obj)
        patch = _outline(obj, ev)
        patch.set_facecolor("none" if isinstance(obj, Line) else _paint(ev, obj, "fill"))
        patch.set_edgecolor(_paint(ev, obj, "stroke"))
        patch.set_transform(_affine(shape) + to_view)
        strokes.append((patch, ev.value(obj, "stroke-width") * _scale(shape)))
        ax.add_patch(patch)
    elif isinstance(obj, Text):
        # Glyph outlines in scene units, so the canvas transform turns and scales the letters
        # the way an SVG transform does.
        value = ev.value(obj, "value")
        glyphs = TextPath((0, 0), value, size=ev.value(obj, "font-size"))
        shape = ev.shape(obj)
        text = PathPatch(
            glyphs,
            facecolor=_paint(ev, obj, "fill"),
            edgecolor=_paint(ev, obj, "stroke"),
            transform=_affine(shape) + to_view,
            label=value,
        )
        strokes.append((text, ev.value(obj, "stroke-width") * _scale(shape)))
        ax.add_patch(text)


# Each shape drawn around its own origin; ev.shape places it.
def _outline(obj: Obj, ev: Evaluator) -> Patch:
    v = lambda attr: ev.value(obj, attr)  # noqa: E731
    if isinstance(obj, Circle):
        return MplCircle((0, 0), v("r"))
    if isinstance(obj, Rect):
        return Rectangle((0, 0), v("width"), v("height"))
    if isinstance(obj, Ellipse):
        return MplEllipse((0, 0), 2 * v("rx"), 2 * v("ry"))
    if isinstance(obj, Line):
        return PathPatch(Path([(v("x1"), v("y1")), (v("x2"), v("y2"))]))
    return Polygon([v("a"), v("b"), v("c")], closed=True)


def _affine(matrix: Matrix) -> Affine2D:
    (a, b, c), (d, e, f), _ = matrix.rows
    return Affine2D.from_values(a, d, b, e, c, f)


# How much a matrix scales lengths; for a stretch that differs by direction, an average.
def _scale(matrix: Matrix) -> float:
    (a, b, _), (d, e, _), _ = matrix.rows
    return math.sqrt(abs(a * e - b * d))


def _paint(ev: Evaluator, obj: Obj, attr: str):
    color = ev.value(obj, attr)
    if color == "none":
        return "none"
    return to_rgba(color, ev.value(obj, f"{attr}-opacity") * ev.opacity(obj))
