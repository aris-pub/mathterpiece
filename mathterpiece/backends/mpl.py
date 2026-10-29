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
    Group,
    Obj,
    Real,
    Scene,
    Text,
    Visual,
    attributes,
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

    def value(self, obj: Obj, attr: str) -> Any:
        key = (id(obj), attr)
        if key in self.cache:
            return self.cache[key]
        if key in self.active:
            raise EvalError(f"cycle through {obj.name or 'an anonymous object'}.{attr}")
        param = getattr(obj, attributes(type(obj))[attr].name)
        if isinstance(param, Bound):
            self.active.add(key)
            try:
                result = self.eval(param.expr, obj)
            finally:
                self.active.discard(key)
            (declared,) = get_args(attributes(type(obj))[attr].type)
            result = float(result) if declared is float else result
        else:
            result = param.value
        self.cache[key] = result
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
        if first == "self":
            obj = owner
        elif first in self.scene:
            obj = self.scene[first]
        else:
            raise EvalError(f"undefined name {first!r}")
        for part in rest:
            if isinstance(part, str):
                if isinstance(obj, Group) and part != "members":
                    return [self.value(member, part) for member in obj.members]
                return self.value(obj, part)
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
        return self.value(obj, "x"), self.value(obj, "y")

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
    if isinstance(obj, Group):
        for member in obj.members:
            _draw(member, ax, ev, to_view)
    elif isinstance(obj, Circle):
        circle = plt.Circle(
            (ev.value(obj, "x"), ev.value(obj, "y")),
            ev.value(obj, "r"),
            facecolor=_paint(ev, obj, "fill"),
            edgecolor=_paint(ev, obj, "stroke"),
            linewidth=ev.value(obj, "stroke-width"),
            transform=to_view,
        )
        ax.add_artist(circle)
    elif isinstance(obj, Text):
        ax.text(
            ev.value(obj, "x"),
            ev.value(obj, "y"),
            ev.value(obj, "value"),
            color=_paint(ev, obj, "fill"),
            transform=to_view,
        )


def _paint(ev: Evaluator, obj: Obj, attr: str):
    color = ev.value(obj, attr)
    if color == "none":
        return "none"
    return to_rgba(color, ev.value(obj, f"{attr}-opacity") * ev.value(obj, "opacity"))
