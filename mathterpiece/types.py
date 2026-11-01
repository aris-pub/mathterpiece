"""Types as objects, and the one rule for what fits where (docs/type-system.md)."""

from dataclasses import dataclass

from mathterpiece.colors import parse_color
from mathterpiece.nodes import (
    Bar,
    Brackets,
    ComplexLit,
    Form,
    IntLit,
    ListLit,
    Name,
    Node,
    NoneLit,
    RatioLit,
    RealLit,
    StrLit,
)


class TypeError_(Exception):
    pass


@dataclass(frozen=True)
class Prim:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class ListT:
    item: "Type"

    def __str__(self) -> str:
        return f"list[{self.item}]"


@dataclass(frozen=True)
class FuncT:
    params: tuple["Type", ...]
    result: "Type"

    def __str__(self) -> str:
        return f"func[{' '.join(map(str, (*self.params, self.result)))}]"


@dataclass(frozen=True)
class Maybe:
    inner: "Type"

    def __str__(self) -> str:
        return f"{self.inner}|none"


@dataclass(frozen=True)
class ShapeT:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Interface:
    name: str
    of: "Type | None" = None

    def __str__(self) -> str:
        return self.name if self.of is None else f"{self.name}[{self.of}]"


Type = Prim | ListT | FuncT | Maybe | ShapeT | Interface

INT, RATIO, REAL, COMPLEX = Prim("int"), Prim("ratio"), Prim("real"), Prim("complex")
BOOL, STRING, COLOR, FONT = Prim("bool"), Prim("string"), Prim("color"), Prim("font")
POINT, TRANSFORM = Prim("point"), Prim("transform")
TRANSITION, ANIMATION = Prim("transition"), Prim("animation")
NONE, SCENE = Prim("none"), Prim("scene")

PRIMS = {
    t.name: t
    for t in (
        INT,
        RATIO,
        REAL,
        COMPLEX,
        BOOL,
        STRING,
        COLOR,
        FONT,
        POINT,
        TRANSFORM,
        TRANSITION,
        ANIMATION,
        NONE,
        SCENE,
    )
}
SHAPES = ("circle", "rect", "ellipse", "line", "triangle", "text", "group")
INTERFACES = ("shape", "positioned", "sequence")
# Each number type is accepted wherever a later one is expected (type-system.md, section 3).
NUMBERS = (INT, RATIO, REAL, COMPLEX)


def fits(actual: Type, expected: Type) -> bool:
    """Whether an object of type actual is accepted where expected is."""
    if actual == expected:
        return True
    if actual in NUMBERS and expected in NUMBERS:
        return NUMBERS.index(actual) <= NUMBERS.index(expected)
    if isinstance(expected, Maybe):
        inner = actual.inner if isinstance(actual, Maybe) else actual
        return actual == NONE or fits(inner, expected.inner)
    if isinstance(actual, ListT) and isinstance(expected, ListT):
        # A list never changes, so a list of narrower items is a list of wider ones.
        return fits(actual.item, expected.item)
    if isinstance(actual, FuncT) and isinstance(expected, FuncT):
        return (
            len(actual.params) == len(expected.params)
            and all(fits(e, a) for a, e in zip(actual.params, expected.params, strict=True))
            and fits(actual.result, expected.result)
        )
    if isinstance(expected, Interface):
        return _satisfies(actual, expected)
    return False


def _satisfies(actual: Type, interface: Interface) -> bool:
    if interface.name == "shape":
        return isinstance(actual, ShapeT)
    if interface.name == "positioned":
        return actual == POINT or (isinstance(actual, ShapeT) and actual.name != "group")
    if interface.name == "sequence":
        item = interface.of
        if isinstance(actual, ListT):
            return item is None or fits(actual.item, item)
        if actual == POINT:
            return item is None or fits(REAL, item)
        # A group's member types are not known from its type alone; the compiler checks them.
        return isinstance(actual, ShapeT) and actual.name == "group"
    return False


