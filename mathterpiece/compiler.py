"""The compiler: reads parsed forms into a world model (docs/syntax.md, docs/type-system.md,
docs/reference.md). Every declaration follows one body rule, (head name? positional… item…), and
every expression is typed, with what it reads, its range, and its value when it is known."""

import math
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Context, Decimal
from fractions import Fraction
from typing import Literal, cast

from mathterpiece.builtins import (
    BUILTINS,
    CONSTANTS,
    SPECIAL_BUILTINS,
    Builtin,
    Undefined,
    compose,
)
from mathterpiece.colors import parse_color
from mathterpiece.model import (
    Attribute,
    Expr,
    FuncDef,
    Model,
    MotifDef,
    Obj,
    Param,
    Range,
    VariantDef,
)
from mathterpiece.nodes import (
    NOPOS,
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
    ANIMATION,
    BOOL,
    COLOR,
    COMPARE,
    COMPLEX,
    FONT,
    INT,
    NONE,
    NUMBERS,
    POINT,
    RATIO,
    REAL,
    SCENE,
    STRING,
    TRANSFORM,
    TRANSITION,
    ComponentT,
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
    "scene animation transition move in-order at-once when else true false none const self".split()
)
CONSTRAINT_HEADS = COMPARE | {"length", "one-of", "const"}
# The optional arguments of controls and listeners; the rest of their items are conditions.
WRITER_OPTIONS = {"animation", "label", "step", "buttons", "value", "when"}
# Every number lies within ±10^150 (type-system.md, "What the compiler proves").
LIMIT = 1e150
UNBOUNDED: tuple[float, float] = (-LIMIT, LIMIT)
# The result of a function whose body is being compiled for the first time: a recursive call
# has it, and the branch that does not recurse decides the real one.
RECURSING = Prim("recursing")
# Forms that are not calls, so a function of the same name never replaces them.
SPECIAL = {"if", "cond", "and", "or", "let", "name", ".", "fn", "repeat", "type-of", "as"}
# The components (reference.md, "Components"), declared at the top level only.
COMPONENTS = {"canvas", "readout", "slider", "button", "play", "toggle", "on-drag", "on-click"}
EASES = ("linear", "ease-in", "ease-out", "ease-in-out")
COLLECTION = {"map", "where", "sort", "reverse", "reduce", "sum", "count", "any", "all"}
# A computed result beyond the largest real overflows, which is undefined.
MAX_REAL = sys.float_info.max
WHOLE: tuple[float, float] = (-MAX_REAL, MAX_REAL)
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

UNIT = Refine(REAL, ((">=", 0), ("<=", 1)))
NON_NEGATIVE = Refine(REAL, ((">=", 0),))
PAINT = Maybe(COLOR)
HALIGN = Refine(STRING, (("one-of", ("start", "middle", "end")),))
VALIGN = Refine(STRING, (("one-of", ("top", "middle", "baseline", "bottom")),))


@dataclass(frozen=True)
class Argument:
    type: Type
    default: object


TRANSFORMS = {
    "translate": Argument(POINT, (0, 0)),
    "transform": Argument(TRANSFORM, IDENTITY),
}
PAINTED = {
    "fill": Argument(PAINT, "#000000ff"),
    "stroke": Argument(PAINT, None),
    "stroke-width": Argument(NON_NEGATIVE, 1),
    "opacity": Argument(UNIT, 1),
    "fill-opacity": Argument(UNIT, 1),
    "stroke-opacity": Argument(UNIT, 1),
}
POSITIONED = {"x": Argument(REAL, 0), "y": Argument(REAL, 0)}
# The attributes each built-in shape takes, with their defaults (reference.md).
SHAPE_ATTRS: dict[str, dict[str, Argument]] = {
    "circle": {**POSITIONED, **PAINTED, **TRANSFORMS, "r": Argument(NON_NEGATIVE, 1)},
    "rect": {
        **POSITIONED,
        **PAINTED,
        **TRANSFORMS,
        "width": Argument(REAL, 1),
        "height": Argument(REAL, 1),
        "rx": Argument(REAL, 0),
        "ry": Argument(REAL, 0),
    },
    "ellipse": {
        **POSITIONED,
        **PAINTED,
        **TRANSFORMS,
        "rx": Argument(REAL, 1),
        "ry": Argument(REAL, 1),
    },
    "line": {
        **PAINTED,
        **TRANSFORMS,
        "from": Argument(POINT, (0, 0)),
        "to": Argument(POINT, (1, 0)),
    },
    "triangle": {
        **PAINTED,
        **TRANSFORMS,
        "a": Argument(POINT, (0, 0)),
        "b": Argument(POINT, (1, 0)),
        "c": Argument(POINT, (0, 1)),
    },
    "text": {
        **POSITIONED,
        **PAINTED,
        **TRANSFORMS,
        "value": Argument(STRING, ""),
        "halign": Argument(HALIGN, "start"),
        "valign": Argument(VALIGN, "baseline"),
        "font": Argument(FONT, None),
    },
    "group": dict(TRANSFORMS),
}
# What a motif instance takes besides its parameters (reference.md, "The scene and shapes").
INSTANCE_ATTRS = {**POSITIONED, **PAINTED, **TRANSFORMS}
# The paint arguments a motif instance gives its members as defaults; opacity is its own.
INHERITED = ("fill", "stroke", "stroke-width", "fill-opacity", "stroke-opacity")
# A font's parts, their types and their defaults (reference.md, "Tokens" and "Defaults"); a
# family of None is the page's font. The style choices are the old code's (mtp-9mg).
FONT_STYLE = Refine(STRING, (("one-of", ("normal", "italic", "oblique")),))
FONT_PARTS = {
    "family": Argument(Maybe(STRING), None),
    "style": Argument(FONT_STYLE, "normal"),
    "weight": Argument(Refine(REAL, ((">=", 1), ("<=", 1000))), 400),
    "size": Argument(REAL, 16),
}
FONT_DEFAULT = {part: spec.default for part, spec in FONT_PARTS.items()}
# The attributes of values that are not objects (type-system.md, section 8).
VALUE_ATTRS = {
    COMPLEX: {"re": REAL, "im": REAL},
    COLOR: {"r": UNIT, "g": UNIT, "b": UNIT, "a": UNIT},
    STRING: {"length": INT},
    FONT: {part: spec.type for part, spec in FONT_PARTS.items()},
}
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
    assert isinstance(node, Form)
    # A comparison with two arguments is an expression; with one, a constraint.
    return head not in COMPARE or len(node.items) == 2


