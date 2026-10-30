from collections.abc import Iterator
from dataclasses import Field, dataclass, field, fields
from typing import Protocol, runtime_checkable

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


# A condition on the scene: active whenever all its conditions hold. moves says how to reach it:
# each free value (object, attribute) and the expression it moves to. problem says why it cannot
# be animated to, if it cannot.
@dataclass(kw_only=True)
class State(Obj):
    conditions: tuple[Node, ...] = field(default=(), metadata={"internal": True})
    moves: tuple[tuple[Obj, str, Node], ...] = field(default=(), metadata={"internal": True})
    problem: str | None = field(default=None, metadata={"internal": True})


@dataclass(kw_only=True)
class Control(Obj):
    label: Attr[str] = Free("")


# Writes one free value while dragged: an attribute, a motif parameter, or a real's value. kind is
# that value's type, which the slider adapts to.
@dataclass(kw_only=True)
class Slider(Control):
    target: Obj | None = field(default=None, metadata={"internal": True})
    attr: str = field(default="value", metadata={"internal": True})
    kind: str = field(default="real", metadata={"internal": True})
    min: Attr[float] = Free(0.0)
    max: Attr[float] = Free(1.0)
    # None means continuous.
    step: Attr[object] = Free(None)


# Goes to its state when pressed, over duration seconds (0 is instant).
@dataclass(kw_only=True)
class Button(Control):
    state: State | None = field(default=None, metadata={"internal": True})
    duration: Attr[float] = Free(0.0)
    ease: Attr[str] = Free("linear")


# One button per state, in order.
@dataclass(kw_only=True)
class Steps(Control):
    states: list[State] = field(default_factory=list, metadata={"internal": True})
    duration: Attr[float] = Free(0.0)
    ease: Attr[str] = Free("linear")


# One step of a tour: wait for duration seconds, or go to state over duration seconds.
@dataclass(frozen=True)
class TourStep:
    kind: str
    state: State | None
    duration: Free[float]
    ease: Free[str] = Free("linear")


# A guided tour: jumps to start (if any) when pressed, then runs its steps in order.
@dataclass(kw_only=True)
class Play(Control):
    start: State | None = field(default=None, metadata={"internal": True})
    steps: tuple[TourStep, ...] = field(default=(), metadata={"internal": True})


# Moves node's target (part of its position) with the pointer while it is dragged, if every
# condition holds where the node would land; when (a condition or a state) attaches the listener
# only while it holds.
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
