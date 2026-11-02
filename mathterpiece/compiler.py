"""The compiler: reads parsed forms into a world model (docs/syntax.md, docs/type-system.md,
docs/reference.md). Every declaration follows one body rule, (head name? positional… item…), and
every expression is typed, with what it reads, its range, and its value when it is known."""

import math
import sys
from collections.abc import Iterator
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

from mathterpiece.colors import parse_color
from mathterpiece.model import (
    Expr,
    FuncDef,
    Model,
    MotifDef,
    Obj,
    Param,
    Place,
    Range,
    VariantDef,
)
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
    NONE,
    NUMBERS,
    POINT,
    RATIO,
    REAL,
    SCENE,
    STRING,
    TRANSFORM,
    FuncT,
    Interface,
    ListT,
    Maybe,
    Prim,
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
# The result of a function whose body is being compiled for the first time: a recursive call
# has it, and the branch that does not recurse decides the real one.
RECURSING = Prim("recursing")
# Forms that are not calls, so a function of the same name never replaces them.
SPECIAL = {"if", "cond", "and", "or", "let", "name", ".", "fn", "repeat"}
# A computed result beyond the largest real overflows, which is undefined.
MAX_REAL = sys.float_info.max
WHOLE: Range = (-MAX_REAL, MAX_REAL)
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
# What a motif instance takes besides its parameters (reference.md, "The scene and shapes").
INSTANCE_ATTRS = {**POSITIONED, **PAINTED, **TRANSFORMS}
# The paint arguments a motif instance gives its members as defaults; opacity is its own.
INHERITED = ("fill", "stroke", "stroke-width", "fill-opacity", "stroke-opacity")
# Arguments a group takes only to write them on each of its members.
SPREAD = frozenset(POSITIONED) | frozenset(PAINTED) | {"pos"}
# The ends or corners whose mean is a line's or a triangle's position.
CORNERS = {"line": ("from", "to"), "triangle": ("a", "b", "c")}
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
    if isinstance(node, Form) and node.items and isinstance(node.items[0], Name):
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
        # The container the expression being compiled sits in: a group, or None for the scene
        # and the top level. Reads convert through the transforms not shared with it.
        self.frame: int | None = None
        # The motif instances whose bodies are being compiled, innermost last: each with its
        # id, its members' names, its parameters and bound variables, and the path its
        # members are named by (None inside an anonymous instance).
        self.bodies: list[dict] = []

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
        if head == "motif":
            return self.motif_decl(form)
        if head == "variant":
            return self.variant_decl(form)
        if head == "func":
            return self.func_decl(form)
        if self.shape_kind(form):
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
        taken = self.model.names.keys() | self.model.funcs.keys() | self.model.types.keys()
        if self.bodies:
            taken = self.bodies[-1]["names"].keys() | self.bodies[-1]["attrs"]
        if name in taken:
            raise CompileError(f"'{name}' is already declared", node.pos)
        return name, node.pos

    def shape_kind(self, node: Node) -> tuple[str, bool] | None:
        """The shape a form declares, and whether it is declared T|none."""
        if not isinstance(node, Form) or not node.items:
            return None
        head = node.items[0]
        absent = False
        if isinstance(head, Bar) and len(head.items) == 2 and isinstance(head.items[1], NoneLit):
            head, absent = head.items[0], True
        if isinstance(head, Name) and len(head.parts) == 1:
            kind = head.parts[0]
            if kind in SHAPE_ATTRS or kind in self.model.motifs or kind in self.model.variants:
                return kind, absent
        return None

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
        if obj.name is not None and self.bodies:
            body = self.bodies[-1]
            body["names"][obj.name] = i
            if body["path"] is not None:
                self.model.names[f"{body['path']}.{obj.name}"] = i
        elif obj.name is not None:
            self.model.names[obj.name] = i
        if obj.parent is not None and obj.kind != "variable":
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
        name, pos, t, node = self.declared(form, scope)
        if isinstance(_core(t), FuncT):
            raise CompileError("a variable cannot hold a function", pos)
        if node is not None and self.shape_kind(node):
            # (shape sel (circle c …)) declares the circle where the variable is, and holds it.
            if parent is None:
                raise CompileError("a shape is declared only inside the scene", node.pos)
            shape = self.read(self.shape(node, parent, scope), None)
            place = self.settle(t, self.expect(shape, t, node.pos), "the value", node.pos)
            self.add(Obj("variable", name, t, access, {"value": place}, parent=parent, pos=pos))
            return
        place = self.place(t, node, form.pos, "the value", scope=scope)
        self.add(Obj("variable", name, t, access, {"value": place}, parent=parent, pos=pos))

    def declared(self, form: Form, scope: dict) -> tuple[str | None, Pos, Type, Node | None]:
        """A (T name value? constraint…) form's name, its type with the constraints, and its
        value's source."""
        if not form.items:
            raise CompileError("expected a declaration, got ()", form.pos)
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
        return name, pos, t, node

    def motif_decl(self, form: Form) -> None:
        name, pos = self.name_of(form)
        if name is None or len(form.items) < 3:
            raise CompileError("a motif is (motif name parameters member…)", form.pos)
        if name in SHAPE_ATTRS or name in self.model.types:
            raise CompileError(f"'{name}' is already declared", pos)
        params = self.params(form.items[2])
        for p in params:
            if p.name in INSTANCE_ATTRS or p.name == "pos":
                raise CompileError(f"every motif instance already has '{p.name}'", form.pos)
        self.model.motifs[name] = MotifDef(name, params, form.items[3:], pos)
        self.model.types[name] = ShapeT(name)
        self.trial(name, form.pos)

    def func_decl(self, form: Form) -> None:
        name, pos = self.name_of(form)
        if name is None or len(form.items) != 4:
            raise CompileError("a function is (func name parameters body)", form.pos)
        params = self.params(form.items[2])
        fid = len(self.model.functions)
        f = FuncDef(name, params, RECURSING, pos=pos)
        self.model.functions.append(f)
        self.model.funcs[name] = fid
        # A recursive call gives RECURSING until the body's type is known; compile again with
        # that type until it no longer changes, since it may broaden (int, then ratio).
        for _ in range(len(NUMBERS) + 2):
            body = self.function_body(params, form.items[3])
            if _inner(body.type) == RECURSING:
                raise CompileError(f"{name} has no base case: every branch calls {name}", pos)
            if body.type == f.result:
                break
            f.result = body.type
        f.body, f.deps = body, body.deps

    def function_body(self, params, node: Node, expected=None, outer=None) -> Expr:
        scope = dict(outer or {})
        for p in params:
            scope[p.name] = Expr("local", p.type, (p.name,), range=_type_range(p.type))
        # A read inside a function uses the frame of the place that called it.
        saved, self.frame = self.frame, "caller"
        try:
            return self.expr(node, expected, scope)
        finally:
            self.frame = saved

    def call(self, fid: int, node: Form, scope: dict) -> Expr:
        f = self.model.functions[fid]
        given = node.items[1:]
        n = len(f.params)
        if len(given) > n:
            raise CompileError(f"{f.name} takes {n} argument{'s' * (n != 1)}", node.pos)
        args, deps, maybe = self.arguments(f.params, given, scope, node.pos)
        t = f.result
        if maybe and t != RECURSING:
            t = _maybe(t)
        r = f.body.range if f.body is not None else _type_range(t)
        return Expr("call", t, (fid, *args), deps | f.deps, r)

    def arguments(self, params, given, scope: dict, pos: Pos) -> tuple[list, frozenset, bool]:
        """Each argument, or what a left-out parameter takes. An argument that may be none
        given to a parameter that does not accept it makes the call none (type-system.md 5.c);
        one given to a constrained parameter must be proved to fit (5.b)."""
        args, maybe = [], False
        for k, p in enumerate(params):
            if k < len(given):
                accepts = _may_be_none(p.type)
                e = self.expr(given[k], p.type if accepts else _maybe(p.type), scope)
                maybe |= not accepts and _may_be_none(e.type)
                inner = _inner(p.type)
                if not e.known and isinstance(inner, Refine):
                    for c in inner.constraints:
                        if c[0] in COMPARE and not _range_within(e.range, c):
                            raise CompileError(f"{p.name} may break {_show(c)}", given[k].pos)
            elif p.default is not None:
                e = self.expr(p.default, p.type, {})
            else:
                e = _known(p.type, self.default(p.type, pos))
            args.append(e)
        return args, frozenset().union(*(a.deps for a in args)), maybe

    def apply(self, fexpr: Expr, node: Form, scope: dict) -> Expr:
        ft = _core(fexpr.type)
        given = node.items[1:]
        if len(given) != len(ft.params):
            n = len(ft.params)
            raise CompileError(f"this function takes {n} argument{'s' * (n != 1)}", node.pos)
        params = tuple(Param(f"argument {k + 1}", t) for k, t in enumerate(ft.params))
        args, deps, maybe = self.arguments(params, given, scope, node.pos)
        t = _maybe(ft.result) if maybe else ft.result
        return Expr("apply", t, (fexpr, *args), deps | fexpr.deps, _type_range(t))

    def fn(self, node: Form, expected: Type | None, scope: dict) -> Expr:
        if len(node.items) != 3:
            raise CompileError("fn is (fn parameters body)", node.pos)
        ft = _core(expected) if expected is not None else None
        ft = ft if isinstance(ft, FuncT) else None
        pnode = node.items[1]
        if isinstance(pnode, Name):
            if ft is None or len(ft.params) != 1:
                raise CompileError(
                    "a bare parameter of fn needs its type from its place: write (fn (T name) …)",
                    pnode.pos,
                )
            params = (Param(pnode.parts[0], ft.params[0]),)
        else:
            params = self.params(pnode)
        body = self.function_body(params, node.items[2], ft.result if ft else None, scope)
        fid = len(self.model.functions)
        self.model.functions.append(FuncDef(None, params, body.type, body, body.deps, node.pos))
        captured = tuple(sorted(_locals(body) - {p.name for p in params}))
        t = FuncT(tuple(p.type for p in params), body.type)
        return Expr("func", t, (fid, captured), body.deps)

    def trial(self, name: str, pos: Pos) -> None:
        """Compile one instance and discard it, so a body's errors show without any instance."""
        objects, names = len(self.model.objects), dict(self.model.names)
        try:
            self.shape(Form((Name((name,), pos), Name(("_",), pos)), pos), None, {})
        finally:
            del self.model.objects[objects:]
            self.model.names = names

    def variant_decl(self, form: Form) -> None:
        name, pos = self.name_of(form)
        if name is None or len(form.items) < 4:
            raise CompileError("a variant is (variant name parameters shape)", form.pos)
        if len(form.items) != 4 or not self.shape_kind(form.items[3]):
            raise CompileError("a variant's body is one shape", form.pos)
        if name in SHAPE_ATTRS or name in self.model.types:
            raise CompileError(f"'{name}' is already declared", pos)
        body = form.items[3]
        base = self.shape_kind(body)[0]
        if base == "group":
            raise CompileError("a group has no variants", body.pos)
        params = self.params(form.items[2])
        taken = self.attrs_of(base)
        for p in params:
            if p.name in taken:
                raise CompileError(f"a {base} already has '{p.name}'", form.pos)
        fixed = set()
        for k, item in enumerate(body.items[2:]):
            head = _head(item)
            if head is None and k < len(POSITIONAL.get(base, ())):
                fixed.add(POSITIONAL[base][k])
            elif head == "pos":
                fixed |= {"x", "y"}
            elif head is not None:
                fixed.add(head)
        self.model.variants[name] = VariantDef(name, params, base, body, frozenset(fixed), pos)
        self.model.types[name] = ShapeT(name, self.model.types.get(base, ShapeT(base)))
        self.trial(name, form.pos)

    def attrs_of(self, kind: str) -> set:
        """What an instance of a shape type is given by name: arguments and parameters."""
        if kind in self.model.variants:
            v = self.model.variants[kind]
            return self.attrs_of(v.base) | {p.name for p in v.params}
        if kind in self.model.motifs:
            return set(INSTANCE_ATTRS) | {"pos"} | {p.name for p in self.model.motifs[kind].params}
        return set(SHAPE_ATTRS[kind]) | ({"pos"} if "x" in SHAPE_ATTRS[kind] else set())

    def fixed_of(self, kind: str) -> frozenset:
        if kind not in self.model.variants:
            return frozenset()
        v = self.model.variants[kind]
        return v.fixed | self.fixed_of(v.base)

    def variant_instance(
        self, form: Form, parent, scope: dict, spread=None, items=None, pre=(), outer=None
    ) -> int:
        """An instance of a variant: its base shape, given the body's arguments, which are fixed,
        and the instance's own; the variant's parameters are attributes of it too."""
        kind, absent = self.shape_kind(form)
        v = self.model.variants[kind]
        outer = outer or kind
        fixed = self.fixed_of(kind)
        params = {p.name for p in v.params}
        own = list(items) if items is not None else _scoped(form.items[2:], scope)
        mine, rest = {}, []
        for item, inner in self.expand_scoped(own):
            head = _head(item)
            if head in params:
                if head in mine or not isinstance(item, Form) or len(item.items) != 2:
                    raise CompileError(f"'{head}' is given twice", item.pos)
                mine[head] = (item.items[1], inner)
                continue
            hit = sorted(fixed & ({"x", "y"} if head == "pos" else {head}))
            if hit:
                raise CompileError(f"a {kind}'s {hit[0]} is fixed", item.pos)
            rest.append((item, inner))
        i = len(self.model.objects)
        body_scope = {p: (lambda p=p: self.read(i, p)) for p in params}

        def place_params(obj: Obj) -> None:
            for p in v.params:
                node, inner = mine.get(p.name, (p.default, {}))
                obj.attrs[p.name] = self.place(p.type, node, form.pos, p.name, None, inner)

        merged = _scoped(v.body.items[2:], body_scope) + rest
        head = Name((v.base,), form.pos)
        if absent:
            head = Bar((head, NoneLit(form.pos)), form.pos)
        base_form = Form((head, form.items[1]), form.pos)
        pre = (*pre, place_params)
        if v.base in self.model.variants:
            return self.variant_instance(base_form, parent, scope, spread, merged, pre, outer)
        j = self.shape(base_form, parent, scope, spread, merged, pre)
        obj = self.model.objects[j]
        obj.of = outer
        obj.type = Maybe(self.model.types[outer]) if absent else self.model.types[outer]
        for attr in self.fixed_of(outer):
            obj.attrs[attr].fixed = True
        return j

    def expand_scoped(self, scoped: list) -> Iterator[tuple[Node, dict]]:
        for node, scope in scoped:
            yield from self.expand([node], scope)

    def params(self, node: Node) -> tuple[Param, ...]:
        """One parameter (real t 0.5), or a list of them ((real t 0.5) (color c 'red'))."""
        if not isinstance(node, Form):
            raise CompileError("expected a parameter such as (real t 0.5)", node.pos)
        if not node.items:
            return ()
        forms = node.items if isinstance(node.items[0], Form) else (node,)
        out = []
        for f in forms:
            if not isinstance(f, Form) or len(f.items) < 2:
                raise CompileError("expected a parameter such as (real t 0.5)", f.pos)
            name, pos, t, default = self.declared(f, {})
            if name is None:
                raise CompileError("a parameter needs a name", pos)
            if any(p.name == name for p in out):
                raise CompileError(f"'{name}' is already declared", pos)
            out.append(Param(name, t, default))
        return tuple(out)

    def instance(
        self, form: Form, parent, scope: dict, spread=None, absent=False, items=None, pre=()
    ) -> int:
        kind = self.shape_kind(form)[0]
        motif = self.model.motifs[kind]
        name, pos = self.name_of(form, scope)
        t = Maybe(ShapeT(kind)) if absent else ShapeT(kind)
        obj = Obj("instance", name, t, parent=parent, pos=pos, of=kind)
        i = self.add(obj)
        params = {p.name: p for p in motif.params}
        given: dict[str, tuple[Node, dict]] = {}
        scoped = list(items) if items is not None else _scoped(form.items[2:], scope)
        for item, inner in self.expand_scoped(scoped):
            head = _head(item)
            if self.shape_kind(item) and head not in params:
                raise CompileError(f"an instance of {kind} takes no members", item.pos)
            if head is None or not isinstance(item, Form) or len(item.items) != 2:
                raise CompileError(f"expected an argument such as (r 1), got {item}", item.pos)
            if head not in params and head not in INSTANCE_ATTRS and head != "pos":
                raise CompileError(f"a {kind} takes no argument '{head}'", item.pos)
            if head in given or _overlaps(head, given):
                raise CompileError(f"'{head}' is given twice", item.pos)
            given[head] = (item.items[1], inner)
        for attr, (node, inner) in (spread or {}).items():
            if not _overlaps(attr, given):
                given[attr] = (node, inner)
        saved, self.frame = self.frame, (parent if parent != self.scene else None)
        try:
            for f in pre:
                f(obj)
            for p in motif.params:
                node, inner = given.get(p.name, (p.default, {}))
                at = _maybe(p.type) if absent else p.type
                obj.attrs[p.name] = self.place(at, node, form.pos, p.name, None, inner)
            self.shape_attrs(obj, given, absent, form.pos, scope, INSTANCE_ATTRS)
        finally:
            self.frame = saved
        outer = self.bodies[-1]["path"] if self.bodies else ""
        path = None if name is None or outer is None else (f"{outer}.{name}" if outer else name)
        self.bodies.append({"id": i, "names": {}, "attrs": set(params), "path": path})
        saved, self.frame = self.frame, i
        down = {a: (_dot(Name(("self",), form.pos), a), {}) for a in INHERITED}
        try:
            for item, inner in self.expand(motif.body, {}):
                if self.shape_kind(item):
                    self.shape(item, i, inner, down)
                elif isinstance(item, Form) and _head(item) not in ("motif", "scene"):
                    self.body_variable(item, obj, inner)
                else:
                    raise CompileError("a motif's body holds shapes and bound variables", item.pos)
        finally:
            self.bodies.pop()
            self.frame = saved
        return i

    def body_variable(self, form: Form, obj: Obj, scope: dict) -> None:
        name, pos, t, node = self.declared(form, scope)
        place = self.place(t, node, form.pos, "the value", scope=scope)
        if name is None:
            raise CompileError("a variable in a motif's body needs a name", pos)
        if not place.bound and not _is_const(t):
            raise CompileError(
                "a motif's body declares only bound variables; free state is a parameter", pos
            )
        obj.attrs[name] = place
        self.bodies[-1]["attrs"].add(name)

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
            elif head in ("motif", "variant", "func"):
                raise CompileError(f"a {head} is declared only at the top level", item.pos)
            elif self.shape_kind(item):
                self.shape(item, self.scene, scope)
            elif isinstance(item, Form):
                self.variable(item, self.scene, "scene", scope)
            else:
                raise CompileError("the scene holds shapes and variables", item.pos)

    def shape(self, form: Form, parent, scope: dict, spread=None, items=None, pre=()) -> int:
        """A shape declaration. items, when given, replaces the form's own items, each with its
        scope, and pre runs on the new object before its attributes are compiled (a variant
        uses both)."""
        kind, absent = self.shape_kind(form)
        if kind in self.model.variants:
            return self.variant_instance(form, parent, scope, spread)
        if kind in self.model.motifs:
            return self.instance(form, parent, scope, spread, absent, items, pre)
        name, pos = self.name_of(form, scope)
        specs = SHAPE_ATTRS[kind]
        # A shape declared T|none may be absent, so its attributes may be none.
        t = Maybe(ShapeT(kind)) if absent else ShapeT(kind)
        obj = Obj(kind, name, t, parent=parent, pos=pos)
        i = self.add(obj)
        takes = specs.keys() | SPREAD if kind == "group" else specs.keys()
        given: dict[str, tuple[Node, dict]] = {}
        members: list[tuple[Node, dict]] = []
        scoped = list(items) if items is not None else _scoped(form.items[2:], scope)
        for attr in POSITIONAL.get(kind, ()):
            if scoped and _head(scoped[0][0]) is None:
                given[attr] = scoped.pop(0)
        for item, inner in self.expand_scoped(scoped):
            if kind == "group" and self.shape_kind(item):
                members.append((item, inner))
                continue
            head = _head(item)
            if head is None or not isinstance(item, Form) or len(item.items) != 2:
                raise CompileError(f"expected an argument such as (r 1), got {item}", item.pos)
            if head == "pos" and "x" in takes:
                for attr in ("x", "y"):
                    if attr in given:
                        raise CompileError(f"'{attr}' is given twice", item.pos)
            elif head not in takes:
                raise CompileError(f"a {kind} takes no argument '{head}'", item.pos)
            if head in given or ("pos" in given and head in ("x", "y")):
                raise CompileError(f"'{head}' is given twice", item.pos)
            given[head] = (item.items[1], inner)
        # A group's arguments are defaults for its members: a member's own value wins, and the
        # nearest group's wins over one further out (reference.md, "The scene and shapes").
        down = dict(spread or {})
        if kind == "group":
            for attr in [a for a in given if a in SPREAD]:
                down.update(_coordinates(attr, *given.pop(attr)))
        else:
            for attr, (node, inner) in down.items():
                if attr not in specs:
                    raise CompileError(f"a {kind} takes no argument '{attr}'", node.pos)
                if attr not in given and not (attr in ("x", "y") and "pos" in given):
                    given[attr] = (node, inner)
        saved, self.frame = self.frame, (parent if parent != self.scene else None)
        try:
            for f in pre:
                f(obj)
            self.shape_attrs(obj, given, absent, form.pos, scope, specs)
        finally:
            self.frame = saved
        for item, inner in members:
            self.shape(item, i, inner, down)
        return i

    def shape_attrs(
        self, obj: Obj, given: dict, absent: bool, pos: Pos, scope: dict, specs: dict
    ) -> None:
        for attr, spec in specs.items():
            if attr in ("x", "y") and "pos" in given:
                continue
            node, inner = given.get(attr, (None, scope))
            at = _maybe(spec.type) if absent else spec.type
            obj.attrs[attr] = self.place(at, node, pos, attr, spec.default, inner)
        if "pos" in given:
            node, inner = given["pos"]
            point = self.expr(node, _maybe(POINT) if absent else POINT, inner)
            for k, attr in enumerate(("x", "y")):
                at = _maybe(REAL) if absent else REAL
                obj.attrs[attr] = self.settle(at, _part(point, k), attr, node.pos)
        if absent:
            for attr, place in obj.attrs.items():
                if not _may_be_none(_value_type(place)):
                    place.type = specs[attr].type

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
        inner = _inner(t)
        if isinstance(inner, Refine):
            broken = tuple(
                c for c in inner.constraints if c[0] in COMPARE and not _range_within(e.range, c)
            )
            if broken and not _may_be_none(t):
                raise CompileError(f"{what} may break {_show(broken[0])}", pos)
            if broken:
                e = Expr("check", _maybe(e.type), (e, broken), e.deps, e.range)
        return Place(t, expr=e)

    def default(self, t: Type, pos: Pos) -> object:
        """The value a type has when none is given (reference.md, "Defaults")."""
        if isinstance(t, Maybe):
            return None
        base, cons = (t.base, t.constraints) if isinstance(t, Refine) else (t, ())
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
        if e.type == RECURSING:
            return e
        # A constraint is checked on the value (known) or its range (settle), not on its type.
        target = _loose(expected) if expected is not None else None
        if target is not None and not fits(_loose(e.type), target):
            if _may_be_none(e.type) and not _may_be_none(target):
                raise CompileError(
                    "this value may be none: give it a default with (or? value default)", node.pos
                )
            raise CompileError(f"expected {expected}, got {e.type}", node.pos)
        narrowed = _inner(expected) if expected is not None else None
        if e.known and e.value is not None and isinstance(narrowed, Refine):
            for c in narrowed.constraints:
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
        if isinstance(node, Form) and not node.items:
            raise CompileError(
                "() is an empty list of parameters or bindings, not a value", node.pos
            )
        if isinstance(node, Form):
            return self.form(node, expected, scope)
        raise CompileError(f"unexpected {type(node).__name__}", node.pos)

    def literal(self, node: Node, expected: Type | None) -> Expr:
        if isinstance(node, NoneLit) and expected is None:
            return _known(NONE, None)
        place = _loose(expected) if expected is not None else None
        try:
            t = literal_type(node, place)
        except TypeError_ as e:
            raise CompileError(str(e), node.pos) from None
        if isinstance(node, NoneLit):
            return _known(t, None)
        # A literal that is not none has the type of its place's other values.
        t = _inner(t)
        value = node.value
        if isinstance(value, (int, float, Fraction)) and abs(value) > LIMIT:
            raise CompileError(f"{value} is beyond ±10^150, the limit of every number", node.pos)
        if t == COLOR or (isinstance(t, Maybe) and t.inner == COLOR):
            value = parse_color(node.value)
        return _known(t, value)

    def list_literal(self, node: ListLit, expected: Type | None, scope: dict) -> Expr:
        place = expected.base if isinstance(expected, Refine) else expected
        if isinstance(place, Maybe):
            place = place.inner
        if place == POINT:
            items = [self.expr(i, Maybe(REAL), scope) for i in node.items]
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
                wider = _widen(t, e.type)
                if wider is None:
                    raise CompileError(f"a list holds one type, but has {t} and {e.type}", node.pos)
                t = wider
            if t == NONE:
                raise CompileError("a list of only none needs its type: write list[T]", node.pos)
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
            if e.known and e.value is None:
                return _known(Maybe(STRING), None)
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
        t = Maybe(STRING) if any(_may_be_none(e.type) for e in exprs) else STRING
        return Expr("format", t, tuple(merged), frozenset().union(*(e.deps for e in exprs)))

    def name(self, node: Name, scope: dict) -> Expr:
        first = node.parts[0]
        if not isinstance(first, str):
            raise CompileError("expected a name", node.pos)
        e = self.lookup(first, scope, node.pos)
        for part in node.parts[1:]:
            e = self.part(e, part, scope, node.pos)
        return e

    def expect(self, e: Expr, t: Type, pos: Pos) -> Expr:
        if not fits(_loose(e.type), _loose(t)):
            raise CompileError(f"expected {t}, got {e.type}", pos)
        return e

    def lookup(self, name: str, scope: dict, pos: Pos) -> Expr:
        if name in scope:
            v = scope[name]
            # A variant's body reads its parameters from an object made after its scope.
            return v() if callable(v) else v
        if self.bodies:
            body = self.bodies[-1]
            if name == "self":
                return self.read(body["id"], None)
            if name in body["names"]:
                return self.read(body["names"][name], None)
            if name in body["attrs"]:
                return self.read(body["id"], name)
        if name == "self":
            raise CompileError("self is used only in a motif's body", pos)
        if name in self.model.funcs:
            fid = self.model.funcs[name]
            f = self.model.functions[fid]
            t = FuncT(tuple(p.type for p in f.params), f.result)
            return Expr("func", t, (fid, ()), f.deps)
        if name in self.model.names:
            return self.read(self.model.names[name], None)
        raise CompileError(f"unknown name '{name}'", pos)

    def read(self, i: int, attr: str | None) -> Expr:
        obj = self.model.objects[i]
        moves: frozenset = frozenset()
        if obj.kind == "variable" and attr is None:
            place = obj.value
        else:
            if attr is None:
                return Expr("obj", obj.type, (i,))
            if attr not in obj.attrs:
                raise CompileError(f"a {obj.kind} has no attribute '{attr}'", obj.pos)
            place = obj.attrs[attr]
            if obj.kind in SHAPE_ATTRS or (obj.kind == "instance" and attr in INSTANCE_ATTRS):
                moves = self.moves(i)
        t = _maybe(place.type) if isinstance(obj.type, Maybe) else place.type
        if not place.bound and _is_const(place.type):
            return _known(t, place.value)
        deps = frozenset({(i, attr)}) | moves
        return Expr("read", t, (i, attr, self.frame), deps, _type_range(t))

    def moves(self, i: int) -> frozenset:
        """The translate and transform places a read of shape i converts through: its own and
        its containers', up to the one the reading expression sits in (reference.md,
        "Coordinates")."""
        shared = set()
        j = None if self.frame == "caller" else self.frame
        while j is not None and j != self.scene:
            shared.add(j)
            j = self.model.objects[j].parent
        out = set()
        j = i
        while j is not None and j != self.scene and j not in shared:
            out |= {(j, "translate"), (j, "transform")}
            # An instance's x and y move its frame, before its translate.
            if self.model.objects[j].kind == "instance":
                out |= {(j, "x"), (j, "y")}
            j = self.model.objects[j].parent
        return frozenset(out)

    def part(self, e: Expr, part, scope: dict, pos: Pos) -> Expr:
        if e.known and e.value is None:
            return e
        r = self.part_of(e, part, scope, pos)
        if _may_be_none(e.type) and not _may_be_none(r.type):
            return replace(r, type=_maybe(r.type))
        return r

    def has_attr(self, e: Expr, name) -> bool:
        if e.op == "obj":
            return name in self.attr_names(e.args[0])
        if e.op == "member":
            return name in self.type_attrs(_inner(e.type), e.args[2])
        return _base(_inner(e.type)) == POINT and name in ("x", "y")

    def attr_names(self, i: int) -> set:
        obj = self.model.objects[i]
        names = set(obj.attrs)
        if obj.kind in ("group", "scene"):
            names |= {"length", "members"}
        if "x" in obj.attrs or obj.kind in CORNERS:
            names |= {"x", "y", "pos"}
        if obj.kind == "instance":
            names |= {self.model.objects[m].name for m in obj.members} - {None}
        if obj.kind == "group" and obj.members:
            names |= set.intersection(*(self.attr_names(m) for m in obj.members)) - {"members"}
        return names

    def type_attrs(self, t: Type, candidates: tuple) -> set:
        """What a member of type t, one of candidates, may be read for (type-system.md, 6)."""
        if t == Interface("positioned"):
            return {"x", "y", "pos"}
        if t == Interface("shape"):
            return {"translate", "transform"}
        return self.attr_names(candidates[0]) if candidates else set()

    def common(self, ids: list[int]) -> Type:
        """The type where members meet: theirs when they share it, or else the most specific
        interface all of them satisfy."""
        types = [self.model.objects[m].type for m in ids]
        inner = [_inner(t) for t in types]
        if inner and all(t == inner[0] for t in inner):
            c = inner[0]
        elif inner and all(fits(t, Interface("positioned")) for t in inner):
            c = Interface("positioned")
        else:
            c = Interface("shape")
        return Maybe(c) if any(isinstance(t, Maybe) for t in types) else c

    def obj_attr(self, i: int, name: str, pos: Pos) -> Expr:
        obj = self.model.objects[i]
        if obj.kind in ("group", "scene") and name == "length":
            return _known(INT, len(obj.members))
        if obj.kind in ("group", "scene") and name == "members":
            items = tuple(self.read(m, None) for m in obj.members)
            return Expr("list", ListT(self.common(obj.members)), items)
        if name == "pos" and "pos" in self.attr_names(i):
            return _gather(POINT, [self.obj_attr(i, "x", pos), self.obj_attr(i, "y", pos)])
        if obj.kind in CORNERS and name in ("x", "y"):
            k = 0 if name == "x" else 1
            ends = [_part(self.read(i, c), k) for c in CORNERS[obj.kind]]
            return self.arith(pos, "/", [self.arith(pos, "+", ends), _known(INT, len(ends))])
        if name in obj.attrs:
            return self.read(i, name)
        if obj.kind == "instance":
            for m in obj.members:
                if self.model.objects[m].name == name:
                    return self.read(m, None)
        if obj.kind == "group":
            if not obj.members or name not in self.attr_names(i):
                raise CompileError(f"every member of {obj.name} must have '{name}'", pos)
            reads = [self.obj_attr(m, name, pos) for m in obj.members]
            t = _join_all([r.type for r in reads], pos)
            deps = frozenset().union(*(r.deps for r in reads))
            return Expr("spread", ListT(t), (Expr("obj", obj.type, (i,)), name), deps)
        raise CompileError(f"a {obj.kind} has no attribute '{name}'", pos)

    def part_of(self, e: Expr, part, scope: dict, pos: Pos) -> Expr:
        if isinstance(part, str):
            if e.op == "obj":
                return self.obj_attr(e.args[0], part, pos)
            held = self.held(e)
            if held is not None:
                e = Expr("member", e.type, (e, None, held), e.deps)
            if e.op == "member":
                candidates = e.args[2]
                common = _inner(e.type)
                if part not in self.type_attrs(common, candidates):
                    raise CompileError(f"a {common} has no attribute '{part}'", pos)
                reads = [self.obj_attr(m, part, pos) for m in candidates]
                t = _join_all([r.type for r in reads], pos)
                deps = e.deps.union(*(r.deps for r in reads))
                return Expr("part", t, (e, part), deps, _type_range(t))
            if _base(_inner(e.type)) == POINT and part in ("x", "y"):
                return _part(e, 0 if part == "x" else 1)
            raise CompileError(f"a {e.type} has no attribute '{part}'", pos)
        index = self.expr(part, None, scope)
        if e.op == "obj" and self.model.objects[e.args[0]].kind in ("group", "scene"):
            return self.member(e.args[0], index, pos)
        if not fits(_loose(index.type), INT):
            raise CompileError(f"a position is an int, got {index.type}", pos)
        whole = _base(_inner(e.type))
        if isinstance(whole, ListT) or whole == POINT:
            item = REAL if whole == POINT else whole.item
            n = _length(e)
            # A fixed position on a list of known length never gives none.
            if index.known and n is not None:
                k = index.value
                if not -n <= k < n:
                    raise CompileError(f"position {k} is out of range", pos)
                if e.known:
                    return _known(item, e.value[k])
                if e.op == "list":
                    return e.args[k]
            else:
                item = _maybe(item)
            return Expr("part", item, (e, index), e.deps | index.deps, _type_range(item))
        raise CompileError(f"a {e.type} has no items", pos)

    def held(self, e: Expr) -> tuple | None:
        """The shapes a variable typed with a shape or an interface may hold."""
        if e.op != "read" or e.args[1] is not None:
            return None
        if not isinstance(_core(e.type), (ShapeT, Interface)):
            return None
        place = self.model.objects[e.args[0]].value
        if place.bound and place.expr.op == "obj":
            return (place.expr.args[0],)
        return None

    def member(self, i: int, index: Expr, pos: Pos) -> Expr:
        """A member of a group or the scene, by position or name."""
        obj = self.model.objects[i]
        ids = obj.members
        names = [self.model.objects[m].name for m in ids]
        key = _core(index.type)
        if key not in (INT, STRING):
            raise CompileError(f"a member is found by an int or a string, got {index.type}", pos)
        if index.known:
            k = index.value
            if key == STRING:
                if k not in names:
                    raise CompileError(f"a {obj.kind} has no member '{k}'", pos)
                return self.read(ids[names.index(k)], None)
            if not -len(ids) <= k < len(ids):
                raise CompileError(f"position {k} is out of range", pos)
            return self.read(ids[k], None)
        # A key known only while drawing may miss, unless every choice of its type is a name.
        choices = _choices(index.type)
        safe = choices is not None and all(c in names for c in choices)
        t = self.common(ids)
        e = Expr("obj", obj.type, (i,))
        return Expr("member", t if safe else _maybe(t), (e, index, tuple(ids)), index.deps)

    def form(self, node: Form, expected: Type | None, scope: dict) -> Expr:
        head = _head(node)
        args = node.items[1:]
        if head is not None and head not in SPECIAL:
            if head in scope:
                local = self.lookup(head, scope, node.pos)
                if isinstance(_core(local.type), FuncT):
                    return self.apply(local, node, scope)
            elif head in self.model.funcs:
                return self.call(self.model.funcs[head], node, scope)
        if head == "fn":
            return self.fn(node, expected, scope)
        if head == "if":
            if len(args) != 3:
                raise CompileError("if takes a condition and two branches", node.pos)
            c = self.expr(args[0], BOOL, scope)
            # Branches may be none; the place the if reaches decides whether that is allowed.
            branch = _maybe(expected) if expected is not None else None
            a, b = (self.expr(x, branch, scope) for x in args[1:])
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
            # A bare name is an attribute when whole has one by that name; else it is a value.
            if isinstance(y, Name) and len(y.parts) == 1:
                name = y.parts[0]
                unknown = name not in scope and name not in self.model.names
                if self.has_attr(whole, name) or (unknown and whole.op == "obj"):
                    return self.part(whole, name, scope, node.pos)
            return self.part(whole, y, scope, node.pos)
        if head == "abs":
            (a,) = self.args(node, 1)
            return self.abs(node, self.expr(a, None, scope))
        if head == "or?":
            return self.or_default(node, expected, scope)
        if head in ("none?", "some?"):
            (a,) = self.args(node, 1)
            e = self.expr(a, None, scope)
            if e.known:
                return _known(BOOL, (e.value is None) == (head == "none?"))
            if not _may_be_none(e.type):
                return _known(BOOL, head == "some?")
            return Expr(head, BOOL, (e,), e.deps)
        if head == "somes":
            (a,) = self.args(node, 1)
            e = self.expr(a, None, scope)
            whole = _base(_inner(e.type))
            if not isinstance(whole, ListT) or _may_be_none(e.type):
                raise CompileError(f"somes takes a list, got {e.type}", node.pos)
            t = ListT(_inner(whole.item))
            if e.known:
                return _known(t, [v for v in e.value if v is not None])
            return Expr("somes", t, (e,), e.deps)
        if head in ARITH:
            return self.arith(node.pos, head, [self.expr(x, None, scope) for x in args])
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
        branch = _maybe(expected) if expected is not None else None
        for clause in reversed(clauses):
            if not isinstance(clause, Form) or len(clause.items) != 2:
                raise CompileError("a cond clause is (test value)", clause.pos)
            v = self.expr(clause.items[1], branch, scope)
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

    def arith(self, pos: Pos, op: str, args: list[Expr]) -> Expr:
        if not args or (op in ("/", "^", "mod") and len(args) != 2):
            raise CompileError(
                f"{op} takes {'two' if op in ('/', '^', 'mod') else 'some'} numbers", pos
            )
        if any(a.type == RECURSING for a in args):
            return Expr(op, RECURSING, tuple(args))
        numbers = [a for a in args if a.type != NONE]
        for a in numbers:
            if _core(a.type) not in NUMBERS:
                raise CompileError(f"{op} takes numbers, got {a.type}", pos)
        if not numbers:
            raise CompileError(f"{op} takes numbers, got none", pos)
        t = max((_core(a.type) for a in numbers), key=NUMBERS.index)
        if op == "/" and t == INT:
            t = RATIO
        if op == "^":
            t = _power_type(*args)
        if any(a.known and a.value is None for a in args):
            return _known(Maybe(t), None)
        if all(a.known for a in args):
            return _known(t, _fold_number(op, [a.value for a in args], pos))
        ranges = [a.range for a in args]
        r = _range_of(op, ranges)
        undefined = any(_may_be_none(a.type) for a in args) or _may_be_undefined(op, args)
        if r is not None and (r[0] < -MAX_REAL or r[1] > MAX_REAL):
            undefined = True
            r = (max(r[0], -MAX_REAL), min(r[1], MAX_REAL))
        deps = frozenset().union(*(a.deps for a in args))
        return Expr(op, Maybe(t) if undefined else t, tuple(args), deps, r)

    def or_default(self, node: Form, expected: Type | None, scope: dict) -> Expr:
        x, d = self.args(node, 2)
        ex = self.expr(x, _maybe(expected) if expected is not None else None, scope)
        ed = self.expr(d, expected if expected is not None else _inner(ex.type), scope)
        if ex.known:
            return ed if ex.value is None else ex
        if not _may_be_none(ex.type):
            return ex
        t = _join(_inner(ex.type), ed.type, node.pos)
        return Expr("or?", t, (ex, ed), ex.deps | ed.deps, _union(ex.range, ed.range))

    def abs(self, node: Form, a: Expr) -> Expr:
        if a.type == RECURSING:
            return Expr("abs", RECURSING, (a,))
        base = _core(a.type)
        if base not in NUMBERS:
            raise CompileError(f"abs takes a number, got {a.type}", node.pos)
        t = REAL if base == COMPLEX else base
        if a.known and a.value is None:
            return _known(Maybe(t), None)
        if _may_be_none(a.type):
            t = Maybe(t)
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
        if RECURSING in (a.type, b.type):
            return Expr(op, BOOL, (a, b))
        if op in COMPARE:
            for e in (a, b):
                if e.type != NONE and _core(e.type) not in NUMBERS[:3]:
                    raise CompileError(f"{op} compares numbers, got {e.type}", node.pos)
            if any(e.known and e.value is None for e in (a, b)):
                return _known(Maybe(BOOL), None)
            t = Maybe(BOOL) if _may_be_none(a.type) or _may_be_none(b.type) else BOOL
        else:
            # Equality decides with none too: (= none none) is true, (= none 3) is false.
            ta, tb = _loose(_inner(a.type)), _loose(_inner(b.type))
            if NONE not in (ta, tb) and not (fits(ta, tb) or fits(tb, ta)):
                raise CompileError(
                    f"{op} compares two of one type, got {a.type} and {b.type}", node.pos
                )
            t = BOOL
        if a.known and b.known:
            return _known(t, _fold(op, [a.value, b.value]))
        return Expr(op, t, (a, b), a.deps | b.deps)