class _Compiler:
    def __init__(self):
        self.model = Model()
        self.scene: int | None = None
        # The container the expression being compiled sits in: a group, or None for the scene
        # and the top level. Reads convert through the transforms not shared with it.
        self.frame: int | Literal["caller"] | None = None
        # The names a repeat around the component being compiled gives it.
        self.cscope: dict = {}
        # True while compiling the scene's contents, which may never read page access.
        self.in_scene = False
        # The object and attribute whose attribute is being compiled, so a message can name them:
        # (name, the shape's type or None for a variable, attribute or None).
        self.where: tuple | None = None
        # The motif instances whose bodies are being compiled, innermost last: each with its
        # id, its members' names, its parameters and bound variables, and the path its
        # members are named by (None inside an anonymous instance).
        self.bodies: list[dict] = []
        # For each function body being compiled, what it reads through its parameters.
        self.reads: list[dict[str, set]] = []
        # The attributes of each motif and variant, by type, taken from its trial instance.
        self.shape_types: dict[str, dict[str, Type]] = {}
        # How many function bodies are being compiled again to fold a call.
        self.folding = 0
        # Each rand drawn so far, after repeat and motif instances are expanded.
        self.rand_sites = 0

    def run(self, forms: tuple[Form, ...]) -> Model:
        for form, scope in self.expand(forms, {}):
            self.top(form, scope)
        # A named transition no move ever used still needs its ends compiled.
        for i, obj in enumerate(self.model.objects):
            if obj.kind == "transition" and obj.data.get("end") is None:
                self.type_ends(i, None, obj.pos)
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
        if head == "transition":
            self.transition(form, {}, top=True)
            return
        if head == "animation":
            self.animation(form, {}, named=True)
            return
        if head in COMPONENTS:
            return self.component(form, scope)
        if self.shape_kind(form):
            raise CompileError("a shape is declared only inside the scene", form.pos)
        self.variable(form, None, "scene", scope)

    def name_of(self, form: Form, scope: dict | None = None) -> tuple[str | None, Pos]:
        if len(form.items) < 2:
            raise CompileError("a declaration needs a name", form.pos)
        node = form.items[1]
        if isinstance(node, StrLit):
            raise CompileError("a name is written bare, not in quotes", node.pos)
        # A form given none as its name, or written (head_ …), has no name.
        if isinstance(node, NoneLit):
            return None, node.pos
        if _head(node) == "name":
            assert isinstance(node, Form)
            name = self.built_name(node, scope or {})
        elif isinstance(node, Name) and len(node.parts) == 1 and isinstance(node.parts[0], str):
            name = node.parts[0]
        else:
            raise CompileError("expected a name", node.pos)
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
        if isinstance(form.items[0], Name) and form.items[0].parts == ("font",):
            return self.font_variable(form, parent, access, scope)
        name, pos, t, node = self.declared(form, scope)
        if isinstance(_core(t), FuncT):
            raise CompileError("a variable cannot hold a function", pos)
        if node is not None and self.shape_kind(node):
            # (shape sel (circle c …)) declares the circle where the variable is, and holds it.
            assert isinstance(node, Form)
            if parent is None:
                raise CompileError("a shape is declared only inside the scene", node.pos)
            shape = self.read(self.shape(node, parent, scope), None)
            attribute = self.settle(t, self.expect(shape, t, node.pos), "the value", node.pos)
            self.add(Obj("variable", name, t, access, {"value": attribute}, parent=parent, pos=pos))
            return
        saved, self.where = self.where, (name, None, None)
        try:
            attribute = self.attribute(t, node, form.pos, "the value", scope=scope)
        finally:
            self.where = saved
        t = self.keep_length(t, attribute)
        access = self.access_of(attribute.deps)[0]
        self.add(Obj("variable", name, t, access, {"value": attribute}, parent=parent, pos=pos))

    def keep_length(self, t: Type, attribute: Attribute) -> Type:
        """A bound list always equals its expression, so it keeps that expression's length."""
        inner = _inner(t)
        has_length = isinstance(inner, Refine) and any(c[0] == "length" for c in inner.constraints)
        if attribute.expr is not None and isinstance(_core(t), ListT) and not has_length:
            n = _length(attribute.expr)
            if n is not None:
                t = _with_length(t, n)
                attribute.type = t
        return t

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
        f = FuncDef(name, params, RECURSING, pos=pos, source=form.items[3])
        self.model.functions.append(f)
        self.model.funcs[name] = fid
        # A recursive call gives RECURSING until the body's type is known; compile again with
        # that type until it no longer changes, since it may broaden (int, then ratio).
        for _ in range(len(NUMBERS) + 2):
            body, reads = self.function_body(params, form.items[3])
            if _inner(body.type) == RECURSING:
                raise CompileError(f"{name} has no base case: every branch calls {name}", pos)
            if body.type == f.result:
                break
            f.result = body.type
        f.body, f.deps = body, body.deps
        f.reads = {p.name: frozenset(reads[p.name]) for p in params if p.name in reads}

    def function_body(self, params, node: Node, expected=None, outer=None):
        """The body, and what it reads through each name it does not declare itself."""
        scope = dict(outer or {})
        for p in params:
            scope[p.name] = Expr("local", p.type, (p.name,), range=_type_range(p.type))
        # A read inside a function uses the frame of the attribute that called it.
        saved, self.frame = self.frame, "caller"
        self.reads.append({})
        try:
            return self.expr(node, expected, scope), self.reads[-1]
        finally:
            self.frame = saved
            self.reads.pop()

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
        if f.body is not None and all(self.foldable(a) for a in args):
            folded = self.fold_call(fid, args)
            if folded is not None:
                return _known(t, folded.value)
        r = f.body.range if f.body is not None else _type_range(t)
        for p, a in zip(f.params, args, strict=True):
            for path in f.reads.get(p.name, ()):
                deps |= self.reads_through(a, path)
        return Expr("call", t, (fid, *args), deps | f.deps, r)

    def reads_through(self, e: Expr, path: str) -> frozenset:
        """The attributes a function reads when it reads path through an argument e."""
        if path.startswith("[]."):
            items = self.items_of(e)
            if items is None:
                self.note(e, path)
                return frozenset()
            objs = [Expr("obj", self.model.objects[m].type, (m,)) for m in items]
            return frozenset().union(*(self.reads_through(o, path[3:]) for o in objs))
        objs = self.objects_in(e)
        if objs is None:
            self.note(e, path)
            return frozenset()
        out: set = set()
        for m in objs:
            if path in self.attr_names(m):
                out |= self.obj_attr(m, path, NOPOS).deps
        return frozenset(out)

    def note(self, e: Expr, path: str) -> None:
        """Record, for the function being compiled, a read of path through a parameter."""
        if not self.reads:
            return
        if e.op == "local":
            self.reads[-1].setdefault(e.args[0], set()).add(path)
        elif e.op == "part" and not isinstance(e.args[1], str):
            self.note(e.args[0], "[]." + path)
        elif e.op in ("where", "sort", "reverse", "somes"):
            self.note(e.args[0], path)
        elif e.op == "if":
            self.note(e.args[1], path)
            self.note(e.args[2], path)

    def objects_in(self, e: Expr) -> tuple | None:
        """The shapes e may be, when they are known when compiling."""
        if e.op == "obj":
            return (e.args[0],)
        if e.op == "member":
            return e.args[2]
        if e.op == "if":
            a, b = self.objects_in(e.args[1]), self.objects_in(e.args[2])
            return None if a is None or b is None else a + b
        if e.op == "part" and not isinstance(e.args[1], str):
            return self.items_of(e.args[0])
        return self.held(e)

    def items_of(self, e: Expr) -> tuple | None:
        """The shapes a collection may hold, when they are known when compiling."""
        if e.op == "obj" and self.model.objects[e.args[0]].kind in ("group", "scene"):
            return tuple(self.model.objects[e.args[0]].members)
        if e.op == "list":
            parts = [self.objects_in(a) for a in e.args]
            return None if any(p is None for p in parts) else sum(cast("list[tuple]", parts), ())
        if e.op in ("where", "sort", "reverse", "somes"):
            return self.items_of(e.args[0])
        return None

    def arguments(self, params, given, scope: dict, pos: Pos) -> tuple[list, frozenset, bool]:
        """Each argument, or what a left-out parameter takes. An argument that may be none
        given to a parameter that does not accept it makes the call none (type-system.md 5.c);
        one given to a constrained parameter must be proved to fit (5.b)."""
        args, maybe = [], False
        for k, p in enumerate(params):
            if k < len(given):
                accepts = _may_be_none(p.type)
                e = self.expr(given[k], p.type if accepts else _maybe(p.type), scope)
                self.check_sequence(e, p.type, given[k].pos)
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

    def check_sequence(self, e: Expr, t: Type, pos: Pos) -> None:
        """A group given as sequence[T]: its members' common type must fit T (type-system 6)."""
        t = _inner(t)
        if not (isinstance(t, Interface) and t.name == "sequence" and t.of is not None):
            return
        items = self.items_of(e)
        if items is not None and e.op == "obj":
            common = self.common(list(items))
            if not fits(_loose(common), _loose(t.of)):
                raise CompileError(f"expected {t}, got a group of {common}", pos)

    def apply(self, fexpr: Expr, node: Form, scope: dict) -> Expr:
        ft = _core(fexpr.type)
        assert isinstance(ft, FuncT)
        given = node.items[1:]
        if len(given) != len(ft.params):
            n = len(ft.params)
            raise CompileError(f"this function takes {n} argument{'s' * (n != 1)}", node.pos)
        params = tuple(Param(f"argument {k + 1}", t) for k, t in enumerate(ft.params))
        args, deps, maybe = self.arguments(params, given, scope, node.pos)
        t = _maybe(ft.result) if maybe else ft.result
        if self.foldable(fexpr) and all(self.foldable(a) for a in args):
            folded = self.call_value(fexpr, args)
            if folded is not None:
                return _known(t, folded.value)
        return Expr("apply", t, (fexpr, *args), deps | fexpr.deps, _type_range(t))

    def foldable(self, e: Expr) -> bool:
        """Known when compiling: a value, or a function whose captured names are known."""
        if e.known or e.op == "builtinfunc":
            return True
        if e.op != "func":
            return False
        f = self.model.functions[e.args[0]]
        return all(_get(f.scope, n).known for n in e.args[1])

    def call_value(self, f: Expr, args: list) -> Expr | None:
        """A function value called on known arguments, folded."""
        if f.op == "builtinfunc":
            b = BUILTINS[f.args[0]]
            return self.apply_builtin(f.args[0], b, args, frozenset(), False, NOPOS)
        return self.fold_call(f.args[0], args)

    def builtin(self, node: Form, head: str, scope: dict) -> Expr:
        """A call of a built-in function (reference.md, "Functions")."""
        given = node.items[1:]
        if head in SPECIAL_BUILTINS:
            return self.special_builtin(node, head, given, scope)
        b = BUILTINS[head]
        self.count(head, given, len(b.params), len(b.params), node.pos)
        params = tuple(Param(f"argument {k + 1} of {head}", t) for k, t in enumerate(b.params))
        args, deps, maybe = self.arguments(params, given, scope, node.pos)
        return self.apply_builtin(head, b, args, deps, maybe, node.pos)

    def count(self, head: str, given, low: int, high: int, pos: Pos) -> None:
        if not low <= len(given) <= high:
            n = f"{low}" if low == high else f"{low} to {high}"
            raise CompileError(f"{head} takes {n} argument{'s' * (high != 1)}", pos)

    def apply_builtin(self, head: str, b: Builtin, args, deps, maybe: bool, pos: Pos) -> Expr:
        if any(a.known and a.value is None for a in args):
            return _known(Maybe(b.result), None)
        if all(a.known for a in args):
            return _known(b.result, self.fold_builtin(head, b.fold, [a.value for a in args], pos))
        ranges = [a.range if a.range is not None else UNBOUNDED for a in args]
        undefined = b.undefined is not None and b.undefined(ranges)
        r = cast(Range, b.range(ranges) if callable(b.range) else b.range)
        t = Maybe(b.result) if maybe or undefined else b.result
        return Expr(head, t, tuple(args), deps, r)

    def fold_builtin(self, head: str, fold, values: list, pos: Pos):
        try:
            return fold(*values)
        except (Undefined, ValueError, ZeroDivisionError, OverflowError):
            shown = ", ".join(_value_str(v) for v in values)
            raise CompileError(f"{head} is undefined at {shown}", pos) from None

    def special_builtin(self, node: Form, head: str, given, scope: dict) -> Expr:
        """The built-ins whose arguments vary in number or type."""
        pos = node.pos
        if head == "rand":
            self.count(head, given, 0, 2, pos)
            if len(given) == 1:
                raise CompileError("rand takes no arguments, or lo and hi", pos)
            if self.reads:
                raise CompileError("rand inside a function is a compile error for now", pos)
            bounds = [self.expr(g, REAL, scope) for g in given]
            site, self.rand_sites = self.rand_sites, self.rand_sites + 1
            r = (0.0, 1.0)
            if bounds and all(b.known for b in bounds):
                r = (float(bounds[0].value), float(bounds[1].value))
            elif bounds:
                r = WHOLE
            deps = frozenset().union(*(b.deps for b in bounds))
            return Expr("rand", REAL, (site, *bounds), deps, r)
        if head == "round":
            self.count(head, given, 1, 2, pos)
            params = (Param("x", REAL), Param("decimals", INT))[: len(given)]
            b = Builtin(
                tuple(p.type for p in params), INT if len(given) == 1 else REAL, _round, UNBOUNDED
            )
        elif head == "log":
            self.count(head, given, 1, 2, pos)
            params = (Param("x", REAL), Param("base", REAL))[: len(given)]
            b = Builtin(tuple(p.type for p in params), REAL, _log, UNBOUNDED, _log_undefined)
        elif head in ("min", "max"):
            return self.extreme(node, head, given, scope)
        elif head == "lerp":
            self.count(head, given, 3, 3, pos)
            first = self.expr(given[0], None, scope)
            point = isinstance(given[0], ListLit) or _core(first.type) == POINT
            t = POINT if point else REAL
            params = (Param("a", t), Param("b", t), Param("t", REAL))
            b = Builtin((t, t, REAL), t, _lerp, UNBOUNDED if t == REAL else None)
        elif head == "scale":
            self.count(head, given, 1, 2, pos)
            params = tuple(Param(n, REAL) for n in ("sx", "sy")[: len(given)])
            b = Builtin(tuple(p.type for p in params), TRANSFORM, _scale, None)
        else:  # transform: their composition
            if not given:
                raise CompileError("transform takes one transform or more", pos)
            params = tuple(Param(f"transform {k + 1}", TRANSFORM) for k in range(len(given)))
            b = Builtin(tuple(p.type for p in params), TRANSFORM, compose, None)
        args, deps, maybe = self.arguments(params, given, scope, pos)
        return self.apply_builtin(head, b, args, deps, maybe, pos)

    def extreme(self, node: Form, head: str, given, scope: dict) -> Expr:
        """min and max: of reals, any count, where a list of reals counts as its items (as the
        old code spread a group's attribute into the call; mtp-b80)."""
        pick = min if head == "min" else max
        if not given:
            raise CompileError(f"{head} takes one real or more", node.pos)
        args, maybe, ranges, may_be_empty = [], False, [], True
        for g in given:
            e = self.expr(g, None, scope)
            core = _core(e.type)
            item = core.item if isinstance(core, ListT) else e.type
            if _may_be_none(e.type) and not isinstance(core, ListT):
                maybe = True
            elif _may_be_none(item) or _core(item) not in NUMBERS[:3]:
                raise CompileError(f"{head} takes reals or lists of reals, got {e.type}", g.pos)
            if isinstance(core, ListT):
                if _length(e) != 0 and _length(e) is not None:
                    may_be_empty = False
                ranges.append(_type_range(item) if not e.known or not e.value else e.range)
            else:
                may_be_empty = False
                ranges.append(e.range)
            args.append(e)
        if all(a.known for a in args) and not maybe:
            nums = [v for a in args for v in (a.value if isinstance(a.value, list) else [a.value])]
            if not nums:
                raise CompileError(f"{head} of an empty list is undefined", node.pos)
            return _known(REAL, pick(nums))
        rs = [r if r is not None else UNBOUNDED for r in ranges]
        for a in args:
            if a.known and isinstance(a.value, list) and a.value:
                rs.append((float(min(a.value)), float(max(a.value))))
        r = (pick(x[0] for x in rs), pick(x[1] for x in rs))
        t = Maybe(REAL) if maybe or may_be_empty else REAL
        deps = frozenset().union(*(a.deps for a in args))
        return Expr(head, t, tuple(args), deps, r)

    def itemwise(self, pos: Pos, op: str, args: list) -> Expr:
        """+ - * on points, or on lists of numbers of equal known length, item by item."""
        if op not in ("+", "-", "*"):
            raise CompileError(f"{op} takes numbers, not points or lists", pos)
        kinds = {_core(a.type) == POINT for a in args}
        if len(kinds) != 1 or not all(
            _core(a.type) == POINT or isinstance(_core(a.type), ListT) for a in args
        ):
            raise CompileError(f"{op} takes all points or all lists, item by item", pos)
        lengths = {_length(a) for a in args}
        if len(lengths) != 1 or None in lengths:
            raise CompileError(f"{op} takes lists of equal length, known when compiling", pos)
        if kinds == {True}:
            t = POINT
        else:
            items = [_core(cast(ListT, _core(a.type)).item) for a in args]
            if not all(i in NUMBERS for i in items):
                raise CompileError(f"{op} takes lists of numbers", pos)
            t = ListT(max(items, key=NUMBERS.index))
        maybe = any(_may_be_none(a.type) for a in args)
        if all(a.known for a in args) and not maybe:
            columns = zip(*(a.value for a in args), strict=True)
            vals = [_fold_number(op, list(c), pos) for c in columns]
            return _known(t, tuple(vals) if t == POINT else vals)
        deps = frozenset().union(*(a.deps for a in args))
        return Expr(op, Maybe(t) if maybe else t, tuple(args), deps)

    def fold_call(self, fid: int, args: list) -> Expr | None:
        """The call's value, compiling the body again with its known arguments, or None when
        the body still needs something known only while drawing."""
        f = self.model.functions[fid]
        if f.source is None:
            return None
        scope = dict(f.scope)
        scope.update({p.name: a for p, a in zip(f.params, args, strict=True)})
        functions = len(self.model.functions)
        saved, self.frame = self.frame, "caller"
        self.folding += 1
        self.reads.append({})
        try:
            e = self.expr(f.source, None, scope)
        except RecursionError:
            return None
        finally:
            self.frame = saved
            self.folding -= 1
            self.reads.pop()
            del self.model.functions[functions:]
        return e if e.known else None

    def fold_each(self, f: Expr, item: Type, values: list) -> list | None:
        """f called on each value, when f and every result are known when compiling."""
        if not self.foldable(f):
            return None
        out = []
        for v in values:
            r = self.call_value(f, [_known(item, v)])
            if r is None:
                return None
            out.append(r.value)
        return out

    def fn(self, node: Form, scope: dict, hint=None, result=None) -> Expr:
        """(fn params body). hint holds the parameter types its attribute gives, and result the
        result type it expects, if any."""
        if len(node.items) != 3:
            raise CompileError("fn is (fn parameters body)", node.pos)
        pnode = node.items[1]
        if isinstance(pnode, Name):
            if hint is None or len(hint) != 1:
                raise CompileError(
                    "a bare parameter of fn needs its type from where the function is used:"
                    " write (fn (T name) …)",
                    pnode.pos,
                )
            assert isinstance(pnode.parts[0], str)
            params = (Param(pnode.parts[0], hint[0]),)
        else:
            params = self.params(pnode)
        body, reads = self.function_body(params, node.items[2], result, scope)
        fid = len(self.model.functions)
        own = {p.name for p in params}
        f = FuncDef(None, params, body.type, body, body.deps, node.pos, source=node.items[2])
        f.scope = dict(scope)
        f.reads = {n: frozenset(r) for n, r in reads.items() if n in own}
        self.model.functions.append(f)
        captured = tuple(sorted(_locals(body) - own))
        if self.reads:
            for name in captured:
                self.reads[-1].setdefault(name, set()).update(reads.get(name, ()))
        t = FuncT(tuple(p.type for p in params), body.type)
        return Expr("func", t, (fid, captured), body.deps)

    def function_arg(self, node: Node, params: tuple, result, scope: dict) -> Expr:
        """A function given to a collection function, which calls it with params."""
        if _head(node) == "fn":
            assert isinstance(node, Form)
            e = self.fn(node, scope, params, result)
        else:
            e = self.expr(node, None, scope)
        ft = _core(e.type)
        ok = (
            isinstance(ft, FuncT)
            and len(ft.params) == len(params)
            and all(
                fits(_loose(_inner(a)), _loose(b)) for a, b in zip(params, ft.params, strict=True)
            )
            and (result is None or fits(_loose(ft.result), _loose(result)))
        )
        if not ok:
            want = " ".join(str(t) for t in (*params, result if result is not None else "…"))
            raise CompileError(f"expected func[{want}], got {e.type}", node.pos)
        return e

    def collection(self, node: Form, head: str, scope: dict) -> Expr:
        """map, where, sort, reverse, reduce, sum, count, any and all (reference.md,
        "Collections"): a collection first, then what they need."""
        args = node.items[1:]
        if not args:
            raise CompileError(f"{head} takes a collection first", node.pos)
        coll = self.expr(args[0], None, scope)
        item, n = self.collection_items(coll, head, node.pos)
        rest = args[1:]
        if head in ("sum", "count", "reduce", "any", "all") and _may_be_none(item):
            raise CompileError(
                f"the items of {head} may be none: filter them out with (somes xs)", node.pos
            )
        f, deps = None, coll.deps

        def given(k: int, params: tuple, result) -> Expr:
            nonlocal f, deps
            f = self.function_arg(rest[k], params, result, scope)
            deps |= f.deps
            if f.op == "func":
                fdef = self.model.functions[f.args[0]]
                for path in fdef.reads.get(fdef.params[len(params) - 1].name, ()):
                    deps |= self.reads_through(coll, "[]." + path)
            return f

        def sized(t: Type) -> Type:
            return Refine(t, (("length", n),)) if n is not None else t

        if head == "map":
            self.arity(node, 2)
            ft = _core(given(0, (item,), None).type)
            assert isinstance(ft, FuncT) and f is not None
            out = ft.result
            if _may_be_none(item) and not _may_be_none(ft.params[0]):
                out = _maybe(out)
            vals = self.fold_each(f, item, coll.value) if coll.known else None
            if vals is not None:
                return _known(sized(ListT(out)), vals)
            # Items that share a range give the list's item type that range.
            if f.op == "func":
                body = self.model.functions[f.args[0]].body
                out = _with_range(out, body.range if body is not None else None)
            return Expr("map", sized(ListT(out)), (coll, f), deps)
        if head == "where":
            self.arity(node, 2)
            given(0, (item,), BOOL)
            assert f is not None
            keep = self.fold_each(f, item, coll.value) if coll.known else None
            if keep is not None:
                return _known(ListT(item), [v for v, k in zip(coll.value, keep, strict=True) if k])
            return Expr("where", ListT(item), (coll, f), deps)
        if head == "sort":
            self.arity(node, 2)
            given(0, (item,), REAL)
            assert f is not None
            keys = self.fold_each(f, item, coll.value) if coll.known else None
            if keys is not None:
                order = sorted(range(len(keys)), key=keys.__getitem__)
                return _known(sized(ListT(item)), [coll.value[k] for k in order])
            return Expr("sort", sized(ListT(item)), (coll, f), deps)
        if head == "reverse":
            self.arity(node, 1)
            if not isinstance(_core(coll.type), ListT):
                raise CompileError(f"reverse takes a list, got {coll.type}", node.pos)
            if coll.known:
                return _known(coll.type, list(reversed(coll.value)))
            return Expr("reverse", sized(ListT(item)), (coll,), deps)
        if head == "reduce":
            self.arity(node, 3)
            start = self.expr(rest[0], self.accumulator(rest[1]), scope)
            ft = _core(given(1, (start.type, item), None).type)
            assert isinstance(ft, FuncT) and f is not None
            acc = ft.params[0]
            if not fits(_loose(ft.result), _loose(acc)):
                raise CompileError(f"reduce's function gives {ft.result}, not {acc}", node.pos)
            if coll.known and start.known and self.foldable(f):
                total = start
                for v in coll.value:
                    total = self.call_value(f, [total, _known(item, v)])
                    if total is None:
                        break
                if total is not None:
                    return _known(acc, total.value)
            return Expr("reduce", acc, (coll, start, f), deps | start.deps, _type_range(acc))
        if head == "sum":
            self.arity(node, 1)
            t = _core(item)
            if t not in NUMBERS:
                raise CompileError(f"sum takes numbers, got {item}", node.pos)
            if coll.known:
                return _known(t, sum(coll.value))
            return Expr("sum", t, (coll,), deps, WHOLE)
        if head == "count":
            if len(rest) > 1:
                raise CompileError("count takes a collection and, optionally, a function", node.pos)
            if not rest:
                if n is not None:
                    return _known(INT, n)
                return Expr("count", INT, (coll,), deps, (0.0, MAX_REAL))
            given(0, (item,), BOOL)
            assert f is not None
            hits = self.fold_each(f, item, coll.value) if coll.known else None
            if hits is not None:
                return _known(INT, sum(1 for h in hits if h))
            return Expr("count", INT, (coll, f), deps, (0.0, MAX_REAL))
        # any, all
        if len(rest) > 1:
            raise CompileError(f"{head} takes a collection and, optionally, a function", node.pos)
        if not rest:
            if _core(item) != BOOL:
                raise CompileError(f"{head} takes bools, or a function giving them", node.pos)
            if coll.known:
                return _known(BOOL, (any if head == "any" else all)(coll.value))
            return Expr(head, BOOL, (coll,), deps)
        given(0, (item,), BOOL)
        assert f is not None
        hits = self.fold_each(f, item, coll.value) if coll.known else None
        if hits is not None:
            return _known(BOOL, (any if head == "any" else all)(hits))
        return Expr(head, BOOL, (coll, f), deps)

    def accumulator(self, node: Node) -> Type | None:
        """The type reduce's function declares for its running value, so a literal start such
        as [0 0] takes it."""
        if (
            _head(node) == "fn"
            and isinstance(node, Form)
            and isinstance(node.items[1], Form)
            and node.items[1].items
        ):
            params = self.params(node.items[1])
            return params[0].type if params else None
        if isinstance(node, Name) and len(node.parts) == 1 and node.parts[0] in self.model.funcs:
            f = self.model.functions[self.model.funcs[node.parts[0]]]
            return f.params[0].type if f.params else None
        return None

    def arity(self, node: Form, n: int) -> None:
        if len(node.items) - 1 != n:
            raise CompileError(f"{_head(node)} takes {n} argument{'s' * (n != 1)}", node.pos)

    def collection_items(self, coll: Expr, head: str, pos: Pos) -> tuple[Type, int | None]:
        """The type of a collection's items, and its length when it is known."""
        if _may_be_none(coll.type):
            raise CompileError(f"the collection given to {head} may be none", pos)
        items = self.items_of(coll) if coll.op == "obj" else None
        if items is not None:
            return self.common(list(items)), len(items)
        t = _core(coll.type)
        if isinstance(t, ListT):
            return t.item, _length(coll)
        if isinstance(t, Interface) and t.name == "sequence" and t.of is not None:
            return t.of, None
        if t == ShapeT("group"):
            return Interface("shape"), None
        raise CompileError(f"{head} takes a list or a group, got {coll.type}", pos)

    # Transitions, animations and writers ---------------------------------------------------

    def transition(self, form: Form, scope: dict, top: bool) -> int:
        """A transition, with what it moves, or none for a pure one that keeps only the
        trajectory: (transition name target item…) at the top level, (move target item…) inside
        another form (reference.md, "Transitions and animations")."""
        if top:
            if len(form.items) < 3:
                raise CompileError("a transition is (transition name target item…)", form.pos)
            name, pos = self.name_of(form, scope)
            tnode, items = form.items[2], form.items[3:]
        else:
            if len(form.items) < 2:
                raise CompileError("a move is (move target item…)", form.pos)
            name, pos = None, form.pos
            tnode, items = form.items[1], form.items[2:]
        target = None
        if not isinstance(tnode, NoneLit):
            if not isinstance(tnode, Name):
                raise CompileError(
                    "a transition's target is a variable or an attribute, or none", tnode.pos
                )
            target = self.writable(tnode, scope)
        obj = Obj("transition", name, TRANSITION, pos=pos)
        ends: dict = {}
        given: set[str] = set()
        for item in items:
            head = _head(item)
            if head is None or not isinstance(item, Form) or len(item.items) != 2:
                raise CompileError(f"expected an argument such as (to 1), got {item}", item.pos)
            arg = item.items[1]
            if head == "like":
                # The named transition's arguments, under the ones this one gives itself: they
                # fill only what is not given, wherever (like …) is written.
                if not isinstance(arg, Name):
                    raise CompileError("like takes the name of a transition", arg.pos)
                base = self.model.objects[self.named(arg, "transition")]
                for k, v in base.attrs.items():
                    obj.attrs.setdefault(k, v)
                for k, v in base.data["ends"].items():
                    ends.setdefault(k, v)
                continue
            if head in given:
                raise CompileError(f"'{head}' is given twice", item.pos)
            given.add(head)
            if head in ("from", "to"):
                ends[head] = (arg, scope)
            elif head == "duration":
                obj.attrs["duration"] = Attribute(REAL, self.seconds(arg, scope))
            elif head == "ease":
                obj.attrs["ease"] = self.ease(arg, scope)
            elif head == "path":
                obj.attrs["path"] = self.path(arg, scope)
            else:
                raise CompileError(f"a transition takes no argument '{head}'", item.pos)
        obj.data.update({"ends": ends, "end": None, "target": target})
        i = self.add(obj)
        if target is not None:
            self.type_ends(i, target[2], tnode.pos)
        return i

    def seconds(self, node: Node, scope: dict) -> float:
        e = self.expr(node, REAL, scope)
        if not e.known:
            raise CompileError("a duration is a number of seconds known when compiling", node.pos)
        if e.value < 0:
            raise CompileError("a duration cannot be negative", node.pos)
        return e.value

    def ease(self, node: Node, scope: dict) -> Attribute:
        """'linear', 'ease-in', 'ease-out', 'ease-in-out', (step n), or a func[real real]."""
        if isinstance(node, StrLit):
            if node.value not in EASES:
                raise CompileError(
                    f"'{node.value}' is not an ease: use one of {', '.join(EASES)}", node.pos
                )
            return Attribute(STRING, node.value)
        if _head(node) == "step-ease":
            assert isinstance(node, Form)
            (arg,) = self.args(node, 1)
            at = self.expr(arg, UNIT, scope)
            if not at.known:
                raise CompileError("step-ease takes a point known when compiling", node.pos)
            return Attribute(STRING, ("step-ease", at.value))
        if _head(node) == "step":
            assert isinstance(node, Form)
            (arg,) = self.args(node, 1)
            n = self.expr(arg, INT, scope)
            if not n.known or n.value < 1:
                raise CompileError(
                    "(step n) takes a count of at least 1 known when compiling", node.pos
                )
            return Attribute(STRING, ("step", n.value))
        e = self.expr(node, FuncT((REAL,), REAL), scope)
        return Attribute(e.type, expr=e)

    def path(self, node: Node, scope: dict) -> Attribute:
        e = self.expr(node, None, scope)
        ft = _core(e.type)
        if not isinstance(ft, FuncT) or len(ft.params) != 3:
            raise CompileError("a path is a function of the two ends and the progress", node.pos)
        return Attribute(e.type, expr=e)

    def type_ends(self, tid: int, t: Type | None, pos: Pos) -> None:
        """Compile a transition's ends for an attribute of type t. An end that may be none must be
        handled, except into a color|none attribute, where none is mixed as transparent."""
        obj = self.model.objects[tid]
        if obj.data["end"] is not None:
            if t is not None and not fits(_loose(obj.data["end"]), _loose(t)):
                raise CompileError(f"this transition already moves a {obj.data['end']}", pos)
            return
        target = _loose(t) if t is not None else None
        for end, (node, scope) in obj.data["ends"].items():
            e = self.expr(node, _maybe(target) if target is not None else None, scope)
            if _may_be_none(e.type) and target != Maybe(COLOR):
                raise CompileError(
                    "this end may be none: give it a default with (or? value default)", node.pos
                )
            obj.attrs[end] = Attribute(e.type, e.value) if e.known else Attribute(e.type, expr=e)
        obj.data["end"] = target if target is not None else NONE
        if "path" in obj.attrs and target is not None:
            ft = _core(obj.attrs["path"].type)
            want = FuncT((target, target, REAL), target)
            if not fits(ft, want):
                raise CompileError(f"this path is {ft}, but the move needs {want}", pos)

    def animation(self, form: Form, scope: dict, named: bool) -> int:
        if named:
            name, pos = self.name_of(form)
            items = form.items[2:]
        else:
            name, pos, items = None, form.pos, form.items[1:]
            if len(items) == 1 and isinstance(items[0], Name):
                return self.named(items[0], "animation")
        self.options_first(
            items, lambda it: _head(it) in ("default-duration", "default-ease", "loop"), "animation"
        )
        loops = [it for it in items if _head(it) == "loop"]
        if len(loops) > 1:
            raise CompileError("an animation takes one (loop …)", loops[1].pos)
        steps = _in_order(self.steps([it for it in items if it not in loops], None, None, scope))
        if loops:
            if _duration(steps) <= 0:
                raise CompileError("this animation loops, but a round of it takes no time", pos)
            steps = ("loop", self.loop_count(loops[0], scope), steps)
        # An animation that loops forever has no duration: reading it is a compile error.
        attrs = (
            {}
            if _duration(steps) == float("inf")
            else {"duration": Attribute(REAL, _duration(steps))}
        )
        obj = Obj("animation", name, ANIMATION, attrs=attrs, pos=pos, data={"steps": steps})
        return self.add(obj)

    def loop_count(self, form, scope: dict) -> int | None:
        """How many times (loop n) repeats an animation; None, with no n, for forever."""
        if len(form.items) == 1:
            return None
        (node,) = self.args(form, 1)
        e = self.expr(node, None, scope)
        if not e.known:
            raise CompileError("a loop's count must be known when compiling", node.pos)
        if _core(e.type) != INT:
            raise CompileError(f"a loop's count is an int, got {e.type}", node.pos)
        if e.value < 1:
            raise CompileError("a loop's count is at least 1", node.pos)
        return e.value

    def named(self, node: Name, kind: str) -> int:
        name = node.parts[0] if len(node.parts) == 1 else None
        i = self.model.names.get(name) if isinstance(name, str) else None
        if i is None or self.model.objects[i].kind != kind:
            raise CompileError(f"expected the name of a {kind}", node.pos)
        return i

    def steps(self, items, duration, ease, scope: dict) -> list:
        """The steps among items; the defaults among them apply to the moves inside."""
        self.options_first(
            items, lambda it: _head(it) in ("default-duration", "default-ease"), "animation"
        )
        for item in items:
            head = _head(item)
            if head == "default-duration":
                duration = self.seconds(self.args(item, 1)[0], scope)
            elif head == "default-ease":
                ease = _ease_value(self.ease(self.args(item, 1)[0], scope))
        out = []
        for item in items:
            head = _head(item)
            if head in ("default-duration", "default-ease"):
                continue
            if isinstance(item, Name):
                # A name stands for the animation or transition it names.
                name = item.parts[0] if len(item.parts) == 1 else None
                i = self.model.names.get(name) if isinstance(name, str) else None
                if i is None or self.model.objects[i].kind not in ("animation", "transition"):
                    raise CompileError(
                        "expected the name of an animation or a transition", item.pos
                    )
                if self.model.objects[i].kind == "animation":
                    out.append(self.model.objects[i].data["steps"])
                else:
                    out.append(self.played(i, duration, ease, item.pos))
            elif head == "move":
                assert isinstance(item, Form)
                out.append(
                    self.played(self.transition(item, scope, top=False), duration, ease, item.pos)
                )
            elif head in ("at-once", "in-order"):
                assert isinstance(item, Form)
                out.append((head, *self.steps(item.items[1:], duration, ease, scope)))
            else:
                raise CompileError("an animation holds moves, at-once and in-order", item.pos)
        return out

    def played(self, tid: int, duration, ease, pos: Pos) -> tuple:
        """What a transition does inside an animation: it moves its target, or, with none,
        waits."""
        tr = self.model.objects[tid]
        target = tr.data["target"]
        d = tr.attrs["duration"].value if "duration" in tr.attrs else duration
        if target is None:
            if tr.data["ends"] or "ease" in tr.attrs or "path" in tr.attrs:
                raise CompileError("a move with no target waits, so it takes only a duration", pos)
            if d is None:
                raise CompileError(
                    "this wait needs a duration (or a default-duration around it)", pos
                )
            return ("wait", d)
        i, attr, t = target
        if d is None:
            raise CompileError("this move needs a duration (or a default-duration around it)", pos)
        own = tr.attrs.get("ease")
        e = _ease_value(own) if own is not None else ease
        core = _core(t)
        discrete = (
            "bool"
            if core == BOOL
            else "choice"
            if _choices(t)
            else "string"
            if core == STRING
            else None
        )
        if discrete:
            # A bool's or a choice's ease must take only the values 0 and 1 (piecewise
            # constant): (step 1), the default, or step-ease.
            if own is not None and e != ("step", 1) and not _is_step_ease(e):
                raise CompileError(
                    f"an ease for a {discrete} takes only the values 0 and 1; by default it"
                    " changes at the start of its move and holds",
                    pos,
                )
            if not _is_step_ease(e):
                e = ("step", 1)
        return ("move", (i, attr), tid, d, e if e is not None else "linear")

    def writable(self, node: Name, scope: dict) -> tuple[int, str | None, Type]:
        """The attribute a name such as k, p.r, g[1].r or d.c.pos denotes, which a writer may
        write: free, not const, not a token and not fixed by a variant."""
        label = _name_text(node)
        first = node.parts[0]
        if not isinstance(first, str) or first not in self.model.names:
            raise CompileError(f"unknown name '{first}'", node.pos)
        i, attr = self.model.names[first], None
        for part in node.parts[1:]:
            obj = self.model.objects[i]
            if attr is not None:
                raise CompileError(f"{label} is not a variable or an attribute", node.pos)
            if isinstance(part, str):
                members = {self.model.objects[m].name: m for m in obj.members}
                if obj.kind == "instance" and part in members and part not in obj.attrs:
                    i = members[part]
                else:
                    attr = part
            else:
                e = self.member(i, self.expr(part, None, scope), node.pos)
                if e.op != "obj":
                    raise CompileError(
                        "the position of a member to write must be known when compiling", node.pos
                    )
                i = e.args[0]
        obj = self.model.objects[i]
        if attr is None:
            if obj.kind != "variable":
                raise CompileError(
                    f"{label} is not a variable: write one of its attributes", node.pos
                )
            return i, None, self.check_writable(obj, obj.value, label, node.pos)
        if obj.kind == "group" and attr not in obj.attrs:
            types = [self.writable_attr(m, attr, label, node.pos) for m in obj.members]
            if not types:
                raise CompileError(f"{label} cannot be written: the group is empty", node.pos)
            return i, attr, _join_all(types, node.pos)
        return i, attr, self.writable_attr(i, attr, label, node.pos)

    def writable_attr(self, i: int, attr: str, label: str, pos: Pos) -> Type:
        obj = self.model.objects[i]
        if attr in ("x", "y", "pos") and obj.kind in CORNERS:
            # A write to a line's or triangle's position moves every end or corner.
            for c in CORNERS[obj.kind]:
                self.check_writable(obj, obj.attrs[c], label, pos)
            return POINT if attr == "pos" else REAL
        if attr == "pos" and "x" in obj.attrs:
            for a in ("x", "y"):
                self.check_writable(obj, obj.attrs[a], label, pos)
            return POINT
        if obj.kind == "group" and attr not in obj.attrs:
            return ListT(
                _join_all([self.writable_attr(m, attr, label, pos) for m in obj.members], pos)
            )
        if attr not in obj.attrs:
            raise CompileError(f"a {obj.kind} has no attribute '{attr}'", pos)
        return self.check_writable(obj, obj.attrs[attr], label, pos)

    def check_writable(self, obj: Obj, attribute: Attribute, label: str, pos: Pos) -> Type:
        if attribute.bound:
            raise CompileError(
                f"{label} is bound: only a free variable or attribute can be written", pos
            )
        if _is_const(attribute.type):
            raise CompileError(f"{label} is const: it is never written", pos)
        if obj.kind == "variable" and _core(attribute.type) in (COLOR, FONT):
            raise CompileError(f"{label} is a token: no writer can write it", pos)
        if attribute.fixed:
            raise CompileError(f"{label} is fixed by its variant", pos)
        return attribute.type

    def component(self, form: Form, scope: dict) -> None:
        """A view, control or listener (reference.md, "Components")."""
        # The names a repeat around the component gives it.
        self.cscope = scope
        kind = _head(form)
        assert kind is not None
        if kind in ("on-drag", "on-click"):
            if len(form.items) < 2:
                raise CompileError(f"{kind} takes the shape it listens to", form.pos)
            name, pos, items = None, form.pos, form.items[2:]
            shape = self.read_shape(form.items[1])
        else:
            name, pos = self.name_of(form)
            items, shape = form.items[2:], None
        obj = Obj(kind, name, ComponentT(kind), "page", pos=pos)
        # A canvas's body is what it shows; a writer's is its conditions.
        if kind == "canvas":
            self.options_first(
                items, lambda it: not isinstance(it, Name) and _head(it) != "when", kind
            )
        elif kind != "readout":
            # A slider's first item is its move, and on-drag's and toggle's their target:
            # positional arguments.
            body = items[1:] if kind in ("slider", "on-drag", "toggle") else items
            self.options_first(body, lambda it: _head(it) in WRITER_OPTIONS, kind)
        build = getattr(self, "build_" + kind.replace("-", "_"))
        build(obj, list(items), shape)
        self.add(obj)

    def options_first(self, items, is_option, what: str) -> None:
        """Optional arguments come before a form's body (syntax.md, section 8)."""
        body = False
        for item in items:
            if not is_option(item):
                body = True
            elif body:
                raise CompileError(
                    f"({_head(item)} …) is an optional argument, so it comes before the {what}'s"
                    " body",
                    item.pos,
                )

    def read_shape(self, node: Node) -> int:
        e = self.expr(node, None, self.cscope)
        if e.op != "obj" or not isinstance(_core(e.type), ShapeT):
            raise CompileError("expected the name of a shape", node.pos)
        return e.args[0]

    def take(self, items: list, head: str) -> Node | None:
        """Remove the (head value) item from items and give its value."""
        found = [it for it in items if _head(it) == head]
        if len(found) > 1:
            raise CompileError(f"'{head}' is given twice", found[1].pos)
        if not found:
            return None
        items.remove(found[0])
        return self.args(found[0], 1)[0]

    def writer(self, obj: Obj, items: list, written: set) -> None:
        """What every writer has: a label (controls), conditions, and the items left over."""
        if obj.kind not in ("on-drag", "on-click"):
            label = self.take(items, "label")
            # By default a control's label is its name; one with no name has an empty label.
            obj.attrs["label"] = (
                self.attribute(STRING, label, obj.pos, "label", scope=self.cscope)
                if label is not None
                else Attribute(STRING, obj.name or "")
            )
        for item in items:
            if not isinstance(item, Form):
                raise CompileError(f"expected an item of a {obj.kind}, got a name", item.pos)
        obj.data["conditions"] = [self.condition(c, written) for c in items]

    def animated(self, obj: Obj, items: list) -> set:
        anims = [it for it in items if _head(it) == "animation"]
        if len(anims) > 1:
            raise CompileError("'animation' is given twice", anims[1].pos)
        animation = None
        if anims:
            items.remove(anims[0])
            animation = self.animation(anims[0], self.cscope, named=False)
        obj.data["animation"] = animation
        return self.written(animation)

    def when(self, obj: Obj, items: list) -> None:
        node = self.take(items, "when")
        obj.data["when"] = (
            self.attribute(BOOL, node, obj.pos, "when", scope=self.cscope)
            if node is not None
            else None
        )

    def build_button(self, obj: Obj, items: list, shape) -> None:
        written = self.animated(obj, items)
        self.when(obj, items)
        self.writer(obj, items, written)

    def build_slider(self, obj: Obj, items: list, shape) -> None:
        # A slider's move is the path its knob scrubs: the reader gives the speed, so it has
        # no duration and no ease, and both ends are fixed (reference.md, "Controls").
        if not items or not (_head(items[0]) == "move" or isinstance(items[0], Name)):
            raise CompileError("a slider is (slider name move item…)", obj.pos)
        node = items.pop(0)
        if isinstance(node, Name):
            tid = self.named(node, "transition")
        else:
            assert isinstance(node, Form)
            tid = self.transition(node, self.cscope, top=False)
        tr = self.model.objects[tid]
        if tr.data["target"] is None:
            raise CompileError("a slider's move needs a target", node.pos)
        for part in ("duration", "ease"):
            if part in tr.attrs:
                raise CompileError(
                    f"a slider's move takes no {part}: the reader moves the knob", node.pos
                )
        if "from" not in tr.data["ends"] or "to" not in tr.data["ends"]:
            raise CompileError("a slider's move needs both (from …) and (to …)", node.pos)
        steps = self.played(tid, 1, None, node.pos)
        animation = self.add(
            Obj(
                "animation",
                None,
                ANIMATION,
                attrs={"duration": Attribute(REAL, 1)},
                pos=node.pos,
                data={"steps": steps},
            )
        )
        obj.data["animation"] = animation
        written = self.written(animation)
        step = self.take(items, "step")
        if step is not None:
            obj.attrs["step"] = self.attribute(
                Refine(INT, ((">=", 2),)), step, obj.pos, "step", scope=self.cscope
            )
        obj.attrs["position"] = Attribute(UNIT, 0)
        self.when(obj, items)
        self.writer(obj, items, written)

    def build_play(self, obj: Obj, items: list, shape) -> None:
        written = self.animated(obj, items)
        buttons = self.take(items, "buttons")
        obj.attrs["buttons"] = self.attribute(BOOL, buttons, obj.pos, "buttons", scope=self.cscope)
        obj.attrs["playing"] = Attribute(BOOL, False)
        obj.attrs["step"] = Attribute(INT, 0)
        self.when(obj, items)
        self.writer(obj, items, written)

    def build_toggle(self, obj: Obj, items: list, shape) -> None:
        # Its target is positional: the bool it writes, or none to hold its own.
        if not items or not (isinstance(items[0], (Name, NoneLit))):
            raise CompileError(
                "a toggle is (toggle name target item…), its target none or a bool", obj.pos
            )
        first = items.pop(0)
        target = None if isinstance(first, NoneLit) else first
        value = self.take(items, "value")
        written: set = set()
        if target is None:
            obj.data["target"] = None
            obj.attrs["value"] = self.attribute(BOOL, value, obj.pos, "value", scope=self.cscope)
        else:
            if value is not None:
                raise CompileError("a toggle with a target shows its target's value", value.pos)
            if not isinstance(target, Name):
                raise CompileError(
                    "a toggle's target is a variable or an attribute, such as b or g.on", target.pos
                )
            i, attr, t = self.writable(target, self.cscope)
            if _core(t) != BOOL:
                raise CompileError(f"a toggle's target is a bool, got {t}", target.pos)
            obj.data["target"] = (i, attr)
            written = {(i, attr)}
            # On a group's attribute it reads true only when every member's is true.
            if attr is not None and attr not in self.model.objects[i].attrs:
                e = Expr("all", BOOL, (self.obj_attr(i, attr, target.pos),))
                e = replace(e, deps=e.args[0].deps)
            else:
                e = self.read(i, attr)
            obj.attrs["value"] = Attribute(BOOL, expr=e)
        self.when(obj, items)
        self.writer(obj, items, written)

    def build_on_drag(self, obj: Obj, items: list, shape: int) -> None:
        if not items or not isinstance(items[0], Name):
            raise CompileError(
                "on-drag is (on-drag shape target item…), its target a variable or an attribute",
                obj.pos,
            )
        target = items.pop(0)
        i, attr, _ = self.writable(target, self.cscope)
        own = i == shape and attr in ("x", "y", "pos")
        if not own and (i, attr) not in self.position_deps(shape):
            raise CompileError(
                f"{_name_text(target)} is not the shape's position, and its position does not"
                " depend on it",
                target.pos,
            )
        obj.data["shape"], obj.data["target"] = shape, (i, attr)
        self.when(obj, items)
        self.writer(obj, items, {(i, attr)})

    def position_deps(self, shape: int) -> set:
        """Every variable and attribute the shape's position depends on, through bound ones too."""
        if "pos" not in self.attr_names(shape):
            return set()
        seen: set = set()
        todo = list(self.obj_attr(shape, "pos", NOPOS).deps)
        while todo:
            dep = todo.pop()
            if dep in seen:
                continue
            seen.add(dep)
            obj = self.model.objects[dep[0]]
            if dep[1] is None and obj.kind == "variable":
                attribute = obj.value
            else:
                attribute = obj.attrs.get(dep[1])
            if attribute is not None and attribute.bound:
                todo.extend(attribute.deps)
        return seen

    def build_on_click(self, obj: Obj, items: list, shape: int) -> None:
        obj.data["shape"] = shape
        written = self.animated(obj, items)
        self.when(obj, items)
        self.writer(obj, items, written)

    def build_canvas(self, obj: Obj, items: list, shape) -> None:
        defaults = {"view-x": -10, "view-y": -10, "view-width": 20, "view-height": 20}
        for attr, d in defaults.items():
            node = self.take(items, attr)
            obj.attrs[attr] = (
                self.attribute(REAL, node, obj.pos, attr, scope=self.cscope)
                if node
                else Attribute(REAL, d)
            )
        node = self.take(items, "transform")
        obj.attrs["transform"] = (
            self.attribute(TRANSFORM, node, obj.pos, "transform", scope=self.cscope)
            if node
            else Attribute(TRANSFORM, IDENTITY)
        )
        # The reader may pan and zoom a canvas unless the author says not (reference.md).
        for attr in ("pan", "zoom"):
            node = self.take(items, attr)
            obj.attrs[attr] = (
                self.attribute(BOOL, node, obj.pos, attr, scope=self.cscope)
                if node
                else Attribute(BOOL, True)
            )
        # What it shows, in the order written, which is the order it draws them in.
        obj.data.update({"shows": [], "transition": None})
        for item in items:
            head = _head(item)
            if isinstance(item, Name):
                obj.data["shows"].append(self.shown(item))
            elif head == "when" and len(item.items) >= 3:
                cond = self.attribute(BOOL, item.items[1], item.pos, "when", scope=self.cscope)
                obj.data["shows"].append((cond, [self.shown(n) for n in item.items[2:]]))
            elif head == "move":
                assert isinstance(item, Form)
                if obj.data["transition"] is not None:
                    raise CompileError("'move' is given twice", item.pos)
                tid = self.transition(item, self.cscope, top=False)
                if self.model.objects[tid].data["target"] is not None:
                    raise CompileError(
                        "a canvas's move fades what it shows, so its target is none", item.pos
                    )
                obj.data["transition"] = tid
            else:
                raise CompileError("expected an item of a canvas", item.pos)

    def shown(self, node: Node) -> int:
        e = self.expr(node, None, self.cscope)
        if e.op != "obj" or self.model.objects[e.args[0]].kind == "variable":
            raise CompileError("a canvas shows shapes or the scene, by name", node.pos)
        return e.args[0]

    def build_readout(self, obj: Obj, items: list, shape) -> None:
        if not items:
            raise CompileError("a readout shows a string: (readout name value)", obj.pos)
        value = items.pop(0)
        obj.attrs["value"] = self.attribute(STRING, value, obj.pos, "value", scope=self.cscope)
        font = self.take(items, "font")
        if font is not None:
            obj.attrs["font"] = self.font_arg(font)
        if items:
            raise CompileError("expected an item of a readout, such as (font f)", items[0].pos)

    def font_arg(self, node: Node) -> Attribute:
        """A text's or readout's font, which is only ever a declared font variable."""
        e = self.expr(node, None, self.cscope) if isinstance(node, Name) else None
        if e is None or e.op != "read" or _core(e.type) != FONT:
            raise CompileError("a font is given as a declared font variable", node.pos)
        return Attribute(FONT, expr=e)

    def font_variable(self, form: Form, parent, access: str, scope: dict) -> None:
        """(font name (family …) (style …) (weight …) (size …)): declared with items, not a
        value (type-system.md, section 4)."""
        name, pos = self.name_of(form, scope)
        parts = {}
        for item in form.items[2:]:
            head = _head(item)
            if head not in FONT_PARTS or not isinstance(item, Form) or len(item.items) != 2:
                raise CompileError(
                    "a font takes (family …), (style …), (weight …), (size …)", item.pos
                )
            if head in parts:
                raise CompileError(f"'{head}' is given twice", item.pos)
            parts[head] = self.expr(item.items[1], FONT_PARTS[head].type, scope)
        for e in parts.values():
            if not e.known:
                raise CompileError("a font's parts must be known when compiling", pos)
        values = {
            p: parts[p].value if p in parts else spec.default for p, spec in FONT_PARTS.items()
        }
        attribute = Attribute(FONT, values)
        self.add(Obj("variable", name, FONT, access, {"value": attribute}, parent=parent, pos=pos))

    def access_of(self, deps) -> tuple[str, int | None]:
        """page, and the object that gives it, when anything in deps has page access."""
        for i, _ in deps:
            if self.model.objects[i].access == "page":
                return "page", i
        return "scene", None

    def written(self, animation: int | None) -> set:
        """The attributes an animation's moves write."""
        if animation is None:
            return set()

        def walk(step) -> set:
            if step[0] == "move":
                return {step[1]}
            if step[0] in ("at-once", "in-order"):
                return set().union(*(walk(s) for s in step[1:]))
            if step[0] == "loop":
                return walk(step[2])
            return set()

        return walk(self.model.objects[animation].data["steps"])

    def condition(self, node: Node, written: set) -> dict:
        """A writer's condition, as a clamp: a comparison of an attribute it writes with a limit
        that does not depend on that attribute (reference.md, "Writes and conditions")."""
        flip = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}
        head = _head(node)
        if head in COMPARE and isinstance(node, Form) and len(node.items) == 3:
            a, b = (self.expr(x, None, self.cscope) for x in node.items[1:])
            for op, side, limit in ((head, a, b), (flip[head], b, a)):
                if side.op == "read":
                    attribute = (side.args[0], side.args[1])
                    if attribute in written and attribute not in limit.deps:
                        lim = self.settle(limit.type, limit, "the limit", node.pos)
                        return {"target": attribute, "op": op, "limit": lim}
        raise CompileError(
            "a condition compares an attribute this writer writes with a limit that does not depend"
            " on it, such as (>= k 0)",
            node.pos,
        )

    def trial(self, name: str, pos: Pos) -> None:
        """Compile one instance and discard it, so a body's errors show without any instance."""
        objects, names, sites = len(self.model.objects), dict(self.model.names), self.rand_sites
        try:
            j = self.shape(Form((Name((name,), pos), NoneLit(pos)), pos), None, {})
            obj = self.model.objects[j]
            types = {a: attribute.type for a, attribute in obj.attrs.items()}
            for m in obj.members:
                member = self.model.objects[m]
                if member.name is not None:
                    types[member.name] = member.type
            self.shape_types[name] = types
        finally:
            del self.model.objects[objects:]
            self.model.names = names
            self.rand_sites = sites

    def variant_decl(self, form: Form) -> None:
        name, pos = self.name_of(form)
        if name is None or len(form.items) < 4:
            raise CompileError("a variant is (variant name parameters shape)", form.pos)
        if len(form.items) != 4 or not self.shape_kind(form.items[3]):
            raise CompileError("a variant's body is one shape", form.pos)
        if name in SHAPE_ATTRS or name in self.model.types:
            raise CompileError(f"'{name}' is already declared", pos)
        body = form.items[3]
        assert isinstance(body, Form)
        found = self.shape_kind(body)
        assert found is not None
        base = found[0]
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
            if k < len(POSITIONAL.get(base, ())) and head not in taken:
                fixed.add(POSITIONAL[base][k])
            elif head == "pos":
                fixed |= {"x", "y"}
            elif head is not None:
                fixed.add(head)
        self.model.variants[name] = VariantDef(name, params, base, body, frozenset(fixed), pos)
        base_type = self.model.types.get(base, ShapeT(base))
        assert isinstance(base_type, ShapeT)
        self.model.types[name] = ShapeT(name, base_type)
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
        found = self.shape_kind(form)
        assert found is not None
        kind, absent = found
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

        def set_params(obj: Obj) -> None:
            for p in v.params:
                node, inner = mine.get(p.name, (p.default, {}))
                obj.attrs[p.name] = self.attribute(p.type, node, form.pos, p.name, None, inner)

        merged = _scoped(v.body.items[2:], body_scope) + rest
        head = Name((v.base,), form.pos)
        if absent:
            head = Bar((head, NoneLit(form.pos)), form.pos)
        base_form = Form((head, form.items[1]), form.pos)
        pre = (*pre, set_params)
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
            value = None
            if default is not None:
                e = self.expr(default, t, {})
                if not e.known:
                    raise CompileError(
                        "a parameter's default must be known when compiling", default.pos
                    )
                value = e.value
            out.append(Param(name, t, default, value))
        return tuple(out)

    def instance(
        self, form: Form, parent, scope: dict, spread=None, absent=False, items=None, pre=()
    ) -> int:
        found = self.shape_kind(form)
        assert found is not None
        kind = found[0]
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
                obj.attrs[p.name] = self.attribute(at, node, form.pos, p.name, None, inner)
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
                    assert isinstance(item, Form)
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
        saved, self.where = self.where, (name, None, None)
        try:
            attribute = self.attribute(t, node, form.pos, "the value", scope=scope)
        finally:
            self.where = saved
        if name is None:
            raise CompileError("a variable in a motif's body needs a name", pos)
        self.keep_length(t, attribute)
        # A value known when compiling is free, but const, so no writer can change it.
        if not attribute.bound and not _is_const(attribute.type):
            raise CompileError(
                "a motif's body declares only bound variables; free state is a parameter", pos
            )
        obj.attrs[name] = attribute
        self.bodies[-1]["attrs"].add(name)

    def scene_decl(self, form: Form) -> None:
        if self.scene is not None:
            raise CompileError("a file has exactly one scene", form.pos)
        name, pos = self.name_of(form)
        attrs = {"background": Attribute(PAINT, None)}
        self.scene = self.add(Obj("scene", name, SCENE, attrs=attrs, pos=pos))
        self.in_scene = True
        try:
            self.scene_items(form, attrs)
        finally:
            self.in_scene = False

    def scene_items(self, form: Form, attrs: dict) -> None:
        self.options_first(form.items[2:], lambda it: _head(it) == "background", "scene")
        for item, scope in self.expand(form.items[2:], {}):
            head = _head(item)
            if head == "background":
                assert isinstance(item, Form)
                attrs["background"] = self.attribute(
                    PAINT, item.items[1], item.pos, "background", scope=scope
                )
            elif head in ("motif", "variant", "func", "transition", "animation") or (
                head in COMPONENTS
            ):
                raise CompileError(f"a {head} is declared only at the top level", item.pos)
            elif self.shape_kind(item):
                assert isinstance(item, Form)
                self.shape(item, self.scene, scope)
            elif isinstance(item, Form):
                self.variable(item, self.scene, "scene", scope)
            else:
                raise CompileError("the scene holds shapes and variables", item.pos)

    def shape(self, form: Form, parent, scope: dict, spread=None, items=None, pre=()) -> int:
        """A shape declaration. items, when given, replaces the form's own items, each with its
        scope, and pre runs on the new object before its attributes are compiled (a variant
        uses both)."""
        found = self.shape_kind(form)
        assert found is not None
        kind, absent = found
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
            # The first item is the positional unless it names one of the shape's arguments.
            if scoped and _head(scoped[0][0]) not in takes | {"pos"}:
                given[attr] = scoped.pop(0)
        for item, inner in self.expand_scoped(scoped):
            if kind == "group" and self.shape_kind(item):
                members.append((item, inner))
                continue
            if members:
                raise CompileError(
                    f"({_head(item)} …) is an optional argument, so it comes before the group's"
                    " body",
                    item.pos,
                )
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
                # A stroke would outline a text's letters, so a text takes none from a group.
                if kind == "text" and attr in ("stroke", "stroke-width"):
                    continue
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
            assert isinstance(item, Form)
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
            if attr == "font" and node is not None:
                obj.attrs[attr] = self.font_arg(node)
                continue
            saved, self.where = self.where, (obj.name, obj.of or obj.kind, attr)
            try:
                obj.attrs[attr] = self.attribute(at, node, pos, attr, spec.default, inner)
            finally:
                self.where = saved
        if "pos" in given:
            node, inner = given["pos"]
            point = self.expr(node, _maybe(POINT) if absent else POINT, inner)
            for k, attr in enumerate(("x", "y")):
                at = _maybe(REAL) if absent else REAL
                obj.attrs[attr] = self.settle(at, _part(point, k), attr, node.pos)
        if absent:
            for attr, attribute in obj.attrs.items():
                if not _may_be_none(_value_type(attribute)):
                    attribute.type = specs[attr].type

    # Attributes ------------------------------------------------------------------------------

    def may_be_none(self, expected: Type) -> str:
        fix = "give it a default with (or? value default)"
        if self.where and self.where[0] and self.where[2]:
            name, kind, attr = self.where
            return f"{name}'s {attr} may be none: {fix}, or declare {name} as {kind}|none"
        if self.where and self.where[0]:
            return f"{self.where[0]} may be none: {fix}, or declare it {_loose(expected)}|none"
        return f"this value may be none: {fix}"

    def may_break(self, what: str, c, t: Type) -> str:
        fix = "constrain what it reads so this can be proved"
        if self.where and self.where[0] and self.where[2]:
            name, kind, attr = self.where
            return f"{name}'s {attr} may break {_show(c)}: {fix}, or declare {name} as {kind}|none"
        if self.where and self.where[0]:
            return f"{self.where[0]} may break {_show(c)}: {fix}, or declare it {t}|none"
        return f"{what} may break {_show(c)}"

    def attribute(
        self, t: Type, node: Node | None, pos: Pos, what: str, default=None, scope=None
    ) -> Attribute:
        if node is None:
            return Attribute(
                t, self.default(t, pos) if default is None and t != Maybe(COLOR) else default
            )
        attribute = self.settle(t, self.expr(node, t, scope or {}), what, node.pos)
        # An attribute given by an expression is bound; folded, it is free but const, so no writer
        # can write it (mtpc.md, "Attributes").
        if not attribute.bound and not _is_literal(node) and not self.is_constant(node, scope):
            attribute.type = _with_const(attribute.type)
        return attribute

    def is_constant(self, node: Node, scope) -> bool:
        """Whether node is a constant: the bare name of a const variable or of a built-in
        constant, or a read of a const attribute such as c.r. Given one, an attribute is free, as
        if given its value (mtpc.md, "Attributes")."""
        if not isinstance(node, Name):
            return False
        parts = [p for p in node.parts if isinstance(p, str)]
        if len(parts) != len(node.parts):
            return False
        first, rest = parts[0], parts[1:]
        if first in (scope or {}) or (self.bodies and first == "self"):
            return False
        if self.bodies and (first in self.bodies[-1]["names"] or first in self.bodies[-1]["attrs"]):
            return False
        if first not in self.model.names:
            return not rest and first in CONSTANTS
        obj = self.model.objects[self.model.names[first]]
        for k, part in enumerate(rest):
            members = {self.model.objects[m].name: m for m in obj.members}
            if part in obj.attrs and k == len(rest) - 1:
                attribute = obj.attrs[part]
                return not attribute.bound and _is_const(attribute.type)
            if part not in members:
                return False
            obj = self.model.objects[members[part]]
        return obj.kind == "variable" and _is_const(obj.value.type)

    def settle(self, t: Type, e: Expr, what: str, pos: Pos) -> Attribute:
        """An attribute holding e: free when e is known, bound otherwise. A bound value must stay
        within the attribute's constraints, or the compiler stops (type-system.md, 5.b and 5.c)."""
        if e.known:
            return Attribute(t, e.value)
        access, source = self.access_of(e.deps)
        if access == "page" and (self.in_scene or self.bodies):
            assert source is not None
            label = self.model.objects[source].name
            raise CompileError(
                f"the scene cannot read {label}: it has page access, so only components and"
                " globals may read it",
                pos,
            )
        inner = _inner(t)
        if isinstance(inner, Refine):
            broken = tuple(
                c for c in inner.constraints if c[0] in COMPARE and not _range_within(e.range, c)
            )
            if broken and not _may_be_none(t):
                raise CompileError(self.may_break(what, broken[0], t), pos)
            if broken:
                e = Expr("check", _maybe(e.type), (e, broken), e.deps, e.range)
        return Attribute(t, expr=e)

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
                        who = self.where[0] if self.where and self.where[0] else "this value"
                        raise CompileError(
                            f"{who} needs a value: 0 breaks {_show(c)}, and there is no lower"
                            " bound to use instead",
                            pos,
                        )
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
        if base == FONT:
            return dict(FONT_DEFAULT)
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
            assert expected is not None
            if _may_be_none(e.type) and not _may_be_none(target):
                raise CompileError(self.may_be_none(expected), node.pos)
            if _core(e.type) == STRING and _core(target) == COLOR:
                raise CompileError(
                    f"expected {expected}, got {e.type}: only a literal string becomes a color",
                    node.pos,
                )
            if e.type == ComponentT("toggle") and e.op == "obj":
                name = self.model.objects[e.args[0]].name
                raise CompileError(
                    f"a toggle is read through its value: write {name}.value", node.pos
                )
            raise CompileError(f"expected {expected}, got {e.type}", node.pos)
        narrowed = _inner(expected) if expected is not None else None
        if e.known and e.value is not None and isinstance(narrowed, Refine):
            for c in narrowed.constraints:
                if c[0] != "const" and not _satisfies(e.value, c):
                    if c[0] == "one-of":
                        choices = ", ".join(f"'{v}'" for v in c[1])
                        if narrowed.name:
                            raise CompileError(
                                f"'{e.value}' is not a {narrowed.name}: a {narrowed.name} is one"
                                f" of {choices}",
                                node.pos,
                            )
                        raise CompileError(f"'{e.value}' is not one of {choices}", node.pos)
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

    def literal(
        self,
        node: IntLit | RatioLit | RealLit | ComplexLit | StrLit | NoneLit,
        expected: Type | None,
    ) -> Expr:
        if isinstance(node, NoneLit) and expected is None:
            return _known(NONE, None)
        attribute = _loose(expected) if expected is not None else None
        try:
            t = literal_type(node, attribute)
        except TypeError_ as e:
            raise CompileError(str(e), node.pos) from None
        if isinstance(node, NoneLit):
            return _known(t, None)
        # A literal that is not none has the type of its attribute's other values.
        t = _inner(t)
        value = node.value
        if isinstance(value, (int, float, Fraction)) and abs(value) > LIMIT:
            raise CompileError(f"{value} is beyond ±10^150, the limit of every number", node.pos)
        if t == COLOR or (isinstance(t, Maybe) and t.inner == COLOR):
            assert isinstance(node, StrLit)
            value = parse_color(node.value)
        return _known(t, value)

    def list_literal(self, node: ListLit, expected: Type | None, scope: dict) -> Expr:
        attribute = expected.base if isinstance(expected, Refine) else expected
        if isinstance(attribute, Maybe):
            attribute = attribute.inner
        if attribute == POINT:
            items = [self.expr(i, Maybe(REAL), scope) for i in node.items]
            if len(items) != 2:
                raise CompileError("a point is two numbers, [x y]", node.pos)
            return _gather(POINT, items)
        item = attribute.item if isinstance(attribute, ListT) else None
        if not node.items:
            if item is None:
                raise CompileError("an empty list needs its type: write list[T]", node.pos)
            return _known(ListT(item), [])
        items = [self.expr(i, item, scope) for i in node.items]
        if any(e.type == RECURSING for e in items):
            return Expr("list", RECURSING, tuple(items))
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
            # Items computed while drawing that share a range give the list's item type that
            # range; a list of literals keeps its plain type, so a writer may replace it.
            if not all(e.known for e in items):
                ranges = [e.range for e in items]
                if all(r is not None for r in ranges):
                    lo = min(r[0] for r in ranges if r is not None)
                    hi = max(r[1] for r in ranges if r is not None)
                    t = _with_range(t, (lo, hi))
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
        if name in CONSTANTS:
            return _known(REAL, CONSTANTS[name])
        if name in BUILTINS:
            b = BUILTINS[name]
            return Expr("builtinfunc", FuncT(b.params, _result(b)), (name,))
        raise CompileError(f"unknown name '{name}'", pos)

    def read(self, i: int, attr: str | None) -> Expr:
        obj = self.model.objects[i]
        moves: frozenset = frozenset()
        if obj.kind == "variable" and attr is None:
            attribute = obj.value
        else:
            if attr is None:
                return Expr("obj", obj.type, (i,))
            if attr not in obj.attrs:
                raise CompileError(f"a {obj.kind} has no attribute '{attr}'", obj.pos)
            attribute = obj.attrs[attr]
            if obj.kind in SHAPE_ATTRS or (obj.kind == "instance" and attr in INSTANCE_ATTRS):
                moves = self.moves(i)
        t = _maybe(attribute.type) if isinstance(obj.type, Maybe) else attribute.type
        # A token is never folded: the page may restyle it. A transition or an animation is a
        # value, so its free parts are known.
        token = obj.kind == "variable" and _core(attribute.type) in (COLOR, FONT)
        fixed = obj.kind in ("transition", "animation")
        if not attribute.bound and (fixed or (_is_const(attribute.type) and not token)):
            return _known(t, attribute.value)
        deps = frozenset({(i, attr)}) | moves
        return Expr("read", t, (i, attr, self.frame), deps, _type_range(t))

    def moves(self, i: int) -> frozenset:
        """The translate and transform attributes a read of shape i converts through: its own and
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

    def shape_part(self, e: Expr, name: str, pos: Pos) -> Expr:
        """An attribute of a shape known only by its type, such as a parameter's: only what
        the type lists can be read (type-system.md, section 6)."""
        t = _core(e.type)
        attrs = self.type_attr_types(t)
        if name not in attrs:
            raise CompileError(f"a {t} has no attribute '{name}'", pos)
        self.note(e, name)
        return Expr("part", attrs[name], (e, name), e.deps, _type_range(attrs[name]))

    def type_attr_types(self, t: Type) -> dict[str, Type]:
        if t == Interface("positioned"):
            return {"x": REAL, "y": REAL, "pos": POINT}
        if t == Interface("shape"):
            return {"translate": POINT, "transform": TRANSFORM}
        if not isinstance(t, ShapeT):
            return {}
        kind = t
        while kind.base is not None:
            kind = kind.base
        if t.name in self.shape_types:
            out = dict(self.shape_types[t.name])
        elif t.name in SHAPE_ATTRS:
            out = {a: spec.type for a, spec in SHAPE_ATTRS[t.name].items()}
        else:
            return {}
        if "x" in out or kind.name in CORNERS:
            out |= {"x": REAL, "y": REAL, "pos": POINT}
        if kind.name == "group":
            out["length"] = INT
        return out

    def has_attr(self, e: Expr, name) -> bool:
        if e.op == "obj":
            return name in self.attr_names(e.args[0])
        if e.op == "member":
            return name in self.type_attrs(_inner(e.type), e.args[2])
        if isinstance(_core(e.type), (ShapeT, Interface)):
            held = self.objects_in(e)
            if held is not None:
                return name in self.type_attrs(_core(e.type), held)
            return name in self.type_attr_types(_core(e.type))
        if _base(_inner(e.type)) == POINT and name in ("x", "y"):
            return True
        core = _core(e.type)
        return name in VALUE_ATTRS.get(core, {}) or (isinstance(core, ListT) and name == "length")

    def value_attr(self, e: Expr, name: str, pos: Pos) -> Expr:
        """An attribute of a value: a complex's re and im, a color's channels, a string's or a
        list's length, a font's parts."""
        core = _core(e.type)
        if isinstance(core, ListT) and name == "length":
            n = _length(e)
            if n is not None:
                return _known(INT, n)
            return Expr("part", INT, (e, name), e.deps, (0.0, MAX_REAL))
        t = VALUE_ATTRS.get(core, {}).get(name)
        if t is None:
            raise CompileError(f"a {e.type} has no attribute '{name}'", pos)
        if e.known:
            return _known(t, _value_part(core, e.value, name))
        return Expr("part", t, (e, name), e.deps, _type_range(t))

    def attr_names(self, i: int) -> set:
        obj = self.model.objects[i]
        names = set(obj.attrs)
        if obj.name is not None and obj.kind != "variable":
            names.add("name")
        if obj.kind in ("group", "scene"):
            names |= {"length", "members"}
        if "x" in obj.attrs or obj.kind in CORNERS:
            names |= {"x", "y", "pos"}
        if obj.kind == "instance":
            names |= cast("set[str]", {self.model.objects[m].name for m in obj.members} - {None})
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
        if name == "name" and name not in obj.attrs:
            return _known(STRING, obj.name) if obj.name is not None else _known(NONE, None)
        if obj.kind == "transition" and name in ("from", "to") and obj.data.get("end") is None:
            self.type_ends(i, None, pos)
        if obj.kind in ("group", "scene") and name == "length":
            return _known(INT, len(obj.members))
        if obj.kind in ("group", "scene") and name == "members":
            items = tuple(self.read(m, None) for m in obj.members)
            return Expr("list", ListT(self.common(obj.members)), items)
        if name == "pos" and obj.kind != "group" and "pos" in self.attr_names(i):
            return _gather(POINT, [self.obj_attr(i, "x", pos), self.obj_attr(i, "y", pos)])
        if obj.kind in CORNERS and name in ("x", "y"):
            k = 0 if name == "x" else 1
            ends = [_part(self.read(i, c), k) for c in CORNERS[obj.kind]]
            return self.arith(pos, "/", [self.arith(pos, "+", ends), _known(INT, len(ends))])
        if name in obj.attrs:
            return self.read(i, name)
        if obj.kind == "animation" and name == "duration":
            raise CompileError(
                f"{obj.name or 'this animation'} loops forever, so it has no duration", pos
            )
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
            t = Refine(ListT(t), (("length", len(obj.members)),))
            return Expr("spread", t, (Expr("obj", obj.type, (i,)), name), deps)
        raise CompileError(f"a {obj.kind} has no attribute '{name}'", pos)

    def part_of(self, e: Expr, part, scope: dict, pos: Pos) -> Expr:
        if e.type == RECURSING:
            index = part if isinstance(part, str) else self.expr(part, None, scope)
            return Expr("part", RECURSING, (e, index))
        if isinstance(part, str):
            if e.op == "obj":
                return self.obj_attr(e.args[0], part, pos)
            if isinstance(_core(e.type), (ShapeT, Interface)) and e.op != "member":
                held = self.objects_in(e)
                if held is None:
                    return self.shape_part(e, part, pos)
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
            return self.value_attr(e, part, pos)
        index = self.expr(part, None, scope)
        if e.op == "obj" and self.model.objects[e.args[0]].kind in ("group", "scene"):
            return self.member(e.args[0], index, pos)
        if not fits(_loose(index.type), INT):
            raise CompileError(f"a position is an int, got {index.type}", pos)
        whole = _base(_inner(e.type))
        if isinstance(whole, ListT) or whole == POINT:
            item = whole.item if isinstance(whole, ListT) else REAL
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
        if isinstance(whole, Interface) and whole.name == "sequence" and whole.of is not None:
            # A sequence parameter's length is not known, so a position on it may be none.
            item = _maybe(whole.of)
            return Expr("part", item, (e, index), e.deps | index.deps, _type_range(item))
        raise CompileError(f"a {e.type} has no items", pos)

    def held(self, e: Expr) -> tuple | None:
        """The shapes a variable typed with a shape or an interface may hold."""
        if e.op != "read" or e.args[1] is not None:
            return None
        if not isinstance(_core(e.type), (ShapeT, Interface)):
            return None
        attribute = self.model.objects[e.args[0]].value
        if attribute.bound and attribute.expr.op == "obj":
            return (attribute.expr.args[0],)
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
        if head == "as":
            type_node, lit = self.args(node, 2)
            # A list in brackets is a literal even when it holds expressions (type-system.md,
            # section 3).
            if not (_is_literal(lit) or isinstance(lit, ListLit)):
                raise CompileError(
                    "as gives a type only to a literal, such as (as color 'gold')", node.pos
                )
            return self.expr(lit, self.type_of(type_node), scope)
        if head == "type-of":
            (a,) = self.args(node, 1)
            return _known(STRING, str(self.expr(a, None, scope).type))
        if head == "fn":
            ft = _core(expected) if expected is not None else None
            if isinstance(ft, FuncT):
                return self.fn(node, scope, ft.params, ft.result)
            return self.fn(node, scope)
        if head in COLLECTION:
            return self.collection(node, head, scope)
        if head in BUILTINS or head in SPECIAL_BUILTINS:
            return self.builtin(node, head, scope)
        if head == "if":
            if len(args) != 3:
                raise CompileError("if takes a condition and two branches", node.pos)
            c = self.expr(args[0], BOOL, scope)
            # Branches may be none; what the if's value is given to decides whether that is allowed.
            branch = _maybe(expected) if expected is not None else None
            # Folding a call takes only the branch it needs, so recursion ends at its base case.
            if c.known and self.folding:
                return self.expr(args[1] if c.value else args[2], branch, scope)
            if branch is None and isinstance(args[1], ListLit) != isinstance(args[2], ListLit):
                # With nothing outside to give a type, a literal list takes the other branch's.
                lit = 1 if isinstance(args[1], ListLit) else 2
                other = self.expr(args[3 - lit], None, scope)
                hint = None if other.type == RECURSING else _maybe(_inner(other.type))
                given = self.expr(args[lit], hint, scope)
                a, b = (given, other) if lit == 1 else (other, given)
            else:
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
            return self.arith(node.pos, head, self.operands(args, expected, scope))
        if head in COMPARE or head in ("=", "!="):
            a, b = self.args(node, 2)
            ea = self.expr(a, None, scope)
            eb = self.typed_like(b, ea.type, scope)
            return self.compare(node, head, ea, eb)
        raise CompileError(f"unknown function '{head}'", node.pos)

    def operands(self, nodes, expected: Type | None, scope: dict) -> list:
        """An operator's operands. A literal list such as [1 2] is a point when the attribute or
        another operand is one, as a literal takes its attribute's type."""
        others = [None if isinstance(n, ListLit) else self.expr(n, None, scope) for n in nodes]
        point = (expected is not None and _core(expected) == POINT) or any(
            o is not None and _core(o.type) == POINT for o in others
        )
        return [
            o if o is not None else self.expr(n, POINT if point else None, scope)
            for n, o in zip(nodes, others, strict=True)
        ]

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
        if self.folding:
            for clause in clauses:
                if not isinstance(clause, Form) or len(clause.items) != 2:
                    break
                if _head(clause) == "else":
                    return self.expr(clause.items[1], branch, scope)
                c = self.expr(clause.items[0], BOOL, scope)
                if not c.known:
                    break
                if c.value:
                    return self.expr(clause.items[1], branch, scope)
        for clause in clauses:
            if not isinstance(clause, Form) or len(clause.items) != 2:
                raise CompileError("a cond clause is (test value)", clause.pos)
        clauses = cast("list[Form]", clauses)
        # With nothing outside to give a type, a literal list takes the other values' type, so the
        # values that are not literal lists are compiled first.
        values: dict[int, Expr] = {}
        if branch is None and any(isinstance(cl.items[1], ListLit) for cl in clauses):
            for k in reversed(range(len(clauses))):
                if not isinstance(clauses[k].items[1], ListLit):
                    values[k] = self.expr(clauses[k].items[1], None, scope)
            known = [v for v in values.values() if v.type != RECURSING]
            if known:
                given = _maybe(_inner(known[0].type))
                for k, cl in enumerate(clauses):
                    if k not in values:
                        values[k] = self.expr(cl.items[1], given, scope)
        for k in reversed(range(len(clauses))):
            clause = clauses[k]
            v = values[k] if k in values else self.expr(clause.items[1], branch, scope)
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
        if any(_core(a.type) == POINT or isinstance(_core(a.type), ListT) for a in args):
            return self.itemwise(pos, op, args)
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
            # A value known when compiling is none or not; if not, its type has no none.
            return ed if ex.value is None else replace(ex, type=_inner(ex.type))
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


