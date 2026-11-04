"""Types as objects, and the one rule for what fits where (docs/type-system.md)."""

from collections.abc import Mapping
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
    # The shape type a variant refines.
    base: "ShapeT | None" = None

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Interface:
    name: str
    of: "Type | None" = None

    def __str__(self) -> str:
        return self.name if self.of is None else f"{self.name}[{self.of}]"


@dataclass(frozen=True)
class NamespaceT:
    """The type of a namespace (mtp-4rc): a mutable object that is not drawn, whose members are
    read and written as attributes are."""

    name: str

    def __str__(self) -> str:
        return f"namespace {self.name}"


@dataclass(frozen=True)
class ComponentT:
    """The type of a component: slider, toggle, canvas, …."""

    name: str

    def __str__(self) -> str:
        return self.name


# A constraint: (">=", 0), ("length", 3), ("one-of", ("a", "b")) or ("const",).
Constraint = tuple


@dataclass(frozen=True)
class Refine:
    """A type narrowed by constraints (type-system.md, section 5.b); base is never a Refine."""

    base: "Type"
    constraints: tuple[Constraint, ...]
    name: str | None = None

    def __str__(self) -> str:
        if self.name:
            return self.name
        return f"({self.base} {' '.join(_show(c) for c in self.constraints)})"


def _show(c: Constraint) -> str:
    if c[0] == "one-of":
        return "(one-of " + " ".join(f"'{v}'" for v in c[1]) + ")"
    return "(" + " ".join(str(p) for p in c) + ")"


Type = Prim | ListT | FuncT | Maybe | ShapeT | Interface | Refine | ComponentT | NamespaceT

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
SHAPES = (
    "circle", "rect", "ellipse", "line", "triangle", "polyline", "polygon", "arc", "ring", "text",
    "group",
)  # fmt: skip
INTERFACES = ("shape", "positioned", "sequence")
# Each number type is accepted wherever a later one is expected (type-system.md, section 3).
NUMBERS = (INT, RATIO, REAL, COMPLEX)


def fits(actual: Type, expected: Type) -> bool:
    """Whether an object of type actual is accepted where expected is."""
    if actual == expected:
        return True
    if isinstance(expected, Maybe):
        inner = actual.inner if isinstance(actual, Maybe) else actual
        return actual == NONE or fits(inner, expected.inner)
    if isinstance(actual, Maybe):
        return False
    if isinstance(actual, ShapeT) and isinstance(expected, ShapeT):
        return actual.base is not None and fits(actual.base, expected)
    if isinstance(actual, Refine) or isinstance(expected, Refine):
        return _fits_refined(actual, expected)
    if actual in NUMBERS and expected in NUMBERS:
        return NUMBERS.index(actual) <= NUMBERS.index(expected)
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


COMPARE = {">=", ">", "<=", "<"}


def _narrowing(t: Type) -> tuple[Type, tuple[Constraint, ...]]:
    # const forbids writes but narrows no value, so it never decides what fits.
    if isinstance(t, Refine):
        return t.base, tuple(c for c in t.constraints if c[0] != "const")
    return t, ()


def _fits_refined(actual: Type, expected: Type) -> bool:
    a_base, a_cons = _narrowing(actual)
    e_base, e_cons = _narrowing(expected)
    return fits(a_base, e_base) and all(_implied(a_cons, c) for c in e_cons)


def _implied(have: tuple[Constraint, ...], need: Constraint) -> bool:
    """Whether the constraints have guarantee need."""
    kind = need[0]
    if kind in COMPARE:
        low = kind in (">=", ">")
        for c in have:
            if c[0] not in COMPARE or (c[0] in (">=", ">")) != low:
                continue
            if c[1] == need[1]:
                if c[0] == need[0] or c[0] in (">", "<"):
                    return True
            elif (c[1] > need[1]) if low else (c[1] < need[1]):
                return True
        return False
    if kind == "length":
        return need in have
    if kind == "one-of":
        return any(c[0] == "one-of" and set(c[1]) <= set(need[1]) for c in have)
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
    """The type a literal takes where the type expected is expected (None: nothing is expected)."""
    if isinstance(expected, Maybe):
        if isinstance(node, NoneLit):
            return expected
        return Maybe(literal_type(node, expected.inner))
    if isinstance(node, NoneLit):
        raise TypeError_(
            f"none is not a {expected}" if expected else "none needs an attribute that allows it"
        )
    if isinstance(expected, Refine):
        literal_type(node, expected.base)
        for c in expected.constraints:
            _check(node, c)
        return expected
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


