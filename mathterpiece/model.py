from collections.abc import Iterator
from dataclasses import Field, dataclass, field, fields
from typing import Any, Protocol, runtime_checkable

from mathterpiece.matrix import IDENTITY, Matrix
from mathterpiece.nodes import Node


@dataclass(frozen=True, slots=True)
class Free[T]:
    value: T


@dataclass(frozen=True, slots=True)
class Bound:
    expr: Node


# A style attribute of an object inside a motif, left unset so it comes from the motif.
@dataclass(frozen=True, slots=True)
class Inherit:
    pass


type Attr[T] = Free[T] | Bound | Inherit


# How deep function calls may nest, in the compiler and while drawing, like Python's limit.
RECURSION_LIMIT = 1000
# Each call nests a few dozen Python frames in the compiler and evaluator, so Python's own
# limit has to be well above ours.
PYTHON_FRAMES = 60 * RECURSION_LIMIT


# A user function: its parameters with their defaults (None for one that takes an object), and
# its body, with consts written in and calls naming functions by their key in Model.functions.
@dataclass(frozen=True)
class Function:
    params: tuple[tuple[str, object], ...]
    body: Node


def _members():
    return field(default_factory=list, metadata={"variadic": True})


@dataclass(kw_only=True)
class Obj:
    name: str | None


@dataclass(kw_only=True)
class Real(Obj):
    value: Attr[float] = Free(0.0)


@dataclass(kw_only=True)
class Bool(Obj):
    value: Attr[bool] = Free(False)


# What fill and stroke take: a color, or a string that names one (checked when it is known).
class Paint(str):
    pass


# A type token: family, style and weight are published so a web page may restyle them; size is
# in scene units, so it stays the figure's.
@dataclass(kw_only=True)
class Font(Obj):
    family: Attr[str] = Free("")
    style: Attr[str] = Free("normal")
    weight: Attr[float] = Free(400.0)
    size: Attr[float] = Free(1.0)


# A color token: a reactive color with a default, which a web page may restyle.
@dataclass(kw_only=True)
class Color(Obj):
    value: Attr[Paint] = Free(Paint("#000000ff"))


# A let binding whose value is only known when drawing. It is computed once and every use reads
# it. self in its expression is the owner; names resolve in the owner's motif body if inside is
# set (the let sits directly in that body), and around the owner otherwise.
@dataclass(kw_only=True)
class Local(Obj):
    value: Attr[object] = Free(None)
    type: str = field(default="real", metadata={"internal": True})
    owner: Obj | None = field(default=None, metadata={"internal": True})
    inside: bool = field(default=False, metadata={"internal": True})


@dataclass(kw_only=True)
class Visual(Obj):
    # Applied around the object's own x and y (which stay in the parent's coordinates), to its
    # shape and to its members, as in Unity or Godot.
    transform: Attr[Matrix] = Free(IDENTITY)


@dataclass(kw_only=True)
class Styled(Visual):
    x: Attr[float] = Free(0.0)
    y: Attr[float] = Free(0.0)
    fill: Attr[Paint] = Free(Paint("#000000ff"))
    stroke: Attr[Paint] = Free(Paint("none"))
    stroke_width: Attr[float] = Free(1.0)
    opacity: Attr[float] = Free(1.0)
    fill_opacity: Attr[float] = Free(1.0)
    stroke_opacity: Attr[float] = Free(1.0)


@dataclass(kw_only=True)
class Circle(Styled):
    r: Attr[float] = Free(1.0)


# Shapes store SVG's attributes, with x and y where SVG has cx and cy. Line and triangle points
# are measured from x and y, which default to 0, so by default they match SVG.
@dataclass(kw_only=True)
class Rect(Styled):
    width: Attr[float] = Free(1.0)
    height: Attr[float] = Free(1.0)
    # Rounded corners, as in SVG: every corner's radius across and up; ry copies rx unless given.
    rx: Attr[float] = Free(0.0)
    ry: Attr[float] = Free(0.0)


@dataclass(kw_only=True)
class Ellipse(Styled):
    rx: Attr[float] = Free(1.0)
    ry: Attr[float] = Free(1.0)


@dataclass(kw_only=True)
class Line(Styled):
    x1: Attr[float] = Free(0.0)
    y1: Attr[float] = Free(0.0)
    x2: Attr[float] = Free(1.0)
    y2: Attr[float] = Free(0.0)


@dataclass(kw_only=True)
class Triangle(Styled):
    a: Attr[tuple[float, float]] = Free((0.0, 0.0))
    b: Attr[tuple[float, float]] = Free((1.0, 0.0))
    c: Attr[tuple[float, float]] = Free((0.0, 1.0))


