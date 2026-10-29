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


type Attr[T] = Free[T] | Bound


def _members():
    return field(default_factory=list, metadata={"variadic": True})


@dataclass(kw_only=True)
class Obj:
    name: str | None


@dataclass(kw_only=True)
class Real(Obj):
    value: Attr[float] = Free(0.0)


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
    return {f.name.replace("_", "-"): f for f in fields(cls) if f.name != "name"}


def variadic(cls: type[Obj]) -> Field | None:
    return next((f for f in fields(cls) if f.metadata.get("variadic")), None)


class DuplicateNameError(ValueError):
    pass


class Scene:
    def __init__(self):
        self._items: list[Obj] = []
        self._index: dict[str, Obj] = {}

    def add(self, obj: Obj):
        if obj.name is not None and obj.name in self._index:
            raise DuplicateNameError(f"name {obj.name!r} is already defined")
        new: dict[str, Obj] = {}
        stack: list[Obj] = [obj]
        while stack:
            thing = stack.pop()
            if thing.name is not None:
                known = self._index.get(thing.name, new.get(thing.name))
                if known is thing:
                    continue
                if known is not None:
                    raise DuplicateNameError(f"name {thing.name!r} is already defined")
                new[thing.name] = thing
            if isinstance(thing, Container):
                stack.extend(reversed(thing.members))
        self._index.update(new)
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
    def views(self) -> list[View]:
        return [obj for obj in self._items if isinstance(obj, View)]

    @property
    def objects(self) -> list[Obj]:
        return [obj for obj in self._items if not isinstance(obj, View)]