def _value_part(core: Type, v, name: str):
    if core == COMPLEX:
        return complex(v).real if name == "re" else complex(v).imag
    if core == COLOR:
        k = "rgba".index(name)
        return int(v[1 + 2 * k : 3 + 2 * k], 16) / 255
    if core == STRING:
        return len(v)
    return v[name]


def _duration(step) -> float:
    """How long a step takes: a move its duration, in-order the sum, at-once the longest."""
    if step[0] == "move":
        return step[3]
    if step[0] == "wait":
        return step[1]
    if step[0] == "loop":
        return float("inf") if step[1] is None else step[1] * _duration(step[2])
    parts = [_duration(s) for s in step[1:]]
    if step[0] == "in-order":
        return sum(parts)
    return max(parts, default=0)


def _result(b: Builtin) -> Type:
    return Maybe(b.result) if b.undefined is not None else b.result


def _round(x, attributes=None):
    """Halves away from zero, on the number's shortest decimal form (reference.md,
    "Rounding"); a negative number of attributes rounds to tens, hundreds, …."""
    step = Decimal(1).scaleb(-(attributes or 0))
    v = Decimal(repr(float(x))).quantize(step, rounding=ROUND_HALF_UP)
    return int(v) if attributes is None else float(v)


def _log(x, base=None):
    if x <= 0 or (base is not None and (base <= 0 or base == 1)):
        raise Undefined
    return math.log(x) if base is None else math.log(x, base)


