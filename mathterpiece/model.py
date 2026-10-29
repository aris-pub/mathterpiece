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


def _members():
    return field(default_factory=list, metadata={"variadic": True})


@dataclass(kw_only=True)
class Obj:
    name: str | None


@dataclass(kw_only=True)
class Real(Obj):
    value: Attr[float] = Free(0.0)


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
    pass


@dataclass(kw_only=True)
class Styled(Visual):
    x: Attr[float] = Free(0.0)
    y: Attr[float] = Free(0.0)
    fill: Attr[str] = Free("black")
    stroke: Attr[str] = Free("none")
    stroke_width: Attr[float] = Free(1.0)
    opacity: Attr[float] = Free(1.0)
    fill_opacity: Attr[float] = Free(1.0)
    stroke_opacity: Attr[float] = Free(1.0)


@dataclass(kw_only=True)
class Circle(Styled):
    r: Attr[float] = Free(1.0)


@dataclass(kw_only=True)
class Text(Styled):
    value: Attr[str] = Free("")


@dataclass(kw_only=True)
class Group(Visual):
    members: list[Visual] = _members()


# The (scene ...) form: the one root of the visual tree.
@dataclass(kw_only=True)
class Root(Group):
    pass


@dataclass(kw_only=True)
class Motif(Styled):
    kind: str = field(default="", metadata={"internal": True})
    params: dict[str, Attr[object]] = field(default_factory=dict, metadata={"internal": True})
    members: list[Visual] = _members()


@dataclass(kw_only=True)
class View(Obj):
    pass


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
    def views(self) -> list[View]:
        return [obj for obj in self._items if isinstance(obj, View)]

    @property
    def objects(self) -> list[Obj]:
        return [obj for obj in self._items if not isinstance(obj, View)]