def _check(node: Node, c: Constraint) -> None:
    """Raises if a literal breaks a constraint (a value known when compiling, section 5.b)."""
    kind = c[0]
    if kind in COMPARE:
        assert isinstance(node, (IntLit, RatioLit, RealLit))
        value = node.value
        ok = {">=": value >= c[1], ">": value > c[1], "<=": value <= c[1], "<": value < c[1]}[kind]
        if not ok:
            raise TypeError_(f"{value} breaks {_show(c)}")
    elif kind == "one-of":
        assert isinstance(node, StrLit)
        if node.value not in c[1]:
            choices = ", ".join(f"'{v}'" for v in c[1])
            raise TypeError_(f"'{node.value}' is not one of {choices}")
    elif kind == "length":
        assert isinstance(node, ListLit)
        if len(node.items) != c[1]:
            raise TypeError_(f"the list has {len(node.items)} items, but its length is {c[1]}")


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


def type_from_node(node: "Node | str", named: "Mapping[str, Type] | None" = None) -> Type:
    """The type a piece of type notation names (type-system.md, section 5.a). named holds the
    types declared so far, by name."""
    named = named or {}
    if isinstance(node, Bar):
        *types, last = node.items
        if len(types) != 1 or not isinstance(last, NoneLit):
            raise TypeError_("a type can be broadened only by none for now: write T|none")
        return Maybe(type_from_node(types[0], named))
    if isinstance(node, Form):
        if not node.items:
            raise TypeError_("() is not a type")
        head = node.items[0]
        if isinstance(head, Name) and head.parts == ("maybe",):
            if len(node.items) != 2:
                raise TypeError_("maybe takes one type")
            return Maybe(type_from_node(node.items[1], named))
        return refine(type_from_node(head, named), node.items[1:])
    if isinstance(node, NoneLit):
        return NONE
    if not isinstance(node, Name) or not isinstance(node.parts[0], str):
        raise TypeError_("expected a type")
    name, *args = node.parts
    assert isinstance(name, str)
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
        item = type_from_node(items[0], named)
        return ListT(item) if name == "list" else Interface("sequence", item)
    if name == "func":
        if not items:
            raise TypeError_("func needs at least its result type: write func[R]")
        *params, result = (type_from_node(i, named) for i in items)
        return FuncT(tuple(params), result)
    if items:
        raise TypeError_(f"{name} takes no item type")
    if name in PRIMS:
        return PRIMS[name]
    if name in SHAPES:
        return ShapeT(name)
    if name in INTERFACES:
        return Interface(name)
    if name in named:
        return named[name]
    raise TypeError_(f"unknown type {name!r}")


def refine(base: Type, nodes: "tuple[Node, ...] | list[Node]", name: str | None = None) -> Type:
    """base narrowed by the constraint forms nodes; a Refine of a Refine is flattened. On a type
    that allows none, the constraints narrow its other values: (T (c…))|none."""
    if isinstance(base, Maybe):
        return Maybe(refine(base.inner, nodes, name))
    own: tuple[Constraint, ...] = ()
    if isinstance(base, Refine):
        own, base = base.constraints, base.base
    added = tuple(constraint(n, base) for n in nodes)
    return Refine(base, own + added, name)


def constraint(node: Node, base: Type) -> Constraint:
    """Reads one constraint form and checks it can narrow base."""
    if not isinstance(node, Form) or not node.items or not isinstance(node.items[0], Name):
        raise TypeError_("expected a constraint")
    head = node.items[0].parts[0]
    args = node.items[1:]
    if head in COMPARE:
        if len(args) != 1:
            raise TypeError_("a comparison takes one number: (>= 0)")
        if not isinstance(args[0], (IntLit, RatioLit, RealLit)):
            raise TypeError_("a comparison takes a number")
        if base not in NUMBERS[:3]:
            raise TypeError_(f"only numbers can be compared, not {base}")
        return (head, args[0].value)
    if head == "length":
        if not isinstance(base, ListT):
            raise TypeError_(f"only lists have a length, not {base}")
        if len(args) != 1 or not isinstance(args[0], IntLit) or args[0].value < 0:
            raise TypeError_("length takes one whole number: (length 3)")
        return ("length", args[0].value)
    if head == "one-of":
        if base != STRING:
            raise TypeError_(f"only strings have choices, not {base}")
        if not args:
            raise TypeError_("one-of needs at least one choice")
        if not all(isinstance(a, StrLit) for a in args):
            raise TypeError_("one-of takes strings: (one-of 'left' 'right')")
        return ("one-of", tuple(a.value for a in args if isinstance(a, StrLit)))
    if head == "const":
        if args:
            raise TypeError_("const takes nothing: (const)")
        return ("const",)
    raise TypeError_(f"unknown constraint {head!r}")
