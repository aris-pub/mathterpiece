"""The matplotlib backend. It reads the JSON the compiler writes (mathterpiece.export), like any
other backend, and evaluates its resolved operations."""

import math
import random
import sys
import time
from dataclasses import dataclass
from typing import Any

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

from mathterpiece.compiler import ARITHMETIC, COMPARISONS
from mathterpiece.compiler import _fold as fold
from mathterpiece.export import ExportError, export
from mathterpiece.matrix import IDENTITY, Matrix, compose
from mathterpiece.model import PYTHON_FRAMES, RECURSION_LIMIT, Model, Obj
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
CONTROLS = {"slider", "button", "steps", "play"}


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
        # Texts in the middle of changing: the old text, and how far the change has gone (0 to 1).
        self.morphs: dict[int, tuple[str, float]] = {}
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
        if op == "arg":
            return env[args[0]]
        if op == "part":
            base = self.eval(args[0], frame, env)
            index = args[1] if isinstance(args[1], int) else int(self.eval(args[1], frame, env))
            return base[index]
        if op == "obj":
            return _Ref(args[0])
        if op == "splice":
            return _Splice(tuple(self.eval(a, frame, env) for a in args))
        if op == "list":
            return tuple(float(self.eval(a, frame, env)) for a in args)
        if op == "complex":
            return complex(args[0], args[1])
        if op == "str":
            return "".join(a if isinstance(a, str) else self.eval(a, frame, env) for a in args)
        if op == "show":
            value = self.eval(args[0], frame, env)
            spec = args[2] if len(args) > 2 else None
            if isinstance(value, _Splice):
                return " ".join(_show(v, args[1], spec) for v in value.values)
            return _show(value, args[1], spec)
        if op == "if":
            test, then, other = args
            return self.eval(then if self.eval(test, frame, env) else other, frame, env)
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
        if op == "transform":
            return compose(*args)
        if op in STDLIB:
            fn = STDLIB[op]
            kinds = ["point" if isinstance(a, (_Ref, tuple)) else "real" for a in args]
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

    # Where reaching a state leads from here: each moved value and what it moves to now.
    def targets(self, state: int) -> list[tuple[int, str, Any]]:
        moves = self.objects[state]["moves"] or []
        return [(i, attr, self.eval(expr, None, {})) for i, attr, expr in moves]


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

    def targets(self, state: Obj) -> list[tuple[Obj, str, Any]]:
        return [(self.objects[i], a, v) for i, a, v in self.runtime.targets(self.id(state))]


def _all_objects(model: Model) -> list[Obj]:
    out: list[Obj] = []
    stack: list[Obj] = list(model)
    while stack:
        obj = stack.pop()
        out.append(obj)
        members = getattr(obj, "members", None)
        if isinstance(members, list):
            stack.extend(members)
        state = getattr(obj, "state", None)
        if isinstance(state, Obj):
            stack.append(state)
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
        _canvases.setdefault(fig, []).append((obj["id"], ax, strokes))
    controls_ = [o for o in doc["objects"] if o["kind"] in CONTROLS]
    if controls_:
        if not figures:
            fig = plt.figure()
            figures.append((fig, fig.add_axes((0, 0, 1, 1), frame_on=False)))
        _add_controls(controls_, rt, [f for f, _ in figures])
    return figures


# The canvases each figure shows, for redrawing them after a control writes.
_canvases: dict[Figure, list[tuple[int, Axes, list]]] = {}
_widgets: dict[Figure, dict[str, Any]] = {}
_presses: dict[Figure, dict[Any, Any]] = {}


def controls(fig: Figure) -> dict[str, Any]:
    """The matplotlib widgets for a figure's controls, by name."""
    return _widgets.get(fig, {})


def press(fig: Figure, name: str):
    """Does what clicking a button or a play button does."""
    _presses[fig][name]()


def choose(fig: Figure, name: str, index: int):
    """Does what clicking a step does."""
    _presses[fig][(name, index)]()


def advance(fig: Figure, seconds: float):
    """Moves a figure's animations forward, as if that much time had passed."""
    _animators[fig].tick(seconds)


