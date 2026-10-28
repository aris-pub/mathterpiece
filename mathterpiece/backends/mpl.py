import math
import random
from fractions import Fraction
from typing import Any, get_args

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

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

LITERALS = (IntLit, RatioLit, RealLit, ComplexLit, BoolLit, StrLit)


class EvalError(Exception):
    pass


def _exact(x) -> bool:
    return isinstance(x, (int, Fraction)) and not isinstance(x, bool)


def _divide(a, b):
    if b == 0:
        raise EvalError("division by zero")
    return Fraction(a) / b if _exact(a) and _exact(b) else a / b


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
        param = getattr(obj, attr)
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
        args: list[Any] = []
        for arg in node.items[1:]:
            value = self.eval(arg, owner)
            args.extend(value if isinstance(value, list) else [value])
        if op == "+":
            return sum(args)
        if op == "*":
            return math.prod(args)
        if op == "-":
            return -args[0] if len(args) == 1 else args[0] - sum(args[1:])
        if op == "/":
            result = args[0]
            for arg in args[1:]:
                result = _divide(result, arg)
            return result
        if op == "rand":
            return self.rng.uniform(float(args[0]), float(args[1])) if args else self.rng.random()
        raise EvalError(f"unknown function {op!r}")


def render(scene: Scene, rng: random.Random | None = None) -> list[tuple[Figure, Axes]]:
    ev = Evaluator(scene, rng)
    figures = []
    for view in scene.views:
        assert isinstance(view, Canvas)
        fig, ax = plt.subplots()
        ax.set_xlim(ev.value(view, "xmin"), ev.value(view, "xmax"))
        ax.set_ylim(ev.value(view, "ymin"), ev.value(view, "ymax"))
        for member in view.members:
            _draw(member, ax, ev)
        figures.append((fig, ax))
    return figures


def _draw(obj: Visual, ax: Axes, ev: Evaluator):
    if isinstance(obj, Group):
        for member in obj.members:
            _draw(member, ax, ev)
    elif isinstance(obj, Circle):
        circle = plt.Circle(
            (ev.value(obj, "x"), ev.value(obj, "y")),
            ev.value(obj, "r"),
            facecolor=ev.value(obj, "facecolor"),
            fill=ev.value(obj, "fill"),
            edgecolor=ev.value(obj, "edgecolor"),
            linewidth=ev.value(obj, "linewidth"),
            alpha=ev.value(obj, "alpha"),
        )
        ax.add_artist(circle)
    elif isinstance(obj, Text):
        ax.text(
            ev.value(obj, "x"),
            ev.value(obj, "y"),
            ev.value(obj, "value"),
            color=ev.value(obj, "facecolor"),
            alpha=ev.value(obj, "alpha"),
        )
