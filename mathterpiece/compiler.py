"""The compiler: reads parsed forms into a world model (docs/syntax.md, docs/type-system.md,
docs/reference.md). Every declaration follows one body rule, (head name? positional… item…), and
every expression is typed, with what it reads, its range, and its value when it is known."""

import math
from collections.abc import Iterator
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

from mathterpiece.colors import parse_color
from mathterpiece.model import Expr, Model, Obj, Place, Range
from mathterpiece.nodes import (
    Bar,
    BoolLit,
    ComplexLit,
    Field,
    Form,
    InterpStrLit,
    IntLit,
    ListLit,
    Name,
    Node,
    NoneLit,
    Pos,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.parse import parse
from mathterpiece.types import (
    BOOL,
    COLOR,
    COMPARE,
    COMPLEX,
    INT,
    NUMBERS,
    POINT,
    RATIO,
    REAL,
    SCENE,
    STRING,
    TRANSFORM,
    ListT,
    Maybe,
    Refine,
    ShapeT,
    Type,
    TypeError_,
    fits,
    literal_type,
    refine,
    type_from_node,
)

RESERVED = frozenset(
    "scene animation transition wait in-order at-once when else true false none const self".split()
)
CONSTRAINT_HEADS = COMPARE | {"length", "one-of", "const"}
# Every number lies within ±10^150 (type-system.md, "What the compiler proves").
LIMIT = 1e150
UNBOUNDED: Range = (-LIMIT, LIMIT)
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

UNIT = Refine(REAL, ((">=", 0), ("<=", 1)))
NON_NEGATIVE = Refine(REAL, ((">=", 0),))
PAINT = Maybe(COLOR)
HALIGN = Refine(STRING, (("one-of", ("start", "middle", "end")),))
VALIGN = Refine(STRING, (("one-of", ("top", "middle", "baseline", "bottom")),))


@dataclass(frozen=True)
class Attr:
    type: Type
    default: object


TRANSFORMS = {
    "translate": Attr(POINT, (0, 0)),
    "transform": Attr(TRANSFORM, IDENTITY),
}
PAINTED = {
    "fill": Attr(PAINT, "#000000ff"),
    "stroke": Attr(PAINT, None),
    "stroke-width": Attr(NON_NEGATIVE, 1),
    "opacity": Attr(UNIT, 1),
    "fill-opacity": Attr(UNIT, 1),
    "stroke-opacity": Attr(UNIT, 1),
}
POSITIONED = {"x": Attr(REAL, 0), "y": Attr(REAL, 0)}
# The attributes each built-in shape takes, with their defaults (reference.md).
SHAPE_ATTRS: dict[str, dict[str, Attr]] = {
    "circle": {**POSITIONED, **PAINTED, **TRANSFORMS, "r": Attr(NON_NEGATIVE, 1)},
    "rect": {
        **POSITIONED,
        **PAINTED,
        **TRANSFORMS,
        "width": Attr(REAL, 1),
        "height": Attr(REAL, 1),
        "rx": Attr(REAL, 0),
        "ry": Attr(REAL, 0),
    },
    "ellipse": {**POSITIONED, **PAINTED, **TRANSFORMS, "rx": Attr(REAL, 1), "ry": Attr(REAL, 1)},
    "line": {**PAINTED, **TRANSFORMS, "from": Attr(POINT, (0, 0)), "to": Attr(POINT, (1, 0))},
    "triangle": {
        **PAINTED,
        **TRANSFORMS,
        "a": Attr(POINT, (0, 0)),
        "b": Attr(POINT, (1, 0)),
        "c": Attr(POINT, (0, 1)),
    },
    "text": {
        **POSITIONED,
        **PAINTED,
        **TRANSFORMS,
        "value": Attr(STRING, ""),
        "halign": Attr(HALIGN, "start"),
        "valign": Attr(VALIGN, "baseline"),
    },
    "group": dict(TRANSFORMS),
}
# The ones a shape is written with as its positional argument.
POSITIONAL = {"text": ("value",)}


class CompileError(Exception):
    def __init__(self, msg: str, pos: Pos):
        super().__init__(f"{pos}: {msg}")
        self.msg = msg
        self.pos = pos


def compile_source(src: str) -> Model:
    return compile_model(parse(src))


def compile_model(forms: tuple[Form, ...]) -> Model:
    return _Compiler().run(forms)


def _head(node: Node) -> str | None:
    if isinstance(node, Form) and isinstance(node.items[0], Name):
        part = node.items[0].parts[0]
        return part if len(node.items[0].parts) == 1 and isinstance(part, str) else None
    return None


def _is_constraint(node: Node) -> bool:
    head = _head(node)
    if head not in CONSTRAINT_HEADS:
        return False
    # A comparison with two arguments is an expression; with one, a constraint.
    return head not in COMPARE or len(node.items) == 2


class _Compiler:
    def __init__(self):
        self.model = Model()
        self.scene: int | None = None

    def run(self, forms: tuple[Form, ...]) -> Model:
        for form, scope in self.expand(forms, {}):
            self.top(form, scope)
        return self.model

    def expand(self, items, scope: dict) -> Iterator[tuple[Node, dict]]:
        """The items, with each (repeat n i decl…) replaced by its copies."""
        for item in items:
            if _head(item) != "repeat":
                yield item, scope
                continue
            if len(item.items) < 3:
                raise CompileError("repeat is (repeat n i declaration…)", item.pos)
            n = self.expr(item.items[1], INT, scope)
            if not n.known:
                raise CompileError("the count of a repeat must be known when compiling", item.pos)
            var = item.items[2]
            if not isinstance(var, Name) or len(var.parts) != 1 or var.parts[0] in RESERVED:
                raise CompileError("expected the name of the repeat's counter", var.pos)
            for k in range(n.value):
                yield from self.expand(item.items[3:], {**scope, var.parts[0]: _known(INT, k)})

    # Declarations ------------------------------------------------------------------------

    def top(self, form: Node, scope: dict) -> None:
        head = _head(form)
        if not isinstance(form, Form):
            raise CompileError("expected a declaration", form.pos)
        if head == "type":
            return self.type_decl(form)
        if head == "scene":
            return self.scene_decl(form)
        if head in SHAPE_ATTRS:
            raise CompileError("a shape is declared only inside the scene", form.pos)
        self.variable(form, None, "scene", scope)

    def name_of(self, form: Form, scope: dict | None = None) -> tuple[str | None, Pos]:
        if len(form.items) < 2:
            raise CompileError("a declaration needs a name", form.pos)
        node = form.items[1]
        if isinstance(node, StrLit):
            raise CompileError("a name is written bare, not in quotes", node.pos)
        if _head(node) == "name":
            name = self.built_name(node, scope or {})
        elif isinstance(node, Name) and len(node.parts) == 1 and isinstance(node.parts[0], str):
            name = node.parts[0]
        else:
            raise CompileError("expected a name", node.pos)
        if name == "_":
            return None, node.pos
        if name in RESERVED:
            raise CompileError(f"'{name}' is reserved", node.pos)
        if name in self.model.names:
            raise CompileError(f"'{name}' is already declared", node.pos)
        return name, node.pos

    def built_name(self, node: Form, scope: dict) -> str:
        """The name (name s) stands for; s must be known when compiling."""
        (arg,) = self.args(node, 1)
        e = self.expr(arg, STRING, scope)
        if not e.known:
            raise CompileError("the string of (name s) must be known when compiling", node.pos)
        return e.value

    def add(self, obj: Obj) -> int:
        self.model.objects.append(obj)
        i = len(self.model.objects) - 1
        if obj.name is not None:
            self.model.names[obj.name] = i
        if obj.parent is not None:
            self.model.objects[obj.parent].members.append(i)
        return i

    def type_decl(self, form: Form) -> None:
        name, pos = self.name_of(form)
        if name is None or len(form.items) < 3:
            raise CompileError("a type declaration is (type name base constraint…)", form.pos)
        base = self.type_of(form.items[2])
        try:
            t = refine(base, form.items[3:], name) if len(form.items) > 3 else base
        except TypeError_ as e:
            raise CompileError(str(e), form.pos) from None
        if isinstance(t, Refine) and t.name is None:
            t = replace(t, name=name)
        self.model.types[name] = t

    def type_of(self, node: Node) -> Type:
        try:
            return type_from_node(node, self.model.types)
        except TypeError_ as e:
            raise CompileError(str(e), node.pos) from None

    def variable(self, form: Form, parent: int | None, access: str, scope: dict) -> None:
        head = form.items[0]
        name, pos = self.name_of(form, scope)
        rest = list(form.items[2:])
        node = rest.pop(0) if rest and not _is_constraint(rest[0]) else None
        # A plain list takes its item type from its value (type-system.md, section 4).
        if isinstance(head, Name) and head.parts == ("list",):
            if node is None:
                raise CompileError("a plain list needs a value to take its item type from", pos)
            t = self.expr(node, None, scope).type
        else:
            t = self.type_of(head)
        try:
            if rest:
                t = refine(t, rest)
        except TypeError_ as e:
            raise CompileError(str(e), rest[0].pos) from None
        place = self.place(t, node, form.pos, "the value", scope=scope)
        self.add(Obj("variable", name, t, access, {"value": place}, parent=parent, pos=pos))

    def scene_decl(self, form: Form) -> None:
        if self.scene is not None:
            raise CompileError("a file has exactly one scene", form.pos)
        name, pos = self.name_of(form)
        attrs = {"background": Place(PAINT, None)}
        self.scene = self.add(Obj("scene", name, SCENE, attrs=attrs, pos=pos))
        for item, scope in self.expand(form.items[2:], {}):
            head = _head(item)
            if head == "background":
                attrs["background"] = self.place(
                    PAINT, item.items[1], item.pos, "background", scope=scope
                )
            elif head in SHAPE_ATTRS:
                self.shape(item, self.scene, scope)
            elif isinstance(item, Form):
                self.variable(item, self.scene, "scene", scope)
            else:
                raise CompileError("the scene holds shapes and variables", item.pos)

    def shape(self, form: Form, parent: int, scope: dict) -> int:
        kind = _head(form)
        assert kind is not None
        name, pos = self.name_of(form, scope)
        specs = SHAPE_ATTRS[kind]
        obj = Obj(kind, name, ShapeT(kind), parent=parent, pos=pos)
        i = self.add(obj)
        given: dict[str, tuple[Node, dict]] = {}
        items = list(form.items[2:])
        for attr in POSITIONAL.get(kind, ()):
            if items and _head(items[0]) is None:
                given[attr] = (items.pop(0), scope)
        for item, inner in self.expand(items, scope):
            head = _head(item)
            if kind == "group" and head in SHAPE_ATTRS:
                self.shape(item, i, inner)
                continue
            if head is None or not isinstance(item, Form) or len(item.items) != 2:
                raise CompileError(f"expected an argument such as (r 1), got {item}", item.pos)
            if head == "pos" and "x" in specs:
                for attr in ("x", "y"):
                    if attr in given:
                        raise CompileError(f"'{attr}' is given twice", item.pos)
                given["pos"] = (item.items[1], inner)
                continue
            if head not in specs:
                raise CompileError(f"a {kind} takes no argument '{head}'", item.pos)
            if head in given or ("pos" in given and head in ("x", "y")):
                raise CompileError(f"'{head}' is given twice", item.pos)
            given[head] = (item.items[1], inner)
        for attr, spec in specs.items():
            if attr in ("x", "y") and "pos" in given:
                continue
            node, inner = given.get(attr, (None, scope))
            obj.attrs[attr] = self.place(spec.type, node, form.pos, attr, spec.default, inner)
        if "pos" in given:
            node, inner = given["pos"]
            point = self.expr(node, POINT, inner)
            for k, attr in enumerate(("x", "y")):
                obj.attrs[attr] = self.settle(REAL, _part(point, k), attr, node.pos)
        return i

    # Places ------------------------------------------------------------------------------

    def place(
        self, t: Type, node: Node | None, pos: Pos, what: str, default=None, scope=None
    ) -> Place:
        if node is None:
            return Place(
                t, self.default(t, pos) if default is None and t != Maybe(COLOR) else default
            )
        return self.settle(t, self.expr(node, t, scope or {}), what, node.pos)

    def settle(self, t: Type, e: Expr, what: str, pos: Pos) -> Place:
        """A place holding e: free when e is known, bound otherwise. A bound value must stay
        within the place's constraints, or the compiler stops (type-system.md, 5.b and 5.c)."""
        if e.known:
            return Place(t, e.value)
        if isinstance(t, Refine):
            for c in t.constraints:
                if c[0] in COMPARE and not _range_within(e.range, c):
                    raise CompileError(f"{what} may break {_show(c)}", pos)
        return Place(t, expr=e)

    def default(self, t: Type, pos: Pos) -> object:
        """The value a type has when none is given (reference.md, "Defaults")."""
        base, cons = (t.base, t.constraints) if isinstance(t, Refine) else (t, ())
        if isinstance(base, Maybe):
            return None
        if base in NUMBERS:
            value = 0
            for c in cons:
                if c[0] in COMPARE and not _satisfies(0, c):
                    low = next((d for d in cons if d[0] == ">="), None)
                    if low is None:
                        raise CompileError(f"this {t} needs a value", pos)
                    value = low[1]
            return value
        if base == BOOL:
            return False
        if base == STRING:
            choices = next((c[1] for c in cons if c[0] == "one-of"), None)
            return choices[0] if choices else ""
        if base == COLOR:
            return "#000000ff"
        if base == POINT:
            return (0, 0)
        if base == TRANSFORM:
            return IDENTITY
        if isinstance(base, ListT):
            n = next((c[1] for c in cons if c[0] == "length"), 0)
            return [self.default(base.item, pos)] * n
        raise CompileError(f"a {t} needs a value", pos)

    # Expressions -------------------------------------------------------------------------

    def expr(self, node: Node, expected: Type | None, scope: dict) -> Expr:
        e = self.typed(node, expected, scope)
        # A constraint is checked on the value (known) or its range (settle), not on its type.
        target = _base(expected) if isinstance(expected, Refine) else expected
        if target is not None and not fits(e.type, target):
            raise CompileError(f"expected {expected}, got {e.type}", node.pos)
        if e.known and isinstance(expected, Refine):
            for c in expected.constraints:
                if c[0] != "const" and not _satisfies(e.value, c):
                    raise CompileError(f"{_value_str(e.value)} breaks {_show(c)}", node.pos)
        return e

    def typed(self, node: Node, expected: Type | None, scope: dict) -> Expr:
        if isinstance(node, (IntLit, RatioLit, RealLit, ComplexLit, StrLit, NoneLit)):
            return self.literal(node, expected)
        if isinstance(node, BoolLit):
            return _known(BOOL, node.value)
        if isinstance(node, ListLit):
            return self.list_literal(node, expected, scope)
        if isinstance(node, Name):
            return self.name(node, scope)
        if isinstance(node, InterpStrLit):
            return self.interp(node, scope)
        if isinstance(node, Bar):
            raise CompileError("type notation is not a value", node.pos)
        if isinstance(node, Form):
            return self.form(node, expected, scope)
        raise CompileError(f"unexpected {type(node).__name__}", node.pos)

    def literal(self, node: Node, expected: Type | None) -> Expr:
        place = expected if not isinstance(expected, Refine) else expected.base
        try:
            t = literal_type(node, place) if place is not None else literal_type(node, None)
        except TypeError_ as e:
            raise CompileError(str(e), node.pos) from None
        if isinstance(node, NoneLit):
            return _known(t, None)
        value = node.value
        if t == COLOR or (isinstance(t, Maybe) and t.inner == COLOR):
            value = parse_color(node.value)
        return _known(t, value)

    def list_literal(self, node: ListLit, expected: Type | None, scope: dict) -> Expr:
        place = expected.base if isinstance(expected, Refine) else expected
        if isinstance(place, Maybe):
            place = place.inner
        if place == POINT:
            items = [self.expr(i, REAL, scope) for i in node.items]
            if len(items) != 2:
                raise CompileError("a point is two numbers, [x y]", node.pos)
            return _gather(POINT, items)
        item = place.item if isinstance(place, ListT) else None
        if not node.items:
            if item is None:
                raise CompileError("an empty list needs its type: write list[T]", node.pos)
            return _known(ListT(item), [])
        items = [self.expr(i, item, scope) for i in node.items]
        t = item
        if t is None:
            t = items[0].type
            for e in items[1:]:
                if fits(t, e.type):
                    t = e.type
                elif not fits(e.type, t):
                    raise CompileError(f"a list holds one type, but has {t} and {e.type}", node.pos)
        return _gather(ListT(t), items)

    def interp(self, node: InterpStrLit, scope: dict) -> Expr:
        parts: list = []
        for part in node.parts:
            if isinstance(part, str):
                parts.append(part)
                continue
            inner, spec = (part.expr, part.spec) if isinstance(part, Field) else (part, "")
            e = self.expr(inner, None, scope)
            _check_spec(e.type, spec, part.pos)
            if e.known:
                parts.append(_show_value(e.type, e.value, spec))
            else:
                parts.append((e, spec))
        merged: list = []
        for p in parts:
            if isinstance(p, str) and merged and isinstance(merged[-1], str):
                merged[-1] += p
            else:
                merged.append(p)
        if all(isinstance(p, str) for p in merged):
            return _known(STRING, "".join(merged))
        exprs = [p[0] for p in merged if not isinstance(p, str)]
        t = Maybe(STRING) if any(isinstance(_base(e.type), Maybe) for e in exprs) else STRING
        return Expr("format", t, tuple(merged), frozenset().union(*(e.deps for e in exprs)))

    def name(self, node: Name, scope: dict) -> Expr:
        first = node.parts[0]
        if not isinstance(first, str):
            raise CompileError("expected a name", node.pos)
        e = self.lookup(first, scope, node.pos)
        for part in node.parts[1:]:
            e = self.part(e, part, scope, node.pos)
        return e

    def lookup(self, name: str, scope: dict, pos: Pos) -> Expr:
        if name in scope:
            return scope[name]
        if name in self.model.names:
            return self.read(self.model.names[name], None)
        raise CompileError(f"unknown name '{name}'", pos)

    def read(self, i: int, attr: str | None) -> Expr:
        obj = self.model.objects[i]
        if obj.kind == "variable" and attr is None:
            place = obj.value
        else:
            if attr is None:
                return Expr("obj", obj.type, (i,))
            if attr not in obj.attrs:
                raise CompileError(f"a {obj.kind} has no attribute '{attr}'", obj.pos)
            place = obj.attrs[attr]
        if not place.bound and _is_const(place.type):
            return _known(place.type, place.value)
        return Expr("read", place.type, (i, attr), frozenset({(i, attr)}), _type_range(place.type))

    def part(self, e: Expr, part, scope: dict, pos: Pos) -> Expr:
        if isinstance(part, str):
            if e.op == "obj":
                obj = self.model.objects[e.args[0]]
                if part == "pos" and "x" in obj.attrs:
                    return _gather(POINT, [self.read(e.args[0], "x"), self.read(e.args[0], "y")])
                if part not in obj.attrs:
                    raise CompileError(f"a {obj.kind} has no attribute '{part}'", pos)
                return self.read(e.args[0], part)
            if e.type == POINT and part in ("x", "y"):
                return _part(e, 0 if part == "x" else 1)
            raise CompileError(f"a {e.type} has no attribute '{part}'", pos)
        index = self.expr(part, None, scope)
        if e.op == "obj" and index.type == STRING:
            obj = self.model.objects[e.args[0]]
            if not index.known:
                raise CompileError("a member's name must be known when compiling", pos)
            for m in obj.members:
                if self.model.objects[m].name == index.value:
                    return self.read(m, None)
            raise CompileError(f"a {obj.kind} has no member '{index.value}'", pos)
        if not fits(index.type, INT):
            raise CompileError(f"a position is an int, got {index.type}", pos)
        whole = _base(e.type)
        if isinstance(whole, ListT) or whole == POINT:
            item = REAL if whole == POINT else whole.item
            if e.known and index.known:
                items = e.value
                k = index.value
                if not -len(items) <= k < len(items):
                    raise CompileError(f"position {k} is out of range", pos)
                return _known(item, items[k])
            return Expr("part", item, (e, index), e.deps | index.deps, _type_range(item))
        if e.op == "obj":
            obj = self.model.objects[e.args[0]]
            if obj.members and index.known:
                k = index.value
                if not -len(obj.members) <= k < len(obj.members):
                    raise CompileError(f"position {k} is out of range", pos)
                return self.read(obj.members[k], None)
        raise CompileError(f"a {e.type} has no items", pos)

    def form(self, node: Form, expected: Type | None, scope: dict) -> Expr:
        head = _head(node)
        args = node.items[1:]
        if head == "if":
            if len(args) != 3:
                raise CompileError("if takes a condition and two branches", node.pos)
            c = self.expr(args[0], BOOL, scope)
            a, b = (self.expr(x, expected, scope) for x in args[1:])
            if c.known:
                return a if c.value else b
            return Expr(
                "if",
                _join(a.type, b.type, node.pos),
                (c, a, b),
                c.deps | a.deps | b.deps,
                _union(a.range, b.range),
            )
        if head == "cond":
            return self.cond(node, expected, scope)
        if head in ("and", "or"):
            parts = [self.expr(x, BOOL, scope) for x in args]
            stop = head == "or"
            kept = []
            for p in parts:
                if p.known:
                    if bool(p.value) == stop:
                        return _known(BOOL, stop)
                    continue
                kept.append(p)
            if not kept:
                return _known(BOOL, not stop)
            return Expr(head, BOOL, tuple(kept), frozenset().union(*(p.deps for p in kept)))
        if head == "not":
            (a,) = self.args(node, 1)
            e = self.expr(a, BOOL, scope)
            return _known(BOOL, not e.value) if e.known else Expr("not", BOOL, (e,), e.deps)
        if head == "let":
            return self.let(node, expected, scope)
        if head == "name":
            return self.lookup(self.built_name(node, scope), scope, node.pos)
        if head == ".":
            x, y = self.args(node, 2)
            whole = self.expr(x, None, scope)
            if isinstance(y, Name) and len(y.parts) == 1 and isinstance(y.parts[0], str):
                return self.part(whole, y.parts[0], scope, node.pos)
            return self.part(whole, y, scope, node.pos)
        if head == "abs":
            (a,) = self.args(node, 1)
            return self.abs(node, self.expr(a, None, scope))
        if head in ARITH:
            return self.arith(node, head, [self.expr(x, None, scope) for x in args])
        if head in COMPARE or head in ("=", "!="):
            a, b = self.args(node, 2)
            ea = self.expr(a, None, scope)
            eb = self.typed_like(b, ea.type, scope)
            return self.compare(node, head, ea, eb)
        raise CompileError(f"unknown function '{head}'", node.pos)

    def typed_like(self, node: Node, other: Type, scope: dict) -> Expr:
        """In (= o.fill 'red'), the literal takes the other side's type."""
        if isinstance(node, (StrLit, ListLit)):
            return self.expr(node, other, scope)
        return self.expr(node, None, scope)

    def args(self, node: Form, n: int) -> tuple[Node, ...]:
        if len(node.items) - 1 != n:
            raise CompileError(f"{_head(node)} takes {n} argument{'s' * (n != 1)}", node.pos)
        return node.items[1:]

    def cond(self, node: Form, expected: Type | None, scope: dict) -> Expr:
        clauses = node.items[1:]
        if not clauses or _head(clauses[-1]) != "else":
            raise CompileError("cond ends with an (else …) clause", node.pos)
        result = None
        for clause in reversed(clauses):
            if not isinstance(clause, Form) or len(clause.items) != 2:
                raise CompileError("a cond clause is (test value)", clause.pos)
            v = self.expr(clause.items[1], expected, scope)
            if _head(clause) == "else" and result is None:
                result = v
                continue
            c = self.expr(clause.items[0], BOOL, scope)
            if c.known:
                result = v if c.value else result
                continue
            assert result is not None
            result = Expr(
                "if",
                _join(v.type, result.type, clause.pos),
                (c, v, result),
                c.deps | v.deps | result.deps,
                _union(v.range, result.range),
            )
        assert result is not None
        return result

    def let(self, node: Form, expected: Type | None, scope: dict) -> Expr:
        if len(node.items) != 3 or not isinstance(node.items[1], Form):
            raise CompileError("let is (let ((name value) …) body)", node.pos)
        inner = dict(scope)
        for binding in node.items[1].items:
            if not isinstance(binding, Form) or len(binding.items) != 2:
                raise CompileError("a let binding is (name value)", binding.pos)
            name = binding.items[0]
            if not isinstance(name, Name) or len(name.parts) != 1:
                raise CompileError("expected a name", binding.pos)
            inner[name.parts[0]] = self.expr(binding.items[1], None, inner)
        return self.expr(node.items[2], expected, inner)

    def arith(self, node: Form, op: str, args: list[Expr]) -> Expr:
        if not args or (op in ("/", "^", "mod") and len(args) != 2):
            raise CompileError(
                f"{op} takes {'two' if op in ('/', '^', 'mod') else 'some'} numbers", node.pos
            )
        for a in args:
            if a.type not in NUMBERS and _base(a.type) not in NUMBERS:
                raise CompileError(f"{op} takes numbers, got {a.type}", node.pos)
        t = max((_base(a.type) for a in args), key=NUMBERS.index)
        if op == "/" and t == INT:
            t = RATIO
        if all(a.known for a in args):
            try:
                v = _fold(op, [a.value for a in args])
            except ZeroDivisionError:
                raise CompileError("division by zero", node.pos) from None
            if t == RATIO and isinstance(v, Fraction) and v.denominator == 1:
                v = Fraction(v)
            return _known(t, v)
        deps = frozenset().union(*(a.deps for a in args))
        return Expr(op, t, tuple(args), deps, _range_of(op, [a.range for a in args]))

    def abs(self, node: Form, a: Expr) -> Expr:
        base = _base(a.type)
        if base not in NUMBERS:
            raise CompileError(f"abs takes a number, got {a.type}", node.pos)
        t = REAL if base == COMPLEX else base
        if a.known:
            return _known(t, abs(a.value))
        r = a.range
        if r is not None:
            r = (
                (0.0, max(-r[0], r[1]))
                if r[0] <= 0 <= r[1]
                else (min(map(abs, r)), max(map(abs, r)))
            )
        return Expr("abs", t, (a,), a.deps, r if r is not None else (0.0, LIMIT))

    def compare(self, node: Form, op: str, a: Expr, b: Expr) -> Expr:
        if op in COMPARE:
            for e in (a, b):
                if _base(e.type) not in NUMBERS[:3]:
                    raise CompileError(f"{op} compares numbers, got {e.type}", node.pos)
        elif not (fits(a.type, b.type) or fits(b.type, a.type)):
            raise CompileError(
                f"{op} compares two of one type, got {a.type} and {b.type}", node.pos
            )
        if a.known and b.known:
            return _known(BOOL, _fold(op, [a.value, b.value]))
        return Expr(op, BOOL, (a, b), a.deps | b.deps)


ARITH = {"+", "-", "*", "/", "^", "mod"}


def _known(t: Type, value) -> Expr:
    r = (
        (float(value), float(value))
        if isinstance(value, (int, float, Fraction)) and not isinstance(value, bool)
        else None
    )
    return Expr("lit", t, (value,), range=r, known=True, value=value)


def _gather(t: Type, items: list[Expr]) -> Expr:
    if all(i.known for i in items):
        v = [i.value for i in items]
        return _known(t, tuple(v) if t == POINT else v)
    return Expr("list", t, tuple(items), frozenset().union(*(i.deps for i in items)))


def _part(e: Expr, k: int) -> Expr:
    if e.known:
        return _known(REAL, e.value[k])
    if e.op == "list":
        return e.args[k]
    return Expr("part", REAL, (e, _known(INT, k)), e.deps, UNBOUNDED)


def _base(t: Type) -> Type:
    return t.base if isinstance(t, Refine) else t


def _is_const(t: Type) -> bool:
    return isinstance(t, Refine) and ("const",) in t.constraints


def _type_range(t: Type) -> Range:
    if isinstance(t, Refine) and t.base in NUMBERS[:3]:
        lo, hi = UNBOUNDED
        for c in t.constraints:
            if c[0] in (">=", ">"):
                lo = max(lo, float(c[1]))
            elif c[0] in ("<=", "<"):
                hi = min(hi, float(c[1]))
        return (lo, hi)
    if t in NUMBERS[:3]:
        return UNBOUNDED
    return None


def _join(a: Type, b: Type, pos: Pos) -> Type:
    if fits(a, b):
        return b
    if fits(b, a):
        return a
    raise CompileError(f"the branches give {a} and {b}", pos)


def _union(a: Range, b: Range) -> Range:
    if a is None or b is None:
        return None
    return (min(a[0], b[0]), max(a[1], b[1]))


def _range_of(op: str, ranges: list[Range]) -> Range:
    if any(r is None for r in ranges):
        return None
    if op == "+":
        return (sum(r[0] for r in ranges), sum(r[1] for r in ranges))
    if op == "-":
        if len(ranges) == 1:
            return (-ranges[0][1], -ranges[0][0])
        lo, hi = ranges[0]
        for r in ranges[1:]:
            lo, hi = lo - r[1], hi - r[0]
        return (lo, hi)
    if op == "*":
        lo, hi = ranges[0]
        for r in ranges[1:]:
            ends = [lo * r[0], lo * r[1], hi * r[0], hi * r[1]]
            ends = [0.0 if math.isnan(x) else x for x in ends]
            lo, hi = min(ends), max(ends)
        return (lo, hi)
    if op == "/":
        a, b = ranges
        if b[0] <= 0 <= b[1]:
            return UNBOUNDED
        ends = [a[0] / b[0], a[0] / b[1], a[1] / b[0], a[1] / b[1]]
        return (min(ends), max(ends))
    return UNBOUNDED


def _range_within(r: Range, c) -> bool:
    if r is None:
        return False
    lo, hi = r
    bound = float(c[1])
    return {">=": lo >= bound, ">": lo > bound, "<=": hi <= bound, "<": hi < bound}[c[0]]


def _satisfies(value, c) -> bool:
    kind = c[0]
    if kind in COMPARE:
        return {">=": value >= c[1], ">": value > c[1], "<=": value <= c[1], "<": value < c[1]}[
            kind
        ]
    if kind == "one-of":
        return value in c[1]
    if kind == "length":
        return len(value) == c[1]
    return True


def _show(c) -> str:
    return "(" + " ".join(str(p) for p in c) + ")"


def _value_str(v) -> str:
    return str(v)


# What a format spec is tried on, to check it fits the type.
_SAMPLES = {INT: 1, RATIO: Decimal("1.5"), REAL: Decimal("1.5"), STRING: "a"}


def _check_spec(t: Type, spec: str, pos: Pos) -> None:
    if not spec:
        return
    base = _base(t)
    base = _base(base.inner) if isinstance(base, Maybe) else base
    try:
        format(_SAMPLES[base], spec)
    except (KeyError, ValueError, TypeError):
        raise CompileError(f"'{spec}' is not a format for a {t}", pos) from None


def _show_value(t: Type, v, spec: str) -> str:
    """A value shown in a string. Halves round away from zero on the number's shortest
    decimal form (reference.md, "Numbers"), so 2.675 to two places is 2.68."""
    base = _base(t)
    if base == INT:
        return format(int(v), spec)
    if base in (RATIO, REAL):
        if not spec:
            return repr(float(v))
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            return format(Decimal(repr(float(v))), spec)
    if base == BOOL:
        return "True" if v else "False"
    if base == POINT:
        return "(" + ", ".join(repr(float(x)) for x in v) + ")"
    return format(v, spec) if spec else str(v)


def _fold(op: str, vals: list):
    if op == "+":
        return sum(vals[1:], vals[0])
    if op == "-":
        if len(vals) == 1:
            return -vals[0]
        out = vals[0]
        for v in vals[1:]:
            out -= v
        return out
    if op == "*":
        out = vals[0]
        for v in vals[1:]:
            out *= v
        return out
    if op == "/":
        a, b = vals
        if b == 0:
            raise ZeroDivisionError
        if isinstance(a, int) and isinstance(b, int):
            return Fraction(a, b)
        return a / b
    if op == "^":
        return vals[0] ** vals[1]
    if op == "mod":
        a, b = vals
        if b == 0:
            raise ZeroDivisionError
        return a % b
    a, b = vals
    return {
        "=": a == b,
        "!=": a != b,
        "<": a < b,
        "<=": a <= b,
        ">": a > b,
        ">=": a >= b,
    }[op]