def _draw_canvas(view: int, ax: Axes, rt: Runtime, strokes: list):
    ax.clear()
    strokes.clear()
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
    for member in rt.objects[view]["shows"]:
        _draw(member, ax, rt, to_view, strokes, _scale(matrix))


# Controls go along the bottom of the first figure, one row each, and redraw every canvas when
# they write.
def _add_controls(objects: list[dict], rt: Runtime, figures: list[Figure]):
    host = figures[0]
    rows = len(objects)
    host.subplots_adjust(bottom=0.08 + 0.06 * rows)
    widgets: dict[str, Any] = {}
    presses: dict[Any, Any] = {}
    sliders: list[tuple[Any, dict]] = []
    steps: list[tuple[list[Any], dict]] = []

    def redraw():
        for fig in figures:
            for view, ax, strokes in _canvases.get(fig, []):
                _draw_canvas(view, ax, rt, strokes)
                _update_strokes(fig, ax, strokes)
        # Sliders follow values that something else moved, without counting as user input.
        for slider, control in sliders:
            target, attr = control["target"]
            slider.eventson = False
            slider.set_val(rt.value(target, attr))
            slider.eventson = True
        for buttons, control in steps:
            for button, state in zip(buttons, control["states"], strict=True):
                button.color = LIT if rt.holds(state) else UNLIT
                button.ax.set_facecolor(button.color)
        for fig in figures:
            fig.canvas.draw_idle()

    animator = _Animator(rt, redraw, host)
    for row, control in enumerate(objects):
        name, i = control["name"], control["id"]
        box = (0.25, 0.02 + 0.06 * (rows - 1 - row), 0.5, 0.04)
        label = rt.value(i, "label")
        if control["kind"] == "slider":
            target, attr = control["target"]
            whole = control["type"] == "int"
            slider = MplSlider(
                host.add_axes(box),
                label,
                rt.value(i, "min"),
                rt.value(i, "max"),
                valinit=rt.value(target, attr),
                valstep=1 if whole else rt.value(i, "step"),
            )
            slider.valtext.set_visible(False)

            def moved(value, target=target, attr=attr, whole=whole):
                animator.cancel()
                rt.write(target, attr, int(round(value)) if whole else float(value))
                redraw()

            slider.on_changed(moved)
            widgets[name] = slider
            sliders.append((slider, control))
        elif control["kind"] == "steps":
            n = len(control["states"])
            buttons = []
            for k, state in enumerate(control["states"]):
                x, y, w, h = box
                cell = host.add_axes((x + w * k / n, y, w / n, h))
                button = MplButton(cell, rt.objects[state]["name"] or str(k))

                def chosen(i=i, state=state):
                    animator.cancel()
                    animator.go(state, rt.value(i, "duration"), rt.value(i, "ease"))

                button.on_clicked(lambda _event, chosen=chosen: chosen())
                buttons.append(button)
                presses[(name, k)] = chosen
            widgets[name] = buttons
            steps.append((buttons, control))
        else:
            button = MplButton(host.add_axes(box), label)
            if control["kind"] == "button":

                def pressed(i=i, state=control["state"]):
                    animator.cancel()
                    animator.go(state, rt.value(i, "duration"), rt.value(i, "ease"))

            else:

                def pressed(control=control):
                    animator.play(control)

            button.on_clicked(lambda _event, pressed=pressed: pressed())
            widgets[name] = button
            presses[name] = pressed
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


# One value moving toward a state, from where it was to the target worked out when the move
# started.
@dataclass
class _Track:
    obj: int
    attr: str
    begin: Any
    target: Any
    start: float
    duration: float
    ease: str


