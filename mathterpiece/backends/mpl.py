import math
import random
from typing import Any, get_args

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.transforms import Affine2D, Transform

from mathterpiece.compiler import COMPARISONS
from mathterpiece.matrix import compose
from mathterpiece.nodes import (
    BoolLit,
    ComplexLit,
    Form,
    InterpStrLit,
    IntLit,
    Name,
    Node,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.scene import (
    Bound,
    Canvas,
    Circle,
    Compound,
    Group,
    Inherit,
    Obj,
    Real,
    Scene,
    Text,
    Visual,
    attributes,
    local_names,
)
from mathterpiece.stdlib import STDLIB, divide, power, translate
from mathterpiece.stdlib import call as stdlib_call

LITERALS = (IntLit, RatioLit, RealLit, ComplexLit, BoolLit, StrLit)


class EvalError(Exception):
    pass


class Evaluator:
    def __init__(self, scene: Scene, rng: random.Random | None = None):
        self.scene = scene
        self.rng = rng or random.Random()
        self.cache: dict[tuple[int, str], Any] = {}
        self.active: set[tuple[int, str]] = set()
        # The innermost compound around each object, whose body the object's expressions live in.
        self.enclosing: dict[int, Compound | None] = {}
        self.locals: dict[int, dict[str, Obj]] = {}
        stack: list[tuple[Obj, Compound | None]] = [(o, None) for o in scene.objects]
        while stack:
            obj, around = stack.pop()
            self.enclosing[id(obj)] = around
            if isinstance(obj, Compound):
                self.locals[id(obj)] = local_names(obj)
                stack.extend((m, obj) for m in obj.members)
            elif isinstance(obj, Group):
                stack.extend((m, around) for m in obj.members)

    def value(self, obj: Obj, attr: str) -> Any:
        key = (id(obj), attr)
        if key in self.cache:
            return self.cache[key]
        if key in self.active:
            raise EvalError(f"cycle through {obj.name or 'an anonymous object'}.{attr}")
        is_param = isinstance(obj, Compound) and attr in obj.params
        if isinstance(obj, Compound) and is_param:
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

    # Where the coordinate system an object's x and y are given in sits, in scene coordinates.
    def origin(self, around: Compound | None) -> tuple[float, float]:
        if around is None:
            return 0.0, 0.0
        x, y = self.origin(self.enclosing.get(id(around)))
        return x + self.value(around, "x"), y + self.value(around, "y")

    # x and y read by an expression are given in the coordinates of the body the reader is in.
    def read(self, obj: Obj, attr: str, reader: Obj) -> Any:
        result = self.value(obj, attr)
        if attr in ("x", "y"):
            i = 0 if attr == "x" else 1
            here = self.origin(self.enclosing.get(id(obj)))[i]
            there = self.origin(self.enclosing.get(id(reader)))[i]
            result = result + here - there
        return result

    def eval(self, node: Node, owner: Obj) -> Any:
        if isinstance(node, LITERALS):
            return node.value
        if isinstance(node, InterpStrLit):
            return "".join(self.text(part, owner) for part in node.parts)
        if isinstance(node, Name):
            return self.name(node, owner)
        assert isinstance(node, Form)
        return self.call(node, owner)

    def text(self, part: str | Name, owner: Obj) -> str:
        if isinstance(part, str):
            return part
        value = self.name(part, owner)
        return " ".join(str(v) for v in value) if isinstance(value, list) else str(value)

    def name(self, node: Name, owner: Obj) -> Any:
        first, *rest = node.parts
        assert isinstance(first, str)
        around = self.enclosing.get(id(owner))
        if first == "self":
            obj = owner
        elif around is not None and first in around.params:
            return self.value(around, first)
        elif around is not None and first in self.locals[id(around)]:
            obj = self.locals[id(around)][first]
        elif first in self.scene:
            obj = self.scene[first]
        else:
            raise EvalError(f"undefined name {first!r}")
        for part in rest:
            if isinstance(part, str):
                if isinstance(obj, Compound) and part in obj.params:
                    return self.value(obj, part)
                if isinstance(obj, Compound) and part in self.locals[id(obj)]:
                    obj = self.locals[id(obj)][part]
                    continue
                if isinstance(obj, Group) and part != "members":
                    return [self.read(member, part, owner) for member in obj.members]
                return self.read(obj, part, owner)
            assert isinstance(obj, Group)
            obj = obj.members[self.eval(part, owner)]
        return self.value(obj, "value") if isinstance(obj, Real) else obj

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
        x, y = self.origin(self.enclosing.get(id(obj)))
        return x + self.value(obj, "x"), y + self.value(obj, "y")

    # Opacity multiplies down the tree, unlike the other style attributes.
    def opacity(self, obj: Obj) -> float:
        around = self.enclosing.get(id(obj))
        outer = self.opacity(around) if around is not None else 1.0
        return outer * self.value(obj, "opacity")

    def apply(self, op: Any, args: list[Any]) -> Any:
        if op == "+":
            return sum(args)
        if op == "*":
            return math.prod(args)
        if op == "-":
            return -args[0] if len(args) == 1 else args[0] - sum(args[1:])
        if op == "/":
            result = args[0]
            for arg in args[1:]:
                result = divide(result, arg)
            return result
        if op == "^":
            result = power(*args)
            if isinstance(result, complex):
                raise EvalError("the result of ^ is not a real number")
            return result
        if op in COMPARISONS:
            return COMPARISONS[op](*args)
        if op == "transform":
            return compose(*args)
        if op in STDLIB:
            fn = STDLIB[op]
            kinds = ["point" if isinstance(a, Obj) else "real" for a in args]
            sig = fn.find(kinds)
            assert sig is not None
            values = [self.point(a) if isinstance(a, Obj) else a for a in args]
            return stdlib_call(fn, sig, values, self.rng)
        raise EvalError(f"unknown function {op!r}")


def render(scene: Scene, rng: random.Random | None = None) -> list[tuple[Figure, Axes]]:
    ev = Evaluator(scene, rng)
    figures = []
    for view in scene.views:
        assert isinstance(view, Canvas)
        fig, ax = plt.subplots()
        x, y = ev.value(view, "view-x"), ev.value(view, "view-y")
        width, height = ev.value(view, "view-width"), ev.value(view, "view-height")
        ax.set_xlim(x, x + width)
        ax.set_ylim(y, y + height)
        center = translate(x + width / 2, y + height / 2)
        to_center = translate(-(x + width / 2), -(y + height / 2))
        matrix = compose(to_center, ev.value(view, "transform"), center)
        (a, b, c), (d, e, f), _ = matrix.rows
        to_view = Affine2D.from_values(a, d, b, e, c, f) + ax.transData
        for member in view.members:
            _draw(member, ax, ev, to_view)
        figures.append((fig, ax))
    return figures


def _draw(obj: Visual, ax: Axes, ev: Evaluator, to_view: Transform):
    if isinstance(obj, (Group, Compound)):
        for member in obj.members:
            _draw(member, ax, ev, to_view)
    elif isinstance(obj, Circle):
        circle = plt.Circle(
            ev.point(obj),
            ev.value(obj, "r"),
            facecolor=_paint(ev, obj, "fill"),
            edgecolor=_paint(ev, obj, "stroke"),
            linewidth=ev.value(obj, "stroke-width"),
            transform=to_view,
        )
        ax.add_artist(circle)
    elif isinstance(obj, Text):
        ax.text(
            *ev.point(obj),
            ev.value(obj, "value"),
            color=_paint(ev, obj, "fill"),
            transform=to_view,
        )


def _paint(ev: Evaluator, obj: Obj, attr: str):
    color = ev.value(obj, attr)
    if color == "none":
        return "none"
    return to_rgba(color, ev.value(obj, f"{attr}-opacity") * ev.opacity(obj))
