from collections.abc import Iterator
from dataclasses import Field, dataclass, field, fields
from typing import Protocol, runtime_checkable

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
    name: str


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
    facecolor: Attr[str] = Free("black")
    fill: Attr[bool] = Free(True)
    edgecolor: Attr[str] = Free("black")
    linewidth: Attr[float] = Free(1.0)
    alpha: Attr[float] = Free(1.0)


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
    xmin: Attr[float] = Free(-10.0)
    xmax: Attr[float] = Free(10.0)
    ymin: Attr[float] = Free(-10.0)
    ymax: Attr[float] = Free(10.0)
    members: list[Visual] = _members()


@runtime_checkable
class Container(Protocol):
    name: str
    members: list[Visual]


def attributes(cls: type[Obj]) -> dict[str, Field]:
    return {f.name: f for f in fields(cls) if f.name != "name"}


def variadic(cls: type[Obj]) -> Field | None:
    return next((f for f in fields(cls) if f.metadata.get("variadic")), None)


class DuplicateNameError(ValueError):
    pass


class Scene:
    def __init__(self):
        self._items: list[Obj] = []
        self._index: dict[str, Obj] = {}

    def add(self, obj: Obj):
        if obj.name in self._index:
            raise DuplicateNameError(f"name {obj.name!r} is already defined")
        new: dict[str, Obj] = {}
        stack: list[Obj] = [obj]
        while stack:
            thing = stack.pop()
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