@dataclass(kw_only=True)
class Text(Styled):
    value: Attr[str] = Free("")
    # In scene units, like r. Text starts at (x, y) on its baseline, as in SVG.
    font_size: Attr[float] = Free(1.0)
    # As in CSS; an empty family means the page's.
    font_family: Attr[str] = Free("")
    font_style: Attr[str] = Free("normal")
    font_weight: Attr[float] = Free(400.0)
    # Where (x, y) sits on the text: its start, middle or end, and its top, middle or bottom
    # (the baseline).
    halign: Attr[str] = Free("start")
    valign: Attr[str] = Free("bottom")


@dataclass(kw_only=True)
class Group(Visual):
    members: list[Visual] = _members()


# The (scene ...) form: the one root of the visual tree.
@dataclass(kw_only=True)
class Root(Group):
    # The color of the plane every object sits on; views show it wherever there is nothing else.
    background: Attr[Paint] = Free(Paint("none"))


@dataclass(kw_only=True)
class Motif(Styled):
    kind: str = field(default="", metadata={"internal": True})
    params: dict[str, Attr[object]] = field(default_factory=dict, metadata={"internal": True})
    param_types: dict[str, str] = field(default_factory=dict, metadata={"internal": True})
    members: list[Visual] = _members()


@dataclass(kw_only=True)
class View(Obj):
    pass


# Shows a string from the scene in the page, inline in prose, as the scene changes.
@dataclass(kw_only=True)
class Readout(View):
    value: Attr[str] = Free("")
    # From a font token; size is the paragraph's, since scene units mean nothing in prose.
    font_family: Attr[str] = Free("")
    font_style: Attr[str] = Free("normal")
    font_weight: Attr[float] = Free(400.0)


@dataclass(kw_only=True)
class Canvas(View):
    # SVG viewBox, except that y points up, so view-y is the bottom edge.
    view_x: Attr[float] = Free(-10.0)
    view_y: Attr[float] = Free(-10.0)
    view_width: Attr[float] = Free(20.0)
    view_height: Attr[float] = Free(20.0)
    # Maps scene coordinates to view coordinates, with the view center as the origin.
    transform: Attr[Matrix] = Free(IDENTITY)
    members: list[Visual] = _members()
    # For each member, the condition under which it is shown (None: always), and the transition it
    # is shown and hidden with (None: at once).
    conditions: list[Node | None] = field(default_factory=list, metadata={"internal": True})
    transitions: list[Any] = field(default_factory=list, metadata={"internal": True})


# A flag on the scene: active whenever all its conditions hold. Nothing goes to a state.
@dataclass(kw_only=True)
class State(Obj):
    conditions: tuple[Node, ...] = field(default=(), metadata={"internal": True})


@dataclass(kw_only=True)
class Control(Obj):
    label: Attr[str] = Free("")


# Scrubs an animation by hand: the knob's place on the track is the animation's progress, and
# durations only share out the track. step snaps the knob to that many evenly spaced places.
@dataclass(kw_only=True)
class Slider(Control):
    animation: Obj | None = field(default=None, metadata={"internal": True})
    step: Attr[object] = Free(None)


# Sets off an animation when pressed.
@dataclass(kw_only=True)
class Button(Control):
    animation: Obj | None = field(default=None, metadata={"internal": True})


# Switches a true/false value: a scene bool, or (target None) its own value, which lives outside
# the scene, where only views and controls read it. Unlike sliders and buttons it takes no
# animation: the new value is always the flipped one, and a bool has no path, so no part of a
# transition would be used. A fade when the value changes belongs to the canvas that reads it.
@dataclass(kw_only=True)
class Toggle(Control):
    target: Obj | None = field(default=None, metadata={"internal": True})
    attr: str = field(default="value", metadata={"internal": True})
    value: Attr[bool] = Free(False)


# Plays and pauses an animation. With buttons, it also shows one button per step of the
# animation's top-level in-order.
@dataclass(kw_only=True)
class Play(Control):
    animation: Obj | None = field(default=None, metadata={"internal": True})
    buttons: Attr[bool] = Free(False)


# Moves node's target (part of its position) with the pointer while it is dragged, if every
# condition holds where the node would land; when (a condition or a state) attaches the listener
# only while it holds. Unlike sliders and buttons it takes no animation: the pointer decides the
# value, at once, so no part of a transition would be used. A drag along a fixed range is a
# slider.
@dataclass(kw_only=True)
class Drag(Obj):
    node: Obj | None = field(default=None, metadata={"internal": True})
    # What the drag writes: the node's x, y or pos (both), or a number the node's position depends
    # on, which the runtime sets so the node comes as close to the pointer as it can.
    target_obj: Obj | None = field(default=None, metadata={"internal": True})
    target: str = field(default="pos", metadata={"internal": True})
    kind: str = field(default="list2", metadata={"internal": True})
    conditions: tuple[Node, ...] = field(default=(), metadata={"internal": True})
    when: "Node | State | None" = field(default=None, metadata={"internal": True})