ARITH = {"+", "-", "*", "/", "^", "mod"}


def _known(t: Type, value) -> Expr:
    r = (
        (float(value), float(value))
        if isinstance(value, (int, float, Fraction)) and not isinstance(value, bool)
        else None
    )
    return Expr("lit", t, (value,), range=r, known=True, value=value)


def _locals(e) -> set:
    """The parameter names an expression reads."""
    if isinstance(e, Expr):
        own = {e.args[0]} if e.op == "local" else set()
        return own.union(*(_locals(a) for a in e.args))
    if isinstance(e, tuple):
        return set().union(*(_locals(a) for a in e))
    return set()


def _scoped(nodes, scope: dict) -> list:
    return [(n, scope) for n in nodes]


def _overlaps(attr: str, given: dict) -> bool:
    """Whether attr, or a place it writes (pos is x and y), is already in given."""
    places = {"x", "y"} if attr == "pos" else {attr}
    return any(a in given or (a in ("x", "y") and "pos" in given) for a in places)


def _dot(node: Node, attr: str) -> Form:
    """(. node attr), built by the compiler."""
    return Form((Name((".",), node.pos), node, Name((attr,), node.pos)), node.pos)


def _coordinates(attr: str, node: Node, scope: dict) -> dict:
    """A group's argument as defaults by place: pos becomes its x and its y, so a member or an
    inner group that gives only one of them still takes the other."""
    if attr != "pos":
        return {attr: (node, scope)}
    dot = Name((".",), node.pos)
    return {
        a: (Form((dot, node, IntLit(k, node.pos)), node.pos), scope) for k, a in enumerate("xy")
    }