def literal_type(node: Node, expected: Type | None) -> Type:
    """The type a literal takes in a place that expects expected (None: a place with no type)."""
    if isinstance(expected, Maybe):
        if isinstance(node, NoneLit):
            return expected
        return Maybe(literal_type(node, expected.inner))
    if isinstance(node, NoneLit):
        raise TypeError_(
            f"none is not a {expected}" if expected else "none needs a place that allows it"
        )
    own = _own_type(node, expected)
    if expected is not None and not fits(own, expected):
        raise TypeError_(f"expected {expected}, got {own}")
    return expected if expected is not None else own


def _own_type(node: Node, expected: Type | None) -> Type:
    if isinstance(node, IntLit):
        return INT
    if isinstance(node, RatioLit):
        return RATIO
    if isinstance(node, RealLit):
        return REAL
    if isinstance(node, ComplexLit):
        return COMPLEX
    if isinstance(node, StrLit):
        if expected == COLOR:
            if parse_color(node.value) is None:
                raise TypeError_(f"{node.value!r} is not a color")
            return COLOR
        return STRING
    if isinstance(node, ListLit):
        if expected == POINT:
            if len(node.items) != 2 or not all(fits(_own_type(i, REAL), REAL) for i in node.items):
                raise TypeError_("a point is two numbers, [x y]")
            return POINT
        item = expected.item if isinstance(expected, ListT) else None
        if not node.items:
            if item is None:
                raise TypeError_("an empty list needs its type: write list[T]")
            return ListT(item)
        return ListT(_common([literal_type(i, item) for i in node.items]))
    raise TypeError_(f"{type(node).__name__} is not a literal")


def _common(types: list[Type]) -> Type:
    """The narrowest type every item fits: the broadest number among numbers."""
    best = types[0]
    for t in types[1:]:
        if fits(t, best):
            continue
        if fits(best, t):
            best = t
        else:
            raise TypeError_(f"a list holds one type, but has {best} and {t}")
    return best


def type_from_node(node: Node) -> Type:
    """The type a piece of type notation names (type-system.md, section 5.a)."""
    if isinstance(node, Bar):
        *types, last = node.items
        if len(types) != 1 or not isinstance(last, NoneLit):
            raise TypeError_("a type can be broadened only by none for now: write T|none")
        return Maybe(type_from_node(types[0]))
    if isinstance(node, Form):
        head = node.items[0]
        if isinstance(head, Name) and head.parts == ("maybe",):
            if len(node.items) != 2:
                raise TypeError_("maybe takes one type")
            return Maybe(type_from_node(node.items[1]))
        raise TypeError_("narrowed types are not read yet")
    if isinstance(node, NoneLit):
        return NONE
    if not isinstance(node, Name) or not isinstance(node.parts[0], str):
        raise TypeError_("expected a type")
    name, *args = node.parts
    if len(args) > 1:
        raise TypeError_(f"{name} takes its types in one pair of brackets")
    inner = args[0] if args else None
    items = inner.items if isinstance(inner, Brackets) else (() if inner is None else (inner,))
    if name in ("list", "sequence"):
        if not items:
            if name == "sequence":
                return Interface("sequence")
            raise TypeError_("list needs its item type: write list[T]")
        if len(items) != 1:
            raise TypeError_(f"{name} takes one item type")
        item = type_from_node(items[0])
        return ListT(item) if name == "list" else Interface("sequence", item)
    if name == "func":
        if not items:
            raise TypeError_("func needs at least its result type: write func[R]")
        *params, result = (type_from_node(i) for i in items)
        return FuncT(tuple(params), result)
    if items:
        raise TypeError_(f"{name} takes no item type")
    if name in PRIMS:
        return PRIMS[name]
    if name in SHAPES:
        return ShapeT(name)
    if name in INTERFACES:
        return Interface(name)
    raise TypeError_(f"unknown type {name!r}")