# An animation's body: one target (or every member of a group, for a group attribute) paired
# with one transition; or animations composed at once or in order; or a pause in a sequence.
# kind is how the targets' values move by default: number, point, color, text or bool.
@dataclass(frozen=True)
class Pair:
    targets: tuple[tuple[Obj, str], ...]
    kind: str
    transition: Any


@dataclass(frozen=True)
class AtOnce:
    parts: tuple[Any, ...]
    ease: Any = None
    default_duration: float | None = None
    default_ease: Any = None


@dataclass(frozen=True)
class InOrder:
    parts: tuple[Any, ...]
    ease: Any = None
    default_duration: float | None = None
    default_ease: Any = None


@dataclass(frozen=True)
class WaitStep:
    duration: float


@dataclass(kw_only=True)
class Animation(Obj):
    body: Any = field(default=None, metadata={"internal": True})


# Sets off an animation when node is clicked: pressed and released on the same shape. when (a
# condition or a state) attaches the listener only while it holds.
@dataclass(kw_only=True)
class Click(Obj):
    node: Obj | None = field(default=None, metadata={"internal": True})
    animation: Obj | None = field(default=None, metadata={"internal": True})
    when: "Node | State | None" = field(default=None, metadata={"internal": True})


@runtime_checkable
class Container(Protocol):
    name: str | None
    members: list[Visual]


# Keys are DSL names, which use hyphens where the Python field names use underscores.
def attributes(cls: type[Obj]) -> dict[str, Field]:
    return {
        f.name.replace("_", "-"): f
        for f in fields(cls)
        if f.name != "name" and not f.metadata.get("internal")
    }


def variadic(cls: type[Obj]) -> Field | None:
    return next((f for f in fields(cls) if f.metadata.get("variadic")), None)


# Names that a motif's body can use for its members: those inside groups count, but not those
# inside a nested motif, which has its own.
def local_names(motif: Motif) -> dict[str, Obj]:
    names: dict[str, Obj] = {}
    stack: list[Obj] = list(reversed(motif.members))
    while stack:
        obj = stack.pop()
        if obj.name is not None:
            names[obj.name] = obj
        if isinstance(obj, Group):
            stack.extend(reversed(obj.members))
    return names


class DuplicateNameError(ValueError):
    pass


class TreeError(ValueError):
    pass


def _label(obj: Obj) -> str:
    return repr(obj.name) if obj.name is not None else "an anonymous object"


class Model:
    def __init__(self):
        self._items: list[Obj] = []
        self._index: dict[str, Obj] = {}
        self._tree: set[int] = set()
        self.functions: dict[str, Function] = {}

    # Each object has one parent. A view is not a parent: it shows objects already in the tree.
    def add(self, obj: Obj):
        new: dict[str, Obj] = {}
        seen: set[int] = set()
        # The flag says whether the name is global; names inside a motif are local to it.
        stack: list[tuple[Obj, bool]] = [(obj, True)]
        while stack:
            thing, is_global = stack.pop()
            if id(thing) in self._tree or id(thing) in seen:
                raise TreeError(f"{_label(thing)} already belongs to the model")
            seen.add(id(thing))
            if thing.name is not None and is_global:
                if thing.name in self._index or thing.name in new:
                    raise DuplicateNameError(f"name {thing.name!r} is already defined")
                new[thing.name] = thing
            if isinstance(thing, Container) and not isinstance(thing, View):
                inner = is_global and not isinstance(thing, Motif)
                stack.extend((m, inner) for m in reversed(thing.members))
        if isinstance(obj, Container) and isinstance(obj, View):
            for member in obj.members:
                if id(member) not in self._tree:
                    raise TreeError(f"{_label(member)} is shown but not in the model")
        self._index.update(new)
        self._tree |= seen
        self._items.append(obj)

    def alias(self, name: str, target: str):
        if name in self._index:
            raise DuplicateNameError(f"name {name!r} is already defined")
        self._index[name] = self._index[target]

    def __getitem__(self, name: str) -> Obj:
        return self._index[name]

    def __contains__(self, name: str) -> bool:
        return name in self._index

    def __iter__(self) -> Iterator[Obj]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @property
    def root(self) -> Root | None:
        return next((obj for obj in self._items if isinstance(obj, Root)), None)

    @property
    def states(self) -> list[State]:
        return [obj for obj in self._items if isinstance(obj, State)]

    @property
    def controls(self) -> list[Control]:
        return [obj for obj in self._items if isinstance(obj, Control)]

    @property
    def listeners(self) -> list[Drag]:
        return [obj for obj in self._items if isinstance(obj, Drag)]

    @property
    def views(self) -> list[View]:
        return [obj for obj in self._items if isinstance(obj, View)]

    @property
    def objects(self) -> list[Obj]:
        return [obj for obj in self._items if not isinstance(obj, View)]