def _choices(t: Type) -> tuple | None:
    t = _inner(t)
    if isinstance(t, Refine):
        return next((c[1] for c in t.constraints if c[0] == "one-of"), None)
    return None


def _join_all(types: list[Type], pos: Pos) -> Type:
    t = types[0]
    for u in types[1:]:
        t = _join(t, u, pos)
    return t


def _inner(t: Type) -> Type:
    return t.inner if isinstance(t, Maybe) else t


def _may_be_none(t: Type) -> bool:
    return isinstance(t, Maybe) or t == NONE


def _maybe(t: Type) -> Type:
    return t if _may_be_none(t) else Maybe(t)


def _core(t: Type) -> Type:
    """t without none and without constraints: what an operation checks its inputs against."""
    return _base(_inner(t))


def _loose(t: Type) -> Type:
    """t without constraints, which are checked on values and ranges, not types."""
    return Maybe(_base(t.inner)) if isinstance(t, Maybe) else _base(t)


def _value_type(place: Place) -> Type:
    return place.expr.type if place.bound else (NONE if place.value is None else place.type)


def _length(e: Expr) -> int | None:
    """A list's length when it is known when compiling (type-system.md, "Known lengths")."""
    if e.known and e.value is not None:
        return len(e.value)
    if e.op == "list":
        return len(e.args)
    t = _inner(e.type)
    if _base(t) == POINT:
        return 2
    if isinstance(t, Refine):
        return next((c[1] for c in t.constraints if c[0] == "length"), None)
    return None