def _log_undefined(ranges) -> bool:
    x = ranges[0]
    if x[0] <= 0:
        return True
    if len(ranges) == 2:
        b = ranges[1]
        return b[0] <= 0 or b[0] <= 1 <= b[1]
    return False


def _lerp(a, b, t):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * t for x, y in zip(a, b, strict=True))
    return a + (b - a) * t


def _scale(sx, sy=None):
    return (sx, 0, 0, sx if sy is None else sy, 0, 0)


def _in_order(steps: list) -> tuple:
    """An animation's one step: several in a row are one in-order."""
    return steps[0] if len(steps) == 1 else ("in-order", *steps)


def _is_literal(node: Node) -> bool:
    if isinstance(node, (IntLit, RatioLit, RealLit, ComplexLit, StrLit, BoolLit, NoneLit)):
        return True
    return isinstance(node, ListLit) and all(_is_literal(i) for i in node.items)


def _with_const(t: Type) -> Type:
    if isinstance(t, Maybe):
        return Maybe(_with_const(t.inner))
    if _is_const(t):
        return t
    if isinstance(t, Refine):
        return replace(t, constraints=(*t.constraints, ("const",)))
    return Refine(t, (("const",),))


def _is_step_ease(ease) -> bool:
    return isinstance(ease, tuple) and ease[0] == "step-ease"


