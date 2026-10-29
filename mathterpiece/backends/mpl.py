import math
import random
import sys
import time
from dataclasses import dataclass
from typing import Any, get_args

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import is_color_like, to_hex, to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import Circle as MplCircle
from matplotlib.patches import Ellipse as MplEllipse
from matplotlib.patches import Patch, PathPatch, Polygon, Rectangle
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D, Transform
from matplotlib.widgets import Button as MplButton
from matplotlib.widgets import Slider as MplSlider

from mathterpiece.compiler import ARITHMETIC, AXES, COMPARISONS, PROPERTIES
from mathterpiece.compiler import _fold as fold
from mathterpiece.matrix import IDENTITY, Matrix, compose
from mathterpiece.model import (
    PYTHON_FRAMES,
    RECURSION_LIMIT,
    Bound,
    Button,
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
    Play,
    Real,
    Rect,
    Slider,
    State,
    Steps,
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
        self.depth = 0
        # Values controls have written, which replace what the model gave.
        self.written: dict[tuple[int, str], Any] = {}
        # Texts in the middle of changing: the old text, and how far the change has gone (0 to 1).
        self.morphs: dict[int, tuple[str, float]] = {}
        sys.setrecursionlimit(max(sys.getrecursionlimit(), PYTHON_FRAMES))
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

    # Whether all of a state's conditions hold. Numbers compared by = count as equal within a
    # small tolerance, so that a state still counts after a drag or an animation.
    def holds(self, state: State) -> bool:
        for cond in state.conditions:
            if isinstance(cond, Form) and _op(cond) == "=" and len(cond.items) == 3:
                if not _close(self.eval(cond.items[1], state), self.eval(cond.items[2], state)):
                    return False
            elif not self.eval(cond, state):
                return False
        return True

    # Where reaching a state leads from here: each moved value and what it moves to now.
    def targets(self, state: State) -> list[tuple[Obj, str, Any]]:
        return [(obj, attr, self.eval(expr, state)) for obj, attr, expr in state.moves]

    # A control's write. Everything computed is dropped, since anything might depend on it.
    def write(self, obj: Obj, attr: str, value: Any):
        self.written[(id(obj), attr)] = value
        self.cache.clear()
        self.frames.clear()

    def value(self, obj: Obj, attr: str) -> Any:
        key = (id(obj), attr)
        if key in self.written:
            return self.written[key]
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

    # env holds the parameters and let names of the function body being evaluated, if any.
    def eval(self, node: Node, owner: Obj, env: dict | None = None) -> Any:
        env = env or {}
        if isinstance(node, LITERALS):
            return node.value
        if isinstance(node, InterpStrLit):
            return "".join(self.text(part, owner, env) for part in node.parts)
        if isinstance(node, Name):
            return self.name(node, owner, env)
        if isinstance(node, ListLit):
            return tuple(float(self.eval(item, owner, env)) for item in node.items)
        assert isinstance(node, Form)
        return self.call(node, owner, env)

    def text(self, part: str | Name, owner: Obj, env: dict) -> str:
        if isinstance(part, str):
            return part
        value = self.name(part, owner, env)
        return " ".join(show(v) for v in value) if isinstance(value, list) else show(value)

    # A part of a list value: x, y, z, or an index.
    def take(self, value: Any, parts: list, owner: Obj, env: dict) -> Any:
        for part in parts:
            i = AXES[part] if isinstance(part, str) else int(self.eval(part, owner, env))
            value = value[i]
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

    def name(self, node: Name, owner: Obj, env: dict) -> Any:
        first, *rest = node.parts
        assert isinstance(first, str)
        me, around = self.context(owner)
        if first in env and not isinstance(env[first], Obj):
            return self.take(env[first], rest, owner, env)
        if first in env:
            obj = env[first]
        elif first == "self":
            assert me is not None
            obj = me
        elif around is not None and first in around.params:
            return self.take(self.value(around, first), rest, owner, env)
        elif around is not None and first in self.locals[id(around)]:
            obj = self.locals[id(around)][first]
        elif first in self.model:
            obj = self.model[first]
        else:
            raise EvalError(f"undefined name {first!r}")
        for i, part in enumerate(rest):
            if isinstance(obj, (Real, Local)):
                return self.take(self.value(obj, "value"), rest[i:], owner, env)
            if isinstance(part, str):
                if isinstance(obj, Motif) and part in obj.params:
                    return self.take(self.value(obj, part), rest[i + 1 :], owner, env)
                if isinstance(obj, Motif) and part in self.locals[id(obj)]:
                    obj = self.locals[id(obj)][part]
                    continue
                if isinstance(obj, Group) and part not in attributes(type(obj)):
                    return [self.read(member, part, owner) for member in obj.members]
                return self.take(self.read(obj, part, owner), rest[i + 1 :], owner, env)
            assert isinstance(obj, Group)
            obj = obj.members[self.eval(part, owner, env)]
        return self.value(obj, "value") if isinstance(obj, (Real, Local)) else obj

    def call(self, node: Form, owner: Obj, env: dict) -> Any:
        head = node.items[0]
        assert isinstance(head, Name)
        op = head.parts[0]
        if op == "if":
            test, then, other = node.items[1:]
            return self.eval(then if self.eval(test, owner, env) else other, owner, env)
        if op == "cond":
            for clause in node.items[1:]:
                assert isinstance(clause, Form)
                test, result = clause.items
                is_else = isinstance(test, Name) and test.parts == ("else",)
                if is_else or self.eval(test, owner, env):
                    return self.eval(result, owner, env)
        if op == "let":
            inner = dict(env)
            pairs = node.items[1]
            assert isinstance(pairs, Form)
            for pair in pairs.items:
                assert isinstance(pair, Form)
                key, expr = pair.items
                assert isinstance(key, Name) and isinstance(key.parts[0], str)
                inner[key.parts[0]] = self.eval(expr, owner, inner)
            return self.eval(node.items[2], owner, inner)
        args: list[Any] = []
        for arg in node.items[1:]:
            value = self.eval(arg, owner, env)
            args.extend(value if isinstance(value, list) else [value])
        if op in self.model.functions:
            return self.call_function(op, args, owner)
        try:
            return self.apply(op, args)
        except (ZeroDivisionError, ValueError) as e:
            raise EvalError(str(e) or "division by zero") from None

    def call_function(self, key: str, args: list[Any], owner: Obj) -> Any:
        if self.depth >= RECURSION_LIMIT:
            raise EvalError(f"recursion is deeper than {RECURSION_LIMIT} calls")
        fn = self.model.functions[key]
        env = {
            name: args[i] if i < len(args) else default
            for i, (name, default) in enumerate(fn.params)
        }
        self.depth += 1
        try:
            return self.eval(fn.body, owner, env)
        finally:
            self.depth -= 1

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
        if op == "abs":
            return abs(args[0])
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
    figures: list[tuple[Figure, Axes]] = []
    for view in model.views:
        assert isinstance(view, Canvas)
        fig, ax = plt.subplots()
        strokes: list[tuple[Patch, float]] = []
        _draw_canvas(view, ax, ev, strokes)
        _stroke_in_scene_units(fig, ax, strokes)
        figures.append((fig, ax))
        _canvases.setdefault(fig, []).append((view, ax, strokes))
    if model.controls:
        if not figures:
            fig = plt.figure()
            figures.append((fig, fig.add_axes((0, 0, 1, 1), frame_on=False)))
        _add_controls(model, ev, [f for f, _ in figures])
    return figures


# The canvases each figure shows, for redrawing them after a control writes.
_canvases: dict[Figure, list[tuple[Canvas, Axes, list]]] = {}
_widgets: dict[Figure, dict[str, Any]] = {}
_presses: dict[Figure, dict[Any, Any]] = {}


def controls(fig: Figure) -> dict[str, Any]:
    """The matplotlib widgets for a figure's controls, by name."""
    return _widgets.get(fig, {})


def press(fig: Figure, name: str):
    """Does what clicking a button or a play button does."""
    _presses[fig][name]()


def _draw_canvas(view: Canvas, ax: Axes, ev: Evaluator, strokes: list):
    ax.clear()
    strokes.clear()
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
    for member in view.members:
        _draw(member, ax, ev, to_view, strokes, _scale(matrix))


# Controls go along the bottom of the first figure, one row each, and redraw every canvas when
# they write.
def _add_controls(model: Model, ev: Evaluator, figures: list[Figure]):
    host = figures[0]
    rows = len(model.controls)
    host.subplots_adjust(bottom=0.08 + 0.06 * rows)
    widgets: dict[str, Any] = {}
    presses: dict[Any, Any] = {}
    sliders: list[tuple[Any, Slider]] = []
    steps: list[tuple[list[Any], Steps]] = []

    def redraw():
        for fig in figures:
            for view, ax, strokes in _canvases.get(fig, []):
                _draw_canvas(view, ax, ev, strokes)
                _update_strokes(fig, ax, strokes)
        # Sliders follow values that something else moved, without counting as user input.
        for slider, control in sliders:
            assert control.target is not None
            slider.eventson = False
            slider.set_val(ev.value(control.target, control.attr))
            slider.eventson = True
        for buttons, control in steps:
            for button, state in zip(buttons, control.states, strict=True):
                button.color = LIT if ev.holds(state) else UNLIT
                button.ax.set_facecolor(button.color)
        for fig in figures:
            fig.canvas.draw_idle()

    animator = _Animator(ev, redraw, host)
    for row, control in enumerate(model.controls):
        assert control.name is not None
        box = (0.25, 0.02 + 0.06 * (rows - 1 - row), 0.5, 0.04)
        label = ev.value(control, "label")
        if isinstance(control, Slider):
            target, attr, kind = control.target, control.attr, control.kind
            assert target is not None
            slider = MplSlider(
                host.add_axes(box),
                label,
                ev.value(control, "min"),
                ev.value(control, "max"),
                valinit=ev.value(target, attr),
                valstep=1 if kind == "int" else ev.value(control, "step"),
            )
            slider.valtext.set_visible(False)

            def moved(value, target=target, attr=attr, kind=kind):
                animator.cancel()
                ev.write(target, attr, int(round(value)) if kind == "int" else float(value))
                redraw()

            slider.on_changed(moved)
            widgets[control.name] = slider
            sliders.append((slider, control))
        elif isinstance(control, Steps):
            n = len(control.states)
            buttons = []
            for i, state in enumerate(control.states):
                x, y, w, h = box
                cell = host.add_axes((x + w * i / n, y, w / n, h))
                button = MplButton(cell, state.name or str(i))

                def chosen(control=control, state=state):
                    animator.cancel()
                    animator.go(state, ev.value(control, "duration"), ev.value(control, "ease"))

                button.on_clicked(lambda _event, chosen=chosen: chosen())
                buttons.append(button)
                presses[(control.name, i)] = chosen
            widgets[control.name] = buttons
            steps.append((buttons, control))
        elif isinstance(control, (Button, Play)):
            button = MplButton(host.add_axes(box), label)
            if isinstance(control, Button):

                def pressed(control=control):
                    assert control.state is not None
                    animator.cancel()
                    duration, ease = ev.value(control, "duration"), ev.value(control, "ease")
                    animator.go(control.state, duration, ease)

            else:

                def pressed(control=control):
                    animator.play(control)

            button.on_clicked(lambda _event, pressed=pressed: pressed())
            widgets[control.name] = button
            presses[control.name] = pressed
    _widgets[host] = widgets
    _presses[host] = presses
    _animators[host] = animator
    redraw()


LIT, UNLIT = "#9ecae1", "0.85"
EASES = {
    "linear": lambda t: t,
    "ease-in": lambda t: t * t * t,
    "ease-out": lambda t: 1 - (1 - t) ** 3,
    "ease-in-out": lambda t: 4 * t**3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
}
_animators: dict[Figure, "_Animator"] = {}


def choose(fig: Figure, name: str, index: int):
    """Does what clicking a step does."""
    _presses[fig][(name, index)]()


def advance(fig: Figure, seconds: float):
    """Moves a figure's animations forward, as if that much time had passed."""
    _animators[fig].tick(seconds)


# One value moving toward a state, from where it was to the target worked out when the move
# started.
@dataclass
class _Track:
    obj: Obj
    attr: str
    begin: Any
    target: Any
    start: float
    duration: float
    ease: str


# Runs the animations of buttons, steps and tours. Time is in seconds since the figure opened;
# a matplotlib timer moves it forward while something is moving.
class _Animator:
    def __init__(self, ev: Evaluator, redraw, fig: Figure):
        self.ev = ev
        self.redraw = redraw
        self.now = 0.0
        self.tracks: list[_Track] = []
        self.tour: Play | None = None
        self.step = 0
        self.step_start = 0.0
        # When the current text morphs started and end.
        self.morph_start = self.morph_end = 0.0
        self.timer = fig.canvas.new_timer(interval=16)
        self.timer.add_callback(self.frame)
        self.last = time.monotonic()

    def cancel(self):
        self.tracks.clear()
        self.tour = None
        self.ev.morphs.clear()

    def go(self, state: State, duration: float, ease: str, start: float | None = None):
        start = self.now if start is None else start
        for obj, attr, target in self.ev.targets(state):
            begin = self.ev.value(obj, attr)
            if duration > 0 and isinstance(obj, Text) and attr == "value" and begin != target:
                self.ev.morphs[id(obj)] = (begin, 0.0)
                self.morph_start, self.morph_end = start, start + duration
            if duration > 0 and _blendable(begin, target):
                self.tracks.append(_Track(obj, attr, begin, target, start, duration, ease))
            else:
                self.ev.write(obj, attr, target)
        self.redraw()
        self.wake()

    def play(self, tour: Play):
        self.cancel()
        if tour.start is not None:
            for obj, attr, target in self.ev.targets(tour.start):
                self.ev.write(obj, attr, target)
        self.tour = tour
        self.step = 0
        self.step_start = self.now
        self.begin_step()
        self.redraw()
        self.wake()

    def begin_step(self):
        assert self.tour is not None
        step = self.tour.steps[self.step]
        if step.kind == "to":
            assert step.state is not None
            self.go(step.state, step.duration.value, step.ease.value, start=self.step_start)

    def tick(self, seconds: float):
        self.now += seconds
        while self.tour is not None:
            step = self.tour.steps[self.step]
            end = self.step_start + step.duration.value
            if self.now < end:
                break
            self.update(end)
            self.step += 1
            self.step_start = end
            if self.step == len(self.tour.steps):
                self.tour = None
            else:
                self.begin_step()
        self.update(self.now)
        self.redraw()

    # Writes every moving value for the given moment, and drops the ones that have arrived.
    def update(self, now: float):
        for track in list(self.tracks):
            t = 1.0 if track.duration == 0 else min(1.0, (now - track.start) / track.duration)
            value = _blend(track.begin, track.target, EASES[track.ease](t))
            self.ev.write(track.obj, track.attr, track.target if t >= 1 else value)
            if t >= 1:
                self.tracks.remove(track)
        if self.ev.morphs:
            span = max(self.morph_end - self.morph_start, 1e-12)
            t = min(1.0, (now - self.morph_start) / span)
            self.ev.morphs = {k: (old, t) for k, (old, _) in self.ev.morphs.items()}
            if t >= 1:
                self.ev.morphs.clear()

    def wake(self):
        self.last = time.monotonic()
        self.timer.start()

    def frame(self):
        now = time.monotonic()
        self.tick(now - self.last)
        self.last = now
        if not self.tracks and self.tour is None and not self.ev.morphs:
            self.timer.stop()


def _is_color(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value == "none" or is_color_like(value)


def _blendable(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return True
    if isinstance(a, tuple) and isinstance(b, tuple):
        return len(a) == len(b)
    return _is_color(a) and _is_color(b) and a != b


# Partway from a to b. Colors blend in RGB, and 'none' counts as the other color, transparent.
def _blend(a: Any, b: Any, t: float) -> Any:
    if isinstance(a, tuple):
        return tuple(x + (y - x) * t for x, y in zip(a, b, strict=True))
    if isinstance(a, str):
        ca = to_rgba(b if a == "none" else a, 0 if a == "none" else None)
        cb = to_rgba(a if b == "none" else b, 0 if b == "none" else None)
        mixed = tuple(x + (y - x) * t for x, y in zip(ca, cb, strict=True))
        return to_hex(mixed, keep_alpha=True)  # ty: ignore[invalid-argument-type]
    result = a + (b - a) * t
    return int(round(result)) if isinstance(a, int) and isinstance(b, int) else result


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
def _draw(
    obj: Visual, ax: Axes, ev: Evaluator, to_view: Transform, strokes: list, view_scale: float
):
    if isinstance(obj, (Group, Motif)):
        for member in obj.members:
            _draw(member, ax, ev, to_view, strokes, view_scale)
    elif isinstance(obj, (Circle, Rect, Ellipse, Line, Triangle)):
        shape = ev.shape(obj)
        patch = _outline(obj, ev)
        patch.set_facecolor("none" if isinstance(obj, Line) else _paint(ev, obj, "fill"))
        patch.set_edgecolor(_paint(ev, obj, "stroke"))
        patch.set_transform(_affine(shape) + to_view)
        strokes.append((patch, ev.value(obj, "stroke-width") * _scale(shape) * view_scale))
        ax.add_patch(patch)
    elif isinstance(obj, Text):
        # Glyph outlines in scene units, so the canvas transform turns and scales the letters
        # the way an SVG transform does.
        # A text in the middle of changing is drawn twice: the old one fading out, the new one in.
        # That is the best matplotlib can do for morphing one text into another.
        shape = ev.shape(obj)
        old, progress = ev.morphs.get(id(obj), (None, 1.0))
        shown = [(ev.value(obj, "value"), progress)]
        if old is not None:
            shown.append((old, 1 - progress))
        for value, fade in shown:
            glyphs = TextPath((0, 0), value, size=ev.value(obj, "font-size"))
            text = PathPatch(
                glyphs,
                facecolor=_paint(ev, obj, "fill", fade),
                edgecolor=_paint(ev, obj, "stroke", fade),
                transform=_affine(shape) + to_view,
                label=value,
            )
            strokes.append((text, ev.value(obj, "stroke-width") * _scale(shape) * view_scale))
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


def _paint(ev: Evaluator, obj: Obj, attr: str, fade: float = 1.0):
    color = ev.value(obj, attr)
    if color == "none":
        return "none"
    r, g, b, a = to_rgba(color)
    return r, g, b, a * ev.value(obj, f"{attr}-opacity") * ev.opacity(obj) * fade


def _op(node: Form) -> str | None:
    head = node.items[0]
    return head.parts[0] if isinstance(head, Name) and isinstance(head.parts[0], str) else None


def _close(a: Any, b: Any) -> bool:
    if isinstance(a, tuple) and isinstance(b, tuple):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b