def _widen(a: Type, b: Type) -> Type | None:
    """The narrowest type both a and b fit, or None."""
    if _inner(a) == RECURSING:
        return b
    if _inner(b) == RECURSING:
        return a
    if fits(a, b):
        return b
    if fits(b, a):
        return a
    if a == NONE:
        return _maybe(b)
    if b == NONE:
        return _maybe(a)
    if _may_be_none(a) or _may_be_none(b):
        inner = _widen(_inner(a), _inner(b))
        return Maybe(inner) if inner is not None else None
    return None


def _power_type(base: Expr, exp: Expr) -> Type:
    a, b = _core(base.type), _core(exp.type)
    if COMPLEX in (a, b):
        return COMPLEX
    if a == INT and b == INT:
        low = exp.value if exp.known else (exp.range[0] if exp.range else -1)
        return INT if low is not None and low >= 0 else RATIO
    return REAL


def _may_be_undefined(op: str, args: list[Expr]) -> bool:
    """Whether a partial operation's inputs' ranges reach a point where it is undefined."""
    if op in ("/", "mod"):
        r = args[1].range
        return r is None or r[0] <= 0 <= r[1]
    if op == "^":
        base, exp = args
        rb, re_ = base.range, exp.range
        if rb is None or re_ is None:
            return True
        if rb[0] <= 0 <= rb[1] and re_[0] < 0:
            return True
        if rb[0] < 0 and _core(exp.type) != INT:
            return True
        for x in rb:
            for y in re_:
                try:
                    if abs(math.pow(abs(x), y)) > MAX_REAL:
                        return True
                except (OverflowError, ZeroDivisionError, ValueError):
                    return True
    return False