def _ease_value(attribute: Attribute):
    """An ease as a move carries it: its name, ("step", n), or ("func", id)."""
    return ("func", attribute.expr.args[0]) if attribute.expr is not None else attribute.value


def _name_text(node: Name) -> str:
    out = ""
    for part in node.parts:
        if isinstance(part, str):
            out += f".{part}" if out else part
        else:
            out += f"[{getattr(part, 'value', '…')}]"
    return out


def _get(scope: dict, name: str) -> Expr:
    v = scope[name]
    return v() if callable(v) else v


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
    """Whether attr, or an attribute it writes (pos is x and y), is already in given."""
    attributes = {"x", "y"} if attr == "pos" else {attr}
    return any(a in given or (a in ("x", "y") and "pos" in given) for a in attributes)


def _dot(node: Node, attr: str) -> Form:
    """(. node attr), built by the compiler."""
    return Form((Name((".",), node.pos), node, Name((attr,), node.pos)), node.pos)


def _coordinates(attr: str, node: Node, scope: dict) -> dict:
    """A group's argument as defaults by attribute: pos becomes its x and its y, so a member or an
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


def _value_type(attribute: Attribute) -> Type:
    return (
        attribute.expr.type
        if attribute.expr is not None
        else (NONE if attribute.value is None else attribute.type)
    )


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
    # Numbers broaden, so two numbers meet at the broader of their types, without narrowing.
    if _core(a) in NUMBERS and _core(b) in NUMBERS:
        return max(_core(a), _core(b), key=NUMBERS.index)
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


def _range_of(op: str, ranges: Sequence[Range]) -> Range:
    if any(r is None for r in ranges):
        return None
    ranges = cast("Sequence[tuple[float, float]]", ranges)
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
    if op == "^":
        return _power_range(ranges[0], ranges[1])
    # Any other function gives its whole range (type-system.md, "What the compiler proves"),
    # which for a number with no limit of its own is ±10^150.
    return UNBOUNDED


def _power_range(base: tuple[float, float], exp: tuple[float, float]) -> Range:
    """x^y over its inputs' ranges. For x >= 0, log(x^y) = y log x, so its extremes are at the
    corners; a negative base only has a value at a whole exponent known when compiling."""

    def at(x: float, y: float) -> float:
        try:
            return math.pow(x, y)
        except (OverflowError, ValueError, ZeroDivisionError):
            return math.copysign(MAX_REAL, x) if x != 0 else MAX_REAL

    if base[0] >= 0:
        ends = [at(x, y) for x in base for y in exp]
        return (min(ends), max(ends))
    if exp[0] == exp[1] and float(exp[0]).is_integer():
        n = exp[0]
        ends = [at(base[0], n), at(base[1], n)]
        if base[0] < 0 < base[1]:
            ends.append(at(0.0, n) if n > 0 else 1.0)
        return (min(ends), max(ends))
    return WHOLE


def _with_length(t: Type, n: int) -> Type:
    if isinstance(t, Maybe):
        return Maybe(_with_length(t.inner, n))
    if isinstance(t, Refine):
        return replace(t, constraints=(*t.constraints, ("length", n)))
    return Refine(t, (("length", n),))


def _with_range(t: Type, r: Range) -> Type:
    """t narrowed to the range r, where r tells more than t's own range."""
    if r is None or _core(t) not in NUMBERS[:3] or _may_be_none(t):
        return t
    have = _type_range(t) or WHOLE
    cs = []
    if r[0] > max(have[0], -LIMIT):
        cs.append((">=", r[0]))
    if r[1] < min(have[1], LIMIT):
        cs.append(("<=", r[1]))
    if not cs:
        return t
    if isinstance(t, Refine):
        return replace(t, constraints=(*t.constraints, *cs))
    return Refine(t, tuple(cs))


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
_SAMPLES: dict[Type, object] = {INT: 1, RATIO: 1.5, REAL: 1.5, STRING: "a"}


