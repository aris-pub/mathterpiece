"""The world model the compiler builds: objects, their places, and typed expressions
(docs/data-model.md; docs/mtpc.md describes how it is written out)."""

from dataclasses import dataclass, field
from typing import Any

from mathterpiece.nodes import NOPOS, Form, Node, Pos
from mathterpiece.types import Type

# What a place or an expression reads: (object id, attribute), with None for a variable.
Dep = tuple[int, str | None]
# A number's range, (low, high), both ends included; None when not a number.
Range = tuple[float, float] | None


@dataclass(frozen=True)
class Expr:
    """A typed expression. known holds its value when it is known when compiling; then the
    expression is never written out, only the value."""

    op: str
    type: Type
    args: tuple = ()
    deps: frozenset[Dep] = frozenset()
    range: Range = None
    known: bool = False
    value: Any = None


@dataclass
class Place:
    """A variable's value or an object's attribute: free (it holds value) or bound (it always
    equals expr, and is recomputed when anything in deps changes)."""

    type: Type
    value: object = None
    expr: Expr | None = None
    # Set by a variant's body: no instance and no writer may change it.
    fixed: bool = False

    @property
    def bound(self) -> bool:
        return self.expr is not None

    @property
    def deps(self) -> frozenset[Dep]:
        return self.expr.deps if self.expr else frozenset()


@dataclass
class Obj:
    kind: str
    name: str | None
    type: Type
    access: str = "scene"
    attrs: dict[str, Place] = field(default_factory=dict)
    members: list[int] = field(default_factory=list)
    parent: int | None = None
    pos: Pos = NOPOS
    # The motif or variant an instance is of.
    of: str | None = None
    # What its kind needs besides attributes: an animation's steps, a writer's animation and
    # conditions, a transition's ends before they are typed.
    data: dict = field(default_factory=dict)

    @property
    def value(self) -> Place:
        """A variable's one place."""
        return self.attrs["value"]


@dataclass(frozen=True)
class Param:
    """A parameter: its default is the source it is compiled from, in each instance or call,
    and value is that default's value, which is always known when compiling."""

    name: str
    type: Type
    default: Node | None = None
    value: object = None


@dataclass(frozen=True)
class MotifDef:
    name: str
    params: tuple[Param, ...]
    body: tuple[Node, ...]
    pos: Pos = NOPOS


@dataclass
class FuncDef:
    """A function: declared with func (with a name) or written in place with fn. deps are the
    places its body reads besides its parameters."""

    name: str | None
    params: tuple[Param, ...]
    result: Type
    body: Expr | None = None
    deps: frozenset[Dep] = frozenset()
    pos: Pos = NOPOS
    # What the body reads through each parameter that holds shapes: attribute names, with
    # "[]." before one read on each item of a collection ("[].r").
    reads: dict[str, frozenset[str]] = field(default_factory=dict)
    # Its body's source and the names around it, so a call with known arguments can be folded
    # by compiling the body again with them.
    source: Node | None = None
    scope: dict = field(default_factory=dict)


@dataclass(frozen=True)
class VariantDef:
    name: str
    params: tuple[Param, ...]
    base: str
    body: Form
    # The attributes its body sets, x and y for pos.
    fixed: frozenset[str]
    pos: Pos = NOPOS


@dataclass
class Model:
    objects: list[Obj] = field(default_factory=list)
    names: dict[str, int] = field(default_factory=dict)
    types: dict[str, Type] = field(default_factory=dict)
    motifs: dict[str, MotifDef] = field(default_factory=dict)
    variants: dict[str, VariantDef] = field(default_factory=dict)
    functions: list[FuncDef] = field(default_factory=list)
    funcs: dict[str, int] = field(default_factory=dict)

    def id(self, name: str) -> int:
        return self.names[name]

    def get(self, name: str) -> Obj:
        return self.objects[self.names[name]]