def _fold_number(op: str, vals: list, pos: Pos):
    if op == "^":
        a, b = vals
        if a == 0 and b < 0:
            raise CompileError("undefined: 0 to a negative power", pos)
        if a < 0 and not float(b).is_integer():
            raise CompileError("undefined: a negative number to a power that is not an int", pos)
        if isinstance(a, (int, Fraction)) and isinstance(b, int) and b < 0:
            a = Fraction(a)
    try:
        v = _fold(op, vals)
    except ZeroDivisionError:
        raise CompileError("division by zero", pos) from None
    except OverflowError:
        raise CompileError("the result is too large for a real", pos) from None
    if isinstance(v, (int, float, Fraction)) and not math.isfinite(v):
        raise CompileError("the result is too large for a real", pos)
    if isinstance(v, (int, Fraction)) and abs(v) > MAX_REAL:
        raise CompileError("the result is too large for a real", pos)
    return v


def _gather(t: Type, items: list[Expr]) -> Expr:
    if any(_may_be_none(i.type) for i in items) and t == POINT:
        t = Maybe(POINT)
    if t == Maybe(POINT) and any(i.known and i.value is None for i in items):
        return _known(t, None)
    if all(i.known for i in items):
        v = [i.value for i in items]
        return _known(t, tuple(v) if t == POINT else v)
    return Expr("list", t, tuple(items), frozenset().union(*(i.deps for i in items)))


def _part(e: Expr, k: int) -> Expr:
    t = _maybe(REAL) if _may_be_none(e.type) else REAL
    if e.known:
        return _known(t, None if e.value is None else e.value[k])
    if e.op == "list":
        return e.args[k]
    return Expr("part", t, (e, _known(INT, k)), e.deps, UNBOUNDED)


def _base(t: Type) -> Type:
    return t.base if isinstance(t, Refine) else t


def _is_const(t: Type) -> bool:
    t = _inner(t)
    return isinstance(t, Refine) and ("const",) in t.constraints


def _type_range(t: Type) -> Range:
    t = _inner(t)
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
    t = _widen(a, b)
    if t is None:
        raise CompileError(f"the branches give {a} and {b}", pos)
    return t


def _union(a: Range, b: Range) -> Range:
    if a is None:
        return b
    if b is None:
        return a
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
    if op == "mod":
        # mod takes the divisor's sign, so it lies between 0 and the divisor.
        b = ranges[1]
        return (min(0.0, b[0]), max(0.0, b[1]))
    # Any other function gives its whole range (type-system.md, "What the compiler proves").
    return WHOLE


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
    if op == "=":
        return a == b
    if op == "!=":
        return a != b
    return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op] if None not in vals else None