def _check_spec(t: Type, spec: str, pos: Pos) -> None:
    if not spec:
        return
    base = _base(t)
    base = _base(base.inner) if isinstance(base, Maybe) else base
    try:
        format(_SAMPLES[base], spec)
    except (KeyError, ValueError, TypeError):
        raise CompileError(f"'{spec}' is not a format for a {t}", pos) from None


_SPEC = re.compile(r"(?:.?[<>=^])?[-+ ]?z?#?0?\d*[,_]?(?:\.(\d+))?([eEfFgGn%]?)$")


def _preround(x: float, spec: str) -> float:
    """x rounded, halves away from zero on its shortest decimal form, to the digits spec keeps,
    so that formatting the result, which rounds halves to even on its binary value, changes
    nothing more (reference.md, "Rounding")."""
    m = _SPEC.match(spec)
    if m is None or x == 0 or not math.isfinite(x):
        return x
    precision, kind = m.group(1), m.group(2)
    p = int(precision) if precision is not None else None
    d = Decimal(repr(x))
    if kind in ("f", "F", "%"):
        attributes = (6 if p is None else p) + (2 if kind == "%" else 0)
    elif kind in ("e", "E"):
        attributes = (6 if p is None else p) - d.adjusted()
    elif kind in ("g", "G", "n") or p is not None:
        attributes = max(6 if p is None else p, 1) - 1 - d.adjusted()
    else:
        return x
    wide = Context(prec=max(d.adjusted() + attributes + 2, 1), rounding=ROUND_HALF_UP)
    return float(d.quantize(Decimal(1).scaleb(-attributes), context=wide))


def _show_value(t: Type, v, spec: str) -> str:
    """A value shown in a string. Halves round away from zero on the number's shortest
    decimal form (reference.md, "Numbers"), so 2.675 to two attributes is 2.68."""
    base = _base(t)
    if base == INT:
        return format(int(v), spec)
    if base in (RATIO, REAL):
        if not spec:
            return repr(float(v))
        return format(_preround(float(v), spec), spec)
    if base == BOOL:
        return "True" if v else "False"
    if base == POINT:
        return "(" + ", ".join(repr(float(x)) for x in v) + ")"
    return format(v, spec) if spec else str(v)


def _fold(op: str, vals: list):
    # A ratio meeting a real broadens to a real first, as the runtime computes it.
    if any(isinstance(v, float) for v in vals):
        vals = [float(v) if isinstance(v, Fraction) else v for v in vals]
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