# Runs the animations of buttons, steps and tours. Time is in seconds since the figure opened;
# a matplotlib timer moves it forward while something is moving.
class _Animator:
    def __init__(self, rt: Runtime, redraw, fig: Figure):
        self.rt = rt
        self.redraw = redraw
        self.now = 0.0
        self.tracks: list[_Track] = []
        self.tour: dict | None = None
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
        self.rt.morphs.clear()

    def go(self, state: int, duration: float, ease: str, start: float | None = None):
        start = self.now if start is None else start
        for i, attr, target in self.rt.targets(state):
            begin = self.rt.value(i, attr)
            if duration > 0 and self.rt.kind(i) == "text" and attr == "value" and begin != target:
                self.rt.morphs[i] = (begin, 0.0)
                self.morph_start, self.morph_end = start, start + duration
            if duration > 0 and _blendable(begin, target):
                self.tracks.append(_Track(i, attr, begin, target, start, duration, ease))
            else:
                self.rt.write(i, attr, target)
        self.redraw()
        self.wake()

    def play(self, tour: dict):
        self.cancel()
        if tour["start"] is not None:
            for i, attr, target in self.rt.targets(tour["start"]):
                self.rt.write(i, attr, target)
        self.tour = tour
        self.step = 0
        self.step_start = self.now
        self.begin_step()
        self.redraw()
        self.wake()

    def begin_step(self):
        assert self.tour is not None
        step = self.tour["steps"][self.step]
        if step[0] == "to":
            _, state, duration, ease = step
            self.go(state, duration, ease, start=self.step_start)

    def tick(self, seconds: float):
        self.now += seconds
        while self.tour is not None:
            step = self.tour["steps"][self.step]
            end = self.step_start + step[1 if step[0] == "wait" else 2]
            if self.now < end:
                break
            self.update(end)
            self.step += 1
            self.step_start = end
            if self.step == len(self.tour["steps"]):
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
            self.rt.write(track.obj, track.attr, track.target if t >= 1 else value)
            if t >= 1:
                self.tracks.remove(track)
        if self.rt.morphs:
            span = max(self.morph_end - self.morph_start, 1e-12)
            t = min(1.0, (now - self.morph_start) / span)
            self.rt.morphs = {k: (old, t) for k, (old, _) in self.rt.morphs.items()}
            if t >= 1:
                self.rt.morphs.clear()

    def wake(self):
        self.last = time.monotonic()
        self.timer.start()

    def frame(self):
        now = time.monotonic()
        self.tick(now - self.last)
        self.last = now
        if not self.tracks and self.tour is None and not self.rt.morphs:
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
        # the way an SVG transform does. A text in the middle of changing is drawn twice: the old
        # one fading out, the new one in. That is the best matplotlib can do for morphing.
        shape = rt.shape(i)
        old, progress = rt.morphs.get(i, (None, 1.0))
        shown = [(rt.value(i, "value"), progress)]
        if old is not None:
            shown.append((old, 1 - progress))
        for value, fade in shown:
            glyphs = TextPath((0, 0), value, size=rt.value(i, "font-size"))
            text = PathPatch(
                glyphs,
                facecolor=_paint(rt, i, "fill", fade),
                edgecolor=_paint(rt, i, "stroke", fade),
                transform=_affine(shape) + to_view,
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
        return Rectangle((0, 0), v("width"), v("height"))
    if kind == "ellipse":
        return MplEllipse((0, 0), 2 * v("rx"), 2 * v("ry"))
    if kind == "line":
        return PathPatch(Path([(v("x1"), v("y1")), (v("x2"), v("y2"))]))
    return Polygon([v("a"), v("b"), v("c")], closed=True)


def _affine(matrix: Matrix) -> Affine2D:
    (a, b, c), (d, e, f), _ = matrix.rows
    return Affine2D.from_values(a, d, b, e, c, f)


# How much a matrix scales lengths; for a stretch that differs by direction, an average.
def _scale(matrix: Matrix) -> float:
    (a, b, _), (d, e, _), _ = matrix.rows
    return math.sqrt(abs(a * e - b * d))


def _paint(rt: Runtime, i: int, attr: str, fade: float = 1.0):
    color = rt.value(i, attr)
    if color == "none":
        return "none"
    r, g, b, a = to_rgba(color)
    return r, g, b, a * rt.value(i, f"{attr}-opacity") * rt.opacity(i) * fade
