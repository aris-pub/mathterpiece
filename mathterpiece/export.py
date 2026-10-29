"""Writes a compiled model as JSON for the backends.

Every reference is resolved here, so backends never look up names: expressions read
[object id, attribute] pairs, motif parameters, and function arguments directly. A read of a
position from another coordinate frame says which frame to convert into.
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from mathterpiece.compiler import ARITHMETIC, COMPARISONS, PROPERTIES, _expected_type
from mathterpiece.matrix import Matrix
from mathterpiece.model import (
    Bound,
    Button,
    Canvas,
    Circle,
    Control,
    Ellipse,
    Free,
    Group,
    Inherit,
    Line,
    Local,
    Model,
    Motif,
    Obj,
    Play,
    Real,
    Rect,
    Root,
    Slider,
    State,
    Steps,
    Text,
    Triangle,
    View,
    attributes,
    local_names,
    variadic,
)
from mathterpiece.nodes import (
    BoolLit,
    ComplexLit,
    Form,
    InterpStrLit,
    IntLit,
    ListLit,
    Name,
    Node,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.stdlib import STDLIB

FORMAT_VERSION = 1
AXES = {"x": 0, "y": 1, "z": 2}
KINDS: dict[type[Obj], str] = {
    Real: "real",
    Local: "value",
    Root: "root",
    Group: "group",
    Motif: "motif",
    Circle: "circle",
    Rect: "rect",
    Ellipse: "ellipse",
    Line: "line",
    Triangle: "triangle",
    Text: "text",
    Canvas: "canvas",
    Slider: "slider",
    Button: "button",
    Steps: "steps",
    Play: "play",
    State: "state",
}
OPERATORS = ARITHMETIC | set(COMPARISONS) | {"^", "mod", "abs", "transform"}


def to_json(model: Model) -> dict:
    return _Writer(model).write()


# Where an expression is evaluated: who self is, which motif body its names resolve in, which
# container's coordinates it reads positions in, and the function arguments and let names in
# scope (objects marks the arguments that hold objects).
@dataclass(frozen=True)
class _Context:
    me: Obj | None = None
    around: Motif | None = None
    frame: Obj | None = None
    env: frozenset[str] = frozenset()
    objects: frozenset[str] = frozenset()
    types: tuple[tuple[str, str], ...] = ()


class _Writer:
    def __init__(self, model: Model):
        self.model = model
        self.ids: dict[int, int] = {}
        self.order: list[Obj] = []
        self.parent: dict[int, Obj | None] = {}
        self.enclosing: dict[int, Motif | None] = {}
        self.paths: dict[int, str] = {}
        for obj in model:
            self.collect(obj, None, None, None)
        for obj in list(self.order):
            if isinstance(obj, Button) and obj.state is not None:
                self.collect(obj.state, None, None, None)

    def collect(self, obj: Obj, parent: Obj | None, around: Motif | None, prefix: str | None):
        if id(obj) in self.ids:
            return
        self.ids[id(obj)] = len(self.order)
        self.order.append(obj)
        self.parent[id(obj)] = parent
        self.enclosing[id(obj)] = around
        if prefix is not None and obj.name is not None:
            self.paths[id(obj)] = f"{prefix}.{obj.name}"
        if isinstance(obj, View):
            return
        if isinstance(obj, Motif):
            inner = self.paths.get(id(obj), obj.name) if obj.name is not None else None
            if prefix is None and obj.name is not None:
                inner = obj.name
            for member in obj.members:
                self.collect(member, obj, obj, inner)
        elif isinstance(obj, Group):
            for member in obj.members:
                self.collect(member, obj, around, prefix)

    def id(self, obj: Obj) -> int:
        return self.ids[id(obj)]

    def write(self) -> dict:
        objects = [self.object(obj) for obj in self.order]
        functions = {
            key: {
                "params": [[p, _plain(d)] for p, d in fn.params],
                "body": self.expr(fn.body, _function_context(fn)),
            }
            for key, fn in self.model.functions.items()
        }
        names = {}
        for obj in self.order:
            if obj.name is not None and id(obj) not in self.paths and ":" not in obj.name:
                if obj.name in self.model and self.model[obj.name] is obj:
                    names[obj.name] = self.id(obj)
        for key in ("π", "τ", "∞"):
            if key in self.model:
                names[key] = self.id(self.model[key])
        for obj in self.order:
            if id(obj) in self.paths:
                names[self.paths[id(obj)]] = self.id(obj)
        doc = {
            "mtp": FORMAT_VERSION,
            "objects": objects,
            "functions": functions,
            "names": names,
            "depends": {},
        }
        doc["depends"] = _depends(doc)
        return doc

    def context(self, obj: Obj) -> _Context:
        if isinstance(obj, Local):
            owner = obj.owner
            if owner is None:
                return _Context()
            if obj.inside:
                assert isinstance(owner, Motif)
                return _Context(around=owner, frame=owner)
            return _Context(owner, self.enclosing.get(id(owner)), self.parent.get(id(owner)))
        if isinstance(obj, (State, Control)):
            return _Context()
        return _Context(obj, self.enclosing.get(id(obj)), self.parent.get(id(obj)))

    def object(self, obj: Obj) -> dict:
        out: dict[str, Any] = {"id": self.id(obj), "kind": KINDS[type(obj)], "name": obj.name}
        parent = self.parent.get(id(obj))
        if parent is not None:
            out["parent"] = self.id(parent)
        ctx = self.context(obj)
        out["attrs"] = {
            attr: self.attr(obj, attr, getattr(obj, f.name), ctx)
            for attr, f in attributes(type(obj)).items()
            if variadic(type(obj)) is not f
        }
        if isinstance(obj, Group | Motif) and not isinstance(obj, View):
            out["members"] = [self.id(m) for m in obj.members]
        if isinstance(obj, Motif):
            out["motif"] = obj.kind
            out["params"] = {p: self.attr(obj, p, v, ctx) for p, v in obj.params.items()}
        if isinstance(obj, Local):
            out["type"] = obj.type
        if isinstance(obj, Canvas):
            out["shows"] = [self.id(m) for m in obj.members]
        if isinstance(obj, State):
            out["conditions"] = [self.expr(c, ctx) for c in obj.conditions]
            out["moves"] = (
                None
                if obj.problem is not None
                else [[self.id(o), a, self.expr(e, ctx)] for o, a, e in obj.moves]
            )
        if isinstance(obj, Slider):
            assert obj.target is not None
            out["target"] = [self.id(obj.target), obj.attr]
            out["type"] = obj.kind
        if isinstance(obj, Button):
            assert obj.state is not None
            out["state"] = self.id(obj.state)
        if isinstance(obj, Steps):
            out["states"] = [self.id(s) for s in obj.states]
        if isinstance(obj, Play):
            out["start"] = None if obj.start is None else self.id(obj.start)
            out["steps"] = []
            for step in obj.steps:
                if step.state is None:
                    out["steps"].append(["wait", step.duration.value])
                else:
                    to = ["to", self.id(step.state), step.duration.value, step.ease.value]
                    out["steps"].append(to)
        return out

    def attr(self, obj: Obj, attr: str, value: Any, ctx: _Context) -> Any:
        if isinstance(value, Free):
            return _plain(value.value)
        if isinstance(value, Bound):
            return self.expr(value.expr, ctx)
        assert isinstance(value, Inherit)
        around = self.enclosing.get(id(obj))
        if around is None:
            return _plain(attributes(type(obj))[attr].default.value)
        return ["read", self.id(around), attr]

    def expr(self, node: Node, ctx: _Context) -> Any:
        if isinstance(node, (IntLit, RatioLit, RealLit)):
            return float(node.value)
        if isinstance(node, ComplexLit):
            return ["complex", node.value.real, node.value.imag]
        if isinstance(node, (BoolLit, StrLit)):
            return node.value
        if isinstance(node, ListLit):
            items = [self.expr(item, ctx) for item in node.items]
            plain = all(isinstance(i, float) for i in items)
            return items if plain else ["list", *items]
        if isinstance(node, InterpStrLit):
            parts: list[Any] = ["str"]
            for part in node.parts:
                if isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(["show", self.name(part, ctx), self.type_of(part, ctx)])
            return parts
        if isinstance(node, Name):
            return self.name(node, ctx)
        assert isinstance(node, Form)
        return self.call(node, ctx)

    def call(self, node: Form, ctx: _Context) -> Any:
        head = node.items[0]
        assert isinstance(head, Name) and isinstance(head.parts[0], str)
        op = head.parts[0]
        args = node.items[1:]
        if op == "cond":
            clauses = []
            for clause in args:
                assert isinstance(clause, Form)
                test, value = clause.items
                is_else = isinstance(test, Name) and test.parts == ("else",)
                clauses.append([True if is_else else self.expr(test, ctx), self.expr(value, ctx)])
            return ["cond", *clauses]
        if op == "let":
            pairs, body = args
            assert isinstance(pairs, Form)
            out = []
            inner = ctx
            for pair in pairs.items:
                assert isinstance(pair, Form)
                key, value = pair.items
                assert isinstance(key, Name) and isinstance(key.parts[0], str)
                out.append([key.parts[0], self.expr(value, inner)])
                inner = _Context(
                    inner.me,
                    inner.around,
                    inner.frame,
                    inner.env | {key.parts[0]},
                    inner.objects - {key.parts[0]},
                    inner.types,
                )
            return ["let", out, self.expr(body, inner)]
        resolved = [self.expr(a, ctx) for a in args]
        if op == "if":
            return ["if", *resolved]
        if op in OPERATORS:
            return [op, *resolved]
        if op in self.model.functions or op in STDLIB:
            return ["call", op, *resolved]
        raise ValueError(f"cannot write the operation {op!r}")

    # A name, resolved the way the evaluator would look it up.
    def name(self, node: Name, ctx: _Context) -> Any:
        first, *rest = node.parts
        assert isinstance(first, str)
        if first in ctx.env:
            if first in ctx.objects:
                return self.parts_of(["arg", first], rest, ctx, dynamic=True)
            return self.list_parts(["arg", first], rest, ctx)
        if first == "self":
            assert ctx.me is not None
            obj: Obj = ctx.me
        elif ctx.around is not None and first in ctx.around.params:
            return self.list_parts(["param", self.id(ctx.around), first], rest, ctx)
        elif ctx.around is not None and first in local_names(ctx.around):
            obj = local_names(ctx.around)[first]
        else:
            obj = self.model[first]
        return self.parts_of(obj, rest, ctx)

    def parts_of(self, obj: Any, rest: list, ctx: _Context, dynamic: bool = False) -> Any:
        if dynamic:
            if not rest:
                return obj
            part = rest[0]
            assert isinstance(part, str)
            return self.list_parts(["read", obj, part], rest[1:], ctx)
        for i, part in enumerate(rest):
            if isinstance(obj, (Real, Local)):
                return self.list_parts(["read", self.id(obj), "value"], rest[i:], ctx)
            if isinstance(part, str):
                if isinstance(obj, Motif) and part in obj.params:
                    return self.list_parts(["param", self.id(obj), part], rest[i + 1 :], ctx)
                if isinstance(obj, Motif) and part in local_names(obj):
                    obj = local_names(obj)[part]
                    continue
                if isinstance(obj, Group) and part not in attributes(type(obj)):
                    return ["splice", *(self.read(m, part, ctx) for m in obj.members)]
                return self.list_parts(self.read(obj, part, ctx), rest[i + 1 :], ctx)
            assert isinstance(obj, Group) and isinstance(part, IntLit)
            obj = obj.members[part.value]
        if isinstance(obj, (Real, Local)):
            return ["read", self.id(obj), "value"]
        return ["obj", self.id(obj)]

    def read(self, obj: Obj, attr: str, ctx: _Context) -> list:
        out: list[Any] = ["read", self.id(obj), attr]
        point = attr in ("x", "y", "pos") or (
            attr in PROPERTIES.get(type(obj), {}) and attr not in ("size", "r")
        )
        here = self.parent.get(id(obj))
        if point and here is not ctx.frame:
            out.append(None if ctx.frame is None else self.id(ctx.frame))
        return out

    def list_parts(self, base: Any, rest: list, ctx: _Context) -> Any:
        for part in rest:
            if isinstance(part, str):
                base = ["part", base, AXES[part]]
            elif isinstance(part, IntLit):
                base = ["part", base, part.value]
            else:
                base = ["part", base, self.expr(part, ctx)]
        return base

    # The type a name shows as in a string, from what it refers to.
    def type_of(self, node: Name, ctx: _Context) -> str:
        first, *rest = node.parts
        assert isinstance(first, str)
        known = dict(ctx.types)
        if first in ctx.env:
            return known.get(first, "real") if not rest else "real"
        if ctx.around is not None and first in ctx.around.params and not rest:
            return ctx.around.param_types.get(first, "real")
        if first == "self":
            obj: Obj | None = ctx.me
        elif ctx.around is not None and first in local_names(ctx.around):
            obj = local_names(ctx.around)[first]
        else:
            obj = self.model[first] if first in self.model else None
        for part in rest:
            if isinstance(obj, Motif) and isinstance(part, str) and part in obj.params:
                return obj.param_types.get(part, "real")
            if isinstance(obj, Motif) and isinstance(part, str) and part in local_names(obj):
                obj = local_names(obj)[part]
                continue
            if isinstance(obj, (Real, Local)):
                return "real"
            if isinstance(part, str) and obj is not None:
                if part in PROPERTIES.get(type(obj), {}):
                    return PROPERTIES[type(obj)][part]
                if part == "pos":
                    return "list2"
                if part in attributes(type(obj)):
                    return _expected_type(type(obj), part)
            return "real"
        if isinstance(obj, Local):
            return obj.type
        return "real"


def _function_context(fn) -> _Context:
    names = frozenset(p for p, _ in fn.params)
    objects = frozenset(p for p, d in fn.params if d is None)
    types = tuple((p, _type_of_value(d)) for p, d in fn.params if d is not None)
    return _Context(env=names, objects=objects, types=types)


def _type_of_value(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, Fraction):
        return "ratio"
    if isinstance(value, str):
        return "str"
    if isinstance(value, tuple):
        return f"list{len(value)}"
    return "real"


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float, Fraction)):
        return float(value)
    if isinstance(value, complex):
        return ["complex", value.real, value.imag]
    if isinstance(value, tuple):
        return [float(v) for v in value]
    if isinstance(value, Matrix):
        (a, b, c), (d, e, f), _ = value.rows
        return [float(v) for v in (a, b, c, d, e, f)]
    raise ValueError(f"cannot write the value {value!r}")


# For each value, the values computed from it. A position read from another frame, and an
# object passed as a point, also depend on the frames involved.
def _depends(doc: dict) -> dict[str, list[str]]:
    objects = doc["objects"]

    def chain(i: int | None) -> list[tuple[int, str]]:
        out = []
        while i is not None:
            out += [(i, "x"), (i, "y"), (i, "transform")]
            i = objects[i].get("parent")
        return out

    def reads(expr: Any, seen: frozenset[str] = frozenset()) -> set[tuple[int, str]]:
        found: set[tuple[int, str]] = set()
        if not isinstance(expr, list) or not expr or not isinstance(expr[0], str):
            if isinstance(expr, list):
                for item in expr:
                    found |= reads(item, seen)
            return found
        op = expr[0]
        if op == "read" and isinstance(expr[1], int):
            found.add((expr[1], expr[2]))
            if len(expr) == 4:
                found |= {(expr[1], "x"), (expr[1], "y")}
                found |= set(chain(objects[expr[1]].get("parent"))) | set(chain(expr[3]))
        elif op == "param":
            found.add((expr[1], expr[2]))
        elif op == "obj":
            found |= {(expr[1], "x"), (expr[1], "y")} | set(chain(objects[expr[1]].get("parent")))
        elif op == "call" and expr[1] in doc["functions"] and expr[1] not in seen:
            body = doc["functions"][expr[1]]["body"]
            found |= reads(body, seen | {expr[1]})
        for item in expr[1:]:
            found |= reads(item, seen)
        return found

    depends: dict[str, set[str]] = {}
    for o in objects:
        values = {**o.get("attrs", {}), **o.get("params", {})}
        for attr, value in values.items():
            for i, a in reads(value):
                if (i, a) != (o["id"], attr):
                    depends.setdefault(f"{i}.{a}", set()).add(f"{o['id']}.{attr}")
    return {
        key: sorted(vals, key=lambda s: (int(s.split(".")[0]), s)) for key, vals in depends.items()
    }
