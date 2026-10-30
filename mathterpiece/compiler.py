import functools
import math
import operator
import sys
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, get_args, get_origin

from mathterpiece.matrix import Matrix, compose
from mathterpiece.model import (
    PYTHON_FRAMES,
    RECURSION_LIMIT,
    Bound,
    Button,
    Canvas,
    Circle,
    Drag,
    Ellipse,
    Free,
    Function,
    Group,
    Inherit,
    Line,
    Local,
    Model,
    Motif,
    Obj,
    Play,
    Readout,
    Real,
    Rect,
    Root,
    Slider,
    State,
    Steps,
    Styled,
    Text,
    TourStep,
    Triangle,
    View,
    Visual,
    attributes,
    local_names,
    variadic,
)
from mathterpiece.nodes import (
    BoolLit,
    ComplexLit,
    Field,
    Form,
    InterpStrLit,
    IntLit,
    ListLit,
    Name,
    Node,
    Pos,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.parse import ParseError, parse_name
from mathterpiece.stdlib import (
    STDLIB,
    add,
    divide_any,
    multiply,
    negate,
    power,
    show,
    subtract,
)
from mathterpiece.stdlib import call as stdlib_call

BUILTINS = [
    (("pi", "π"), math.pi),
    (("tau", "τ"), math.tau),
    (("euler",), math.e),
    (("infty", "∞"), math.inf),
]

NUMERIC = ["int", "ratio", "real", "complex"]
# The type of a recursive call while its function's result type is still being worked out. It
# fits wherever a value is expected.
PENDING = "pending"
PY_TYPES = {float: "real", str: "str", bool: "bool", Matrix: "transform"}
ARITHMETIC = {"+", "-", "*", "/"}
COMPARISONS: dict[str, Callable[[Any, Any], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "=": operator.eq,
    "!=": operator.ne,
}


@dataclass(frozen=True)
class FormSpec:
    cls: type[Obj]
    positional: tuple[str, ...] = ()


# Style attributes that an object inside a motif takes from the motif when it leaves them
# unset. Opacity is not among them because it multiplies down the tree instead.
INHERITED = ("fill", "stroke", "stroke-width", "fill-opacity", "stroke-opacity")
LITERAL_NODES: dict[str, Callable[..., Node]] = {
    "int": IntLit,
    "ratio": RatioLit,
    "real": RealLit,
    "complex": ComplexLit,
    "bool": BoolLit,
    "str": StrLit,
}

# Heads the compiler reads specially. Everything else, like circle or dist, is standard library.
SYNTAX = {
    "motif",
    "params",
    "repeat",
    "ref",
    "if",
    "cond",
    "else",
    "transform",
    "let",
    "const",
    "func",
}

FORMS = {
    "circle": FormSpec(Circle),
    "rect": FormSpec(Rect),
    "ellipse": FormSpec(Ellipse),
    "line": FormSpec(Line),
    "triangle": FormSpec(Triangle),
    "text": FormSpec(Text, ("value",)),
    "real": FormSpec(Real, ("value",)),
    "group": FormSpec(Group),
    "canvas": FormSpec(Canvas),
    "readout": FormSpec(Readout, ("value",)),
}


class CompileError(Exception):
    def __init__(self, msg: str, pos: Pos):
        super().__init__(f"{pos}: {msg}")
        self.msg = msg
        self.pos = pos


@dataclass(frozen=True)
class Const:
    value: object
    type: str


@dataclass(frozen=True)
class Dyn:
    type: str


@dataclass(frozen=True)
class Spread:
    types: tuple[str, ...]


@dataclass(frozen=True)
class ObjRef:
    obj: Obj


@dataclass(frozen=True)
class SelfRef:
    cls: type[Obj]


@dataclass(frozen=True)
class MotifSpec:
    params: dict[str, Const]
    body: tuple[Node, ...]
    # The motifs defined before this one, which is what its body's heads refer to.
    motifs: dict[str, "MotifSpec"]
    # The default (transform ...) of each instance, compiled in the body so it sees the params.
    transform: Form | None = None


Value = Const | Dyn | Spread | ObjRef | SelfRef


# A let name whose value is only known when drawing; stored expressions read the hidden value.
@dataclass(frozen=True)
class LetRef:
    hidden: str
    type: str


# An object passed to a function, and the call site's name for it, written in for the parameter.
@dataclass(frozen=True)
class ArgRef:
    value: "ObjRef | SelfRef"
    node: Name


@dataclass(frozen=True)
class FuncSpec:
    # A parameter without a default takes an object.
    params: dict[str, "Const | None"]
    body: Node
    # The functions and consts defined before this one (and itself), which its body sees.
    funcs: dict[str, "FuncSpec"]
    consts: dict[str, "Const"]
    name: str
    # Its name in the model's functions.
    key: str


# The let values created while one object is being defined, which that object will own.
@dataclass
class Frame:
    locals: list[Local]
    inside: bool = False


Env = dict[str, "int | SelfRef | Const | Dyn | LetRef | ArgRef"]
# The names a motif body can see besides globals: its parameters and its members so far.
Scope = dict[str, Value]


def compile_model(forms: tuple[Form, ...]) -> Model:
    sys.setrecursionlimit(max(sys.getrecursionlimit(), PYTHON_FRAMES))
    return _Compiler(forms).compile()


def _head(node: Node) -> str | None:
    if isinstance(node, Form) and isinstance(node.items[0], Name):
        parts = node.items[0].parts
        if len(parts) == 1 and isinstance(parts[0], str):
            return parts[0]
    return None


def _defined_names(nodes, heads) -> set[str]:
    names: set[str] = set()
    for node in nodes:
        if isinstance(node, Form):
            if _head(node) in heads and len(node.items) > 1 and isinstance(node.items[1], StrLit):
                names.add(node.items[1].value)
            names |= _defined_names(node.items, heads)
    return names


# The attributes of its own object that an expression reads. A bare self is a point, as in
# (dist self a), so it reads x and y.
# A let value read by name brings along what its own expression reads.
def _self_reads(
    node: Node | Field | str,
    lets: dict[str, set[str]],
    props: dict[str, set[str]] | None = None,
) -> set[str]:
    props = props or {}
    if isinstance(node, Name):
        first = node.parts[0]
        reads: set[str] = set(lets.get(first, set()) if isinstance(first, str) else ())
        if node.parts[0] == "self":
            second = node.parts[1] if len(node.parts) > 1 else None
            if not isinstance(second, str) or second == "pos":
                reads |= {"x", "y"}
            else:
                reads |= props.get(second, {second})
        for part in node.parts[1:]:
            if not isinstance(part, str):
                reads |= _self_reads(part, lets, props)
        return reads
    if isinstance(node, Field):
        return _self_reads(node.name, lets, props)
    if isinstance(node, (Form, ListLit, InterpStrLit)):
        parts = node.parts if isinstance(node, InterpStrLit) else node.items
        return set().union(*(_self_reads(p, lets, props) for p in parts))
    return set()


# Without forward references, objects cannot depend on each other in a loop, so a cycle can only
# run through self, inside one object.
def _check_cycles(
    name: str | None,
    given: dict[str, tuple[Any, Pos]],
    owned: list[Local],
    props: dict[str, set[str]] | None = None,
):
    lets: dict[str, set[str]] = {}
    for local in owned:
        assert isinstance(local.value, Bound) and local.name is not None
        lets[local.name] = _self_reads(local.value.expr, lets, props)
    reads = {
        attr: _self_reads(value.expr, lets, props) if isinstance(value, Bound) else set()
        for attr, (value, _) in given.items()
    }
    done: set[str] = set()

    def visit(attr: str, path: list[str]):
        if attr in path:
            loop = [*path[path.index(attr) :], attr]
            shown = " -> ".join(f"{name}.{a}" if name is not None else a for a in loop)
            raise CompileError(f"circular dependency: {shown}", given[loop[0]][1])
        if attr in done:
            return
        for dep in sorted(reads.get(attr, set())):
            visit(dep, [*path, attr])
        done.add(attr)

    for attr in reads:
        visit(attr, [])


# A list of n numbers has the type "list{n}". Its parts are read as x, y, z or by index.
AXES = {"x": 0, "y": 1, "z": 2}


def _list_len(t: str) -> int | None:
    return int(t[4:]) if t.startswith("list") and t[4:].isdigit() else None


def _is_literal_type(t: str) -> bool:
    return t in LITERAL_NODES or _list_len(t) is not None


def _literal(value: "Const", pos: Pos) -> Node:
    if _list_len(value.type) is not None:
        assert isinstance(value.value, tuple)
        return ListLit(tuple(RealLit(float(v), pos) for v in value.value), pos)
    return LITERAL_NODES[value.type](value.value, pos)


def _check_pos(attr: str, given, pos: Pos):
    if (attr == "pos" and {"x", "y", "pos"} & given.keys()) or (
        attr in ("x", "y") and "pos" in given
    ):
        raise CompileError("pos sets both x and y, so give pos or x and y, not both", pos)


# The values controls write, read from the source before compiling so that the compiler does not
# fold them. A target written as a plain path gives that path; any other target only gives its
# last name, which then counts as written in every motif instance.
def _control_targets(forms) -> tuple[set[tuple[str, ...]], set[str]]:
    paths: set[tuple[str, ...]] = set()
    anywhere: set[str] = set()

    def visit(node):
        if not isinstance(node, Form):
            return
        if _head(node) == "state":
            for cond in node.items[2:]:
                if isinstance(cond, Form) and _head(cond) == "=" and len(cond.items) == 3:
                    for side in cond.items[1:]:
                        if isinstance(side, Name) and all(isinstance(p, str) for p in side.parts):
                            paths.add(tuple(p for p in side.parts if isinstance(p, str)))
        if _head(node) == "on-drag" and len(node.items) > 2:
            target = node.items[2]
            if isinstance(target, Name) and all(isinstance(p, str) for p in target.parts):
                *path, last = [p for p in target.parts if isinstance(p, str)]
                coords = ("x", "y") if last == "pos" else (last,)
                paths.update((*path, c) for c in coords)
        if _head(node) in ("slider", "button") and len(node.items) > 2:
            target = node.items[2]
            if isinstance(target, Name) and all(isinstance(p, str) for p in target.parts):
                paths.add(tuple(p for p in target.parts if isinstance(p, str)))
            elif isinstance(target, Name) and isinstance(target.parts[-1], str):
                anywhere.add(target.parts[-1])
            elif isinstance(target, Form) and _head(target) == "ref":
                arg = target.items[1] if len(target.items) > 1 else None
                if isinstance(arg, StrLit):
                    anywhere.add(arg.value.rsplit(".", 1)[-1])
        for item in node.items:
            visit(item)

    for form in forms:
        visit(form)
    return paths, anywhere


# The values a moved attribute stands for: a position is its x and y.
def _covers(attr: str) -> set[str]:
    return {"x", "y"} if attr == "pos" else {attr}


EASES = ("linear", "ease-in", "ease-out", "ease-in-out")
CONTROLS: dict[str, type[Obj]] = {"slider": Slider, "button": Button, "steps": Steps, "play": Play}


def _duration(value: "Value", pos: Pos) -> float:
    if not (isinstance(value, Const) and isinstance(value.value, (int, Fraction, float))):
        raise CompileError("a duration is a number of seconds known at compile time", pos)
    if isinstance(value.value, bool) or value.value < 0:
        raise CompileError("a duration cannot be negative", pos)
    return float(value.value)


def _ease(value: "Value", pos: Pos) -> str:
    if not (isinstance(value, Const) and value.value in EASES):
        raise CompileError(f"ease is one of {', '.join(EASES)}", pos)
    assert isinstance(value.value, str)
    return value.value


def _check_reachable(state: "State", pos: Pos):
    if state.problem is not None:
        label = repr(state.name) if state.name is not None else "this state"
        raise CompileError(f"cannot animate to state {label}: {state.problem}", pos)


def _text(node: Node) -> str:
    if isinstance(node, Name):
        return ".".join(p if isinstance(p, str) else "[...]" for p in node.parts)
    return "this value"


def _names_in(node: Node) -> list[Name]:
    if isinstance(node, Name):
        return [node]
    if isinstance(node, (Form, ListLit)):
        return [n for item in node.items for n in _names_in(item)]
    if isinstance(node, InterpStrLit):
        return [p.name if isinstance(p, Field) else p for p in node.parts if not isinstance(p, str)]
    return []


# A value shown in a string: Python's format() with the spec, as in f-strings, or Python's
# default without one.
def _format(value: Any, kind: str, spec: str | None) -> str:
    if not spec:
        return show(value)
    return format(int(value) if kind == "int" else value, spec)


# A sample of each type, to check a format spec at compile time.
SAMPLES: dict[str, Any] = {
    "int": 1,
    "ratio": Fraction(1, 2),
    "real": 1.5,
    "complex": 1 + 2j,
    "str": "a",
    "bool": True,
}


def _check_spec(spec: str, kind: str, pos: Pos):
    sample = SAMPLES.get(kind)
    try:
        if sample is None:
            raise ValueError
        format(sample, spec)
    except (ValueError, TypeError):
        raise CompileError(f"{spec!r} is not a format for a {kind}", pos) from None


def _check_not_syntax(name: str, pos: Pos):
    if name in SYNTAX:
        raise CompileError(f"{name!r} is part of the language and cannot be used as a name", pos)


def _widens_to(src: str, dst: str) -> bool:
    if src == PENDING:
        return True
    if src in NUMERIC and dst in NUMERIC:
        return NUMERIC.index(src) <= NUMERIC.index(dst)
    return src == dst


CONVERT = {"int": int, "ratio": Fraction, "real": float, "complex": complex}


def _convert(value, dst: str):
    return CONVERT[dst](value) if dst in CONVERT else value


def _expected_type(cls: type[Obj], attr: str) -> str:
    (arg,) = get_args(attributes(cls)[attr].type)
    if get_origin(arg) is tuple:
        return f"list{len(get_args(arg))}"
    return PY_TYPES[arg]


# Other ways to write a shape, besides its stored attributes, and their types. Each can also be
# read back, computed from the stored attributes like a Python property.
PROPERTIES: dict[type[Obj], dict[str, str]] = {
    Rect: {"center": "list2", "size": "list2", "from": "list2", "to": "list2"},
    Ellipse: {"center": "list2", "size": "list2"},
    Line: {"from": "list2", "to": "list2"},
    Triangle: {"center": "list2", "r": "real"},
}
# The stored attributes each property is computed from, for finding cycles through self.
PROPERTY_READS: dict[type[Obj], dict[str, set[str]]] = {
    Rect: {
        "center": {"x", "y", "width", "height"},
        "size": {"width", "height"},
        "from": {"x", "y"},
        "to": {"x", "y", "width", "height"},
    },
    Ellipse: {"center": {"x", "y"}, "size": {"rx", "ry"}},
    Line: {"from": {"x", "y", "x1", "y1"}, "to": {"x", "y", "x2", "y2"}},
    Triangle: {"center": {"x", "y", "a", "b", "c"}, "r": {"a", "b", "c"}},
}


class _Compiler:
    def __init__(self, forms: tuple[Form, ...]):
        self.forms = forms
        self.names: dict[str, Obj] = {}
        self.builtins: list[tuple[Obj, tuple[str, ...]]] = []
        self.toplevel: list[Obj] = []
        # Keyed by id, holding the object too: ids of freed objects get reused.
        self.parents: dict[int, tuple[Obj, str]] = {}
        self.motifs: dict[str, MotifSpec] = {}
        self.root: Root | None = None
        self.consts: dict[str, Const] = {}
        # Paths written by controls (such as ("d", "r")), and parameter names written somewhere
        # the compiler cannot tell; these stay reactive instead of being folded.
        self.written: set[tuple[str, ...]] = set()
        self.written_anywhere: set[str] = set()
        # The names of the motif instances whose bodies are being compiled, outermost first.
        self.instance_path: list[str | None] = []
        self.funcs: dict[str, FuncSpec] = {}
        self.functions: dict[str, Function] = {}
        # The functions being compiled, with the type their recursive calls stand for.
        self.active: dict[int, str] = {}
        self.depth = 0
        # How many enclosing branches are never taken; calls there are checked but not folded.
        self.speculative = 0
        self.builtin_names: set[str] = set()
        # How many function bodies are being compiled; inside one, values and objects are hidden.
        self.in_func = 0
        self.scopes: list[Scope] = []
        # Where a definition lands before anything adopts it: the top level, or a motif body.
        self.pools: list[list[Obj]] = [self.toplevel]
        self.frames: list[Frame] = [Frame([])]
        self.locals: list[Local] = []
        # By node id: the bindings of each expression let, or the written-in body of each function
        # call, for writing them into stored expressions. A node inside a repeat is overwritten
        # each iteration, which is fine because each iteration stores its expressions first.
        self.lets: dict[int, dict | Node] = {}

    def compile(self) -> Model:
        self.add_builtins()
        self.written, self.written_anywhere = _control_targets(self.forms)
        for form in self.forms:
            self.toplevel.extend(self.toplevel_item(form, {}))
        if self.root is None:
            raise CompileError(
                "a file needs exactly one scene, even an empty one: (scene _)", Pos(1, 1)
            )
        model = Model()
        for obj, names in self.builtins:
            model.add(obj)
            for alias in names[1:]:
                model.alias(alias, names[0])
        self.settle(self.frames[0], None)
        for obj in [*self.toplevel, *self.locals]:
            model.add(obj)
        model.functions.update(self.functions)
        return model

    def settle(self, frame: Frame, owner: Obj | None):
        for local in frame.locals:
            local.owner = owner
            local.inside = frame.inside
            self.locals.append(local)

    def bindings(self, node: Form, env: Env) -> Env:
        if len(node.items) < 2 or not isinstance(node.items[1], Form):
            raise CompileError("let takes a list of (name value) pairs", node.pos)
        inner = dict(env)
        for pair in node.items[1].items:
            if not (isinstance(pair, Form) and len(pair.items) == 2):
                raise CompileError("a let binding is (name value)", pair.pos)
            key, expr = pair.items
            if not (
                isinstance(key, Name) and len(key.parts) == 1 and isinstance(key.parts[0], str)
            ):
                raise CompileError("a let binding needs a plain name", key.pos)
            name = key.parts[0]
            _check_not_syntax(name, key.pos)
            value = self.value_arg(expr, inner)
            if isinstance(value, Const):
                inner[name] = value
                continue
            inner[name] = LetRef(self.hidden_value(name, expr, inner, value.type), value.type)
        return inner

    # A value only known when drawing, stored once in the model and read by every use.
    def hidden_value(self, label: str, node: Node, env: Env, kind: str) -> str:
        hidden = f"let:{len(self.names)}:{label}"
        stored = self.resolve_refs(_substitute(node, self.constants(env), self.lets), env)
        local = Local(name=hidden, value=Bound(stored), type=kind)
        self.names[hidden] = local
        self.frames[-1].locals.append(local)
        return hidden

    def pos_value(self, node: Node, env: Env) -> tuple[Free | Bound, Free | Bound]:
        value = self.value_arg(node, env)
        if value.type != "list2":
            raise CompileError(f"pos takes a point of two numbers, got {value.type}", node.pos)
        if isinstance(value, Const):
            assert isinstance(value.value, tuple)
            return Free(float(value.value[0])), Free(float(value.value[1]))
        hidden = self.hidden_value("pos", node, env, "list2")
        return Bound(Name((hidden, "x"), node.pos)), Bound(Name((hidden, "y"), node.pos))

    def let_items[T](self, node: Form, env: Env, item: Callable[[Form, Env], list[T]]) -> list[T]:
        inner = self.bindings(node, env)
        out: list[T] = []
        for child in node.items[2:]:
            if not isinstance(child, Form):
                raise CompileError("expected a form in the let body", child.pos)
            out.extend(item(child, inner))
        return out

    def add_builtins(self):
        motifs = {
            f.items[1].value
            for f in self.forms
            if _head(f) == "motif" and len(f.items) > 1 and isinstance(f.items[1], StrLit)
        }
        taken = _defined_names(self.forms, FORMS.keys() | motifs | {"const"})
        for names, value in BUILTINS:
            available = tuple(name for name in names if name not in taken)
            if not available:
                continue
            obj = Real(name=available[0], value=Free(value))
            self.builtins.append((obj, available))
            self.builtin_names |= set(available)
            for name in available:
                self.names[name] = obj

    def register(self, obj: Obj, pos: Pos):
        if obj.name is None:
            return
        if self.scopes:
            scope = self.scopes[-1]
            if obj.name in scope:
                raise CompileError(f"name {obj.name!r} is already defined", pos)
            scope[obj.name] = ObjRef(obj)
            return
        if obj.name in self.names or obj.name in self.consts:
            raise CompileError(f"name {obj.name!r} is already defined", pos)
        self.names[obj.name] = obj

    def toplevel_item(self, form: Form, env: Env) -> list[Obj]:
        head = _head(form)
        if head == "repeat":
            return self.repeat(form, env, self.toplevel_item)
        if head == "let":
            return self.let_items(form, env, self.toplevel_item)
        if head == "motif":
            self.define_motif(form)
            return []
        if head == "const":
            self.define_const(form, env)
            return []
        if head == "func":
            self.define_func(form)
            return []
        if head in CONTROLS or head == "state":
            return [self.control(form, env, head)]
        if head == "on-drag":
            return [self.on_drag(form, env)]
        if head == "scene":
            return [self.scene_form(form, env)]
        if head in self.motifs or (head in FORMS and issubclass(FORMS[head].cls, Visual)):
            raise CompileError(f"{head} is a visual object, so it goes inside the scene", form.pos)
        if head in FORMS:
            return [self.definition(form, env)]
        if head is None:
            raise CompileError("expected a definition", form.pos)
        if head in ARITHMETIC or head == "rand" or head in self.names:
            raise CompileError(f"{head!r} is not a definition", form.pos)
        raise CompileError(f"unknown form {head!r}", form.pos)

    def repeat[T](self, form: Form, env: Env, item: Callable[[Form, Env], list[T]]) -> list[T]:
        if len(form.items) < 3:
            raise CompileError("repeat takes a variable, a count, and a body", form.pos)
        var, count_node, *body = form.items[1:]
        if not (isinstance(var, Name) and len(var.parts) == 1 and isinstance(var.parts[0], str)):
            raise CompileError("the repeat variable must be a name", var.pos)
        _check_not_syntax(var.parts[0], var.pos)
        count = self.expr(count_node, env)
        if not (isinstance(count, Const) and isinstance(count.value, int) and count.type == "int"):
            raise CompileError(
                "the repeat count must be an int known at compile time", count_node.pos
            )
        if count.value < 0:
            raise CompileError("the repeat count cannot be negative", count_node.pos)
        out: list[T] = []
        for i in range(count.value):
            inner = env | {var.parts[0]: i}
            for node in body:
                if not isinstance(node, Form):
                    raise CompileError("expected a form in the repeat body", node.pos)
                out.extend(item(node, inner))
        return out

    def object_name(self, form: Form, env: Env) -> str | None:
        if len(form.items) < 2:
            raise CompileError(f"{_head(form)} needs a name", form.pos)
        node = form.items[1]
        if isinstance(node, StrLit):
            _check_not_syntax(node.value, node.pos)
            return node.value
        if isinstance(node, Name) and node.parts == ("_",):
            return None
        if isinstance(node, InterpStrLit):
            value = self.expr(node, env)
            if isinstance(value, Const):
                _check_not_syntax(str(value.value), node.pos)
                return str(value.value)
            raise CompileError("a name must be known at compile time", node.pos)
        raise CompileError("expected a name: a string, an interpolated string, or _", node.pos)

    def scene_form(self, form: Form, env: Env) -> Root:
        if self.root is not None:
            raise CompileError("a file has exactly one scene", form.pos)
        name = self.object_name(form, env)
        pool: list[Obj] = []
        self.pools.append(pool)
        frame = Frame([])
        self.frames.append(frame)
        try:
            for node in form.items[2:]:
                pool.extend(self.scene_item(node, env))
        finally:
            self.pools.pop()
            self.frames.pop()
        label = repr(name) if name is not None else "the scene"
        members: list[Visual] = []
        for obj in pool:
            assert isinstance(obj, Visual)
            self.parents[id(obj)] = (obj, label)
            members.append(obj)
        root = Root(name=name, members=members)
        self.settle(frame, root)
        self.register(root, form.pos)
        self.root = root
        return root

    def scene_item(self, node: Node, env: Env) -> list[Obj]:
        head = _head(node)
        if isinstance(node, Form) and head == "repeat":
            return self.repeat(node, env, self.scene_item)
        if isinstance(node, Form) and head == "let":
            return self.let_items(node, env, self.scene_item)
        if isinstance(node, Form) and (head in FORMS or head in self.motifs):
            if head in FORMS and not issubclass(FORMS[head].cls, Visual):
                raise CompileError(f"{head} goes outside the scene", node.pos)
            return [self.definition(node, env)]
        if head == "motif":
            raise CompileError("motifs are defined at the top level", node.pos)
        if head == "const":
            raise CompileError("const goes outside the scene", node.pos)
        if head == "scene":
            raise CompileError("a file has exactly one scene", node.pos)
        raise CompileError("the scene holds only visual objects", node.pos)

    # Which free value a control writes: an attribute, a motif parameter, or a real's value.
    def control_target(self, node: Node, env: Env) -> tuple[Obj, str, str, str]:
        found = self.free_value(node, env)
        if isinstance(found, str):
            raise CompileError(found, node.pos)
        return found

    # The free value a name refers to, or why it is not one.
    def free_value(self, node: Node, env: Env) -> tuple[Obj, str, str, str] | str:
        name = self.resolve_refs(node, env)
        if not isinstance(name, Name):
            return "a control's target must be a name, like disk.r"
        text = ".".join(p if isinstance(p, str) else "[...]" for p in name.parts)
        first = name.parts[0]
        if len(name.parts) == 1 and isinstance(first, str) and first in self.consts:
            return f"{text!r} is a const, so a control cannot write it"
        if len(name.parts) == 1:
            obj = self.names.get(first) if isinstance(first, str) else None
            if not isinstance(obj, Real):
                return f"{text!r} is not a value a control can write"
            attr = "value"
        else:
            holder = self.name(Name(name.parts[:-1], name.pos), env)
            last = name.parts[-1]
            if not isinstance(holder, ObjRef) or not isinstance(last, str):
                return f"{text!r} is not a value a control can write"
            obj, attr = holder.obj, last
        if isinstance(obj, Motif) and attr in obj.params:
            current = obj.params[attr]
            kind = self.motifs[obj.kind].params[attr].type
        elif attr == "pos" and {"x", "y"} <= attributes(type(obj)).keys():
            if any(isinstance(getattr(obj, c), Bound) for c in ("x", "y")):
                return f"{text!r} is computed, so a control cannot write it"
            return obj, "pos", "list2", text
        else:
            attrs = attributes(type(obj))
            if attr not in attrs or variadic(type(obj)) is attrs[attr]:
                raise CompileError(f"{obj.name!r} has no attribute {attr!r}", node.pos)
            current = getattr(obj, attrs[attr].name)
            kind = _expected_type(type(obj), attr)
        if isinstance(current, Bound):
            return f"{text!r} is computed, so a control cannot write it"
        return obj, attr, kind, text

    def control(self, form: Form, env: Env, head: str) -> Obj:
        if head == "state":
            return self.state(form, env)
        name = self.object_name(form, env)
        rest = list(form.items[2:])
        values: dict[str, Any] = {}
        fields: dict[str, Any] = {}
        if head == "slider":
            if not rest:
                raise CompileError("slider needs a target, like disk.r", form.pos)
            target, attr, kind, text = self.control_target(rest.pop(0), env)
            if kind not in ("int", "real"):
                raise CompileError(
                    f"a slider writes a number, but {text} is a {kind}", form.items[2].pos
                )
            fields = {"target": target, "attr": attr, "kind": kind}
            values["label"] = Free(text)
        elif head == "button":
            if not rest:
                raise CompileError("button needs a state, or a target and a value", form.pos)
            state = self.state_named(rest[0])
            if state is not None:
                rest.pop(0)
                values["label"] = Free(state.name)
            else:
                state = self.one_condition_state(rest, env, form.pos)
                values["label"] = Free(_text(form.items[2]))
            _check_reachable(state, form.items[2].pos)
            fields = {"state": state}
        elif head == "steps":
            if not rest or _head(rest[0]) != "states":
                raise CompileError("steps needs (states a b ...)", form.pos)
            listed = rest.pop(0)
            assert isinstance(listed, Form)
            states = []
            for item in listed.items[1:]:
                state = self.state_named(item)
                if state is None:
                    raise CompileError("steps lists states by name", item.pos)
                _check_reachable(state, item.pos)
                states.append(state)
            if not states:
                raise CompileError("steps needs at least one state", listed.pos)
            fields = {"states": states}
            values["label"] = Free(name or "")
        elif head == "play":
            fields = self.tour(rest, form.pos)
            rest = [node for node in rest if _head(node) == "label"]
            values["label"] = Free("play")
        cls = CONTROLS[head]
        allowed = set(attributes(cls)) - {"label"} | {"label"}
        given: set[str] = set()
        for node in rest:
            attr_name = _head(node)
            if attr_name not in allowed or not isinstance(node, Form) or len(node.items) != 2:
                raise CompileError(f"unexpected value in {head}", node.pos)
            if attr_name in given:
                raise CompileError(f"attribute {attr_name!r} is given twice", node.pos)
            given.add(attr_name)
            values[attr_name] = self.control_attr(attr_name, node.items[1], env, cls)
        obj = cls(name=name, **fields, **values)
        self.register(obj, form.pos)
        return obj

    def on_drag(self, form: Form, env: Env) -> Drag:
        if len(form.items) < 3:
            raise CompileError(
                "on-drag needs the object to drag and what it moves, like (on-drag u u.pos)",
                form.pos,
            )
        dragged = form.items[1]
        text = _text(dragged)
        found = self.name(dragged, env) if isinstance(dragged, Name) else None
        if not isinstance(found, ObjRef) or not isinstance(found.obj, Visual):
            raise CompileError(f"{text} cannot be dragged: it is not a visual object", dragged.pos)
        node = found.obj
        target_node = form.items[2]
        moved = self.free_value(target_node, env)
        if isinstance(moved, str):
            raise CompileError(moved, target_node.pos)
        if moved[0] is not node or moved[1] not in ("x", "y", "pos"):
            raise CompileError(
                f"the target must be part of {text}'s position: {text}.x, {text}.y or {text}.pos",
                target_node.pos,
            )
        conditions: list[Node] = []
        when: Node | State | None = None
        for item in form.items[3:]:
            head = _head(item)
            if head == "when" and isinstance(item, Form):
                if when is not None:
                    raise CompileError("when is given twice", item.pos)
                if len(item.items) != 2:
                    raise CompileError("when takes one condition or state", item.pos)
                when = self.state_named(item.items[1]) or self.condition(item.items[1], env)
            elif isinstance(item, Form) and head not in COMPARISONS:
                raise CompileError("unexpected value in on-drag", item.pos)
            else:
                conditions.append(self.condition(item, env))
        return Drag(name=None, node=node, target=moved[1], conditions=tuple(conditions), when=when)

    # A condition stored for drawing time; it must be true or false.
    def condition(self, node: Node, env: Env) -> Node:
        value = self.value_arg(node, env)
        if value.type not in ("bool", PENDING):
            raise CompileError("a listener's conditions must be true or false", node.pos)
        return self.resolve_refs(_substitute(node, self.constants(env), self.lets), env)

    def control_attr(self, attr: str, node: Node, env: Env, cls: type[Obj]) -> Free | Bound:
        if attr == "step":
            step = self.value_arg(node, env)
            if isinstance(step, Const) and step.value == "none":
                return Free(None)
            if isinstance(step, Const) and isinstance(step.value, (int, Fraction, float)):
                return Free(float(step.value))
            raise CompileError("step is a number known at compile time, or 'none'", node.pos)
        if attr == "duration":
            return Free(_duration(self.value_arg(node, env), node.pos))
        if attr == "ease":
            return Free(_ease(self.value_arg(node, env), node.pos))
        value = self.attr_value(cls, attr, node, env)
        assert isinstance(value, (Free, Bound))
        return value

    def state_named(self, node: Node) -> State | None:
        if isinstance(node, Name) and len(node.parts) == 1 and isinstance(node.parts[0], str):
            found = self.names.get(node.parts[0])
            return found if isinstance(found, State) else None
        return None

    # The shorthand (button 'b' target value): the state where target equals value.
    def one_condition_state(self, rest: list[Node], env: Env, pos: Pos) -> State:
        target = rest.pop(0)
        if not rest or _head(rest[0]) in ("label", "duration", "ease"):
            raise CompileError("a button needs the value it writes", pos)
        value_node = rest.pop(0)
        condition = Form((Name(("=",), target.pos), target, value_node), target.pos)
        return self.make_state(None, (condition,), env, pos)

    def state(self, form: Form, env: Env) -> State:
        name = self.object_name(form, env)
        conditions = tuple(form.items[2:])
        if not conditions:
            raise CompileError("a state needs at least one condition", form.pos)
        state = self.make_state(name, conditions, env, form.pos)
        self.register(state, form.pos)
        return state

    def make_state(
        self, name: str | None, conditions: tuple[Node, ...], env: Env, pos: Pos
    ) -> State:
        stored = []
        for cond in conditions:
            value = self.value_arg(cond, env)
            if value.type not in ("bool", PENDING):
                raise CompileError("a state's conditions must be true or false", cond.pos)
            stored.append(self.resolve_refs(_substitute(cond, self.constants(env), self.lets), env))
        moves: list[tuple[Obj, str, Node]] = []
        problem = None
        for cond in conditions:
            problem = problem or self.add_move(cond, env, moves)
        if problem is None:
            problem = self.check_reads(moves, env)
        return State(name=name, conditions=tuple(stored), moves=tuple(moves), problem=problem)

    # How one condition is reached: the free side of (= a b) moves to the other side (the left
    # side when both are free). Returns why it cannot be animated to, if it cannot.
    def add_move(self, cond: Node, env: Env, moves: list) -> str | None:
        if not (isinstance(cond, Form) and _head(cond) == "=" and len(cond.items) == 3):
            return "only conditions of the form (= free-value expression) can be animated to"
        left, right = cond.items[1], cond.items[2]
        for side, other in ((left, right), (right, left)):
            found = self.free_value(side, env)
            if isinstance(found, str):
                continue
            obj, attr, kind, text = found
            if any(o is obj and _covers(a) & _covers(attr) for o, a, _ in moves):
                return f"it moves {text} twice"
            value = self.value_arg(other, env)
            if not _widens_to(value.type, kind):
                raise CompileError(f"{text} takes a {kind}, got {value.type}", other.pos)
            stored = self.resolve_refs(_substitute(other, self.constants(env), self.lets), env)
            moves.append((obj, attr, stored))
            return None
        return f"{_text(left)} is computed, so reaching it would mean solving an equation"

    # Targets are worked out once, when a move starts, so a condition may read the value it moves
    # itself ((= r (* 2 r)) doubles r). Reading a value another condition moves would leave the
    # state not holding once both have arrived.
    def check_reads(self, moves: list, env: Env) -> str | None:
        for obj, attr, expr in moves:
            others = {
                (id(o), c) for o, a, _ in moves if not (o is obj and a == attr) for c in _covers(a)
            }
            for name in _names_in(expr):
                found = self.free_value(name, env)
                if isinstance(found, str):
                    continue
                if any((id(found[0]), c) in others for c in _covers(found[1])):
                    return f"one condition reads {found[3]}, which another condition moves"
        return None

    def tour(self, rest: list[Node], pos: Pos) -> dict[str, Any]:
        start = None
        steps: list[TourStep] = []
        for i, node in enumerate(rest):
            head = _head(node)
            if head == "label":
                continue
            if not isinstance(node, Form):
                raise CompileError("a tour step is (wait seconds) or (to state ...)", node.pos)
            if head == "from":
                if i != 0 or len(node.items) != 2:
                    raise CompileError("(from state) comes first, once", node.pos)
                start = self.state_named(node.items[1])
                if start is None:
                    raise CompileError("from names a state", node.pos)
                _check_reachable(start, node.pos)
            elif head == "wait":
                if len(node.items) != 2:
                    raise CompileError("wait takes a number of seconds", node.pos)
                seconds = _duration(self.value_arg(node.items[1], {}), node.items[1].pos)
                steps.append(TourStep("wait", None, Free(seconds)))
            elif head == "to":
                state = self.state_named(node.items[1]) if len(node.items) > 1 else None
                if state is None:
                    raise CompileError("to names a state", node.pos)
                _check_reachable(state, node.pos)
                options = {"duration": Free(0.0), "ease": Free("linear")}
                for option in node.items[2:]:
                    key = _head(option)
                    if key not in options or not isinstance(option, Form) or len(option.items) != 2:
                        raise CompileError(
                            "to takes (duration seconds) and (ease name)", option.pos
                        )
                    value = self.value_arg(option.items[1], {})
                    item = option.items[1].pos
                    options[key] = Free(
                        _duration(value, item) if key == "duration" else _ease(value, item)
                    )
                steps.append(TourStep("to", state, options["duration"], options["ease"]))
            else:
                raise CompileError("a tour step is (wait seconds) or (to state ...)", node.pos)
        if not steps:
            raise CompileError("a tour needs at least one step", pos)
        return {"start": start, "steps": tuple(steps)}

    def define_const(self, form: Form, env: Env):
        if len(form.items) != 3 or not isinstance(form.items[1], StrLit):
            raise CompileError("const takes a name given as a string and a value", form.pos)
        name = form.items[1].value
        _check_not_syntax(name, form.items[1].pos)
        if name in self.names or name in self.consts:
            raise CompileError(f"name {name!r} is already defined", form.items[1].pos)
        value = self.value_arg(form.items[2], env)
        if not isinstance(value, Const) or not _is_literal_type(value.type):
            raise CompileError(
                "a const must be a number, string, bool, or list known at compile time",
                form.items[2].pos,
            )
        self.consts[name] = value

    def define_func(self, form: Form):
        if len(form.items) < 3 or not isinstance(form.items[1], StrLit):
            raise CompileError("func takes a name given as a string and a body", form.pos)
        name = form.items[1].value
        _check_not_syntax(name, form.items[1].pos)
        if name in FORMS:
            raise CompileError(f"{name!r} is already a form", form.items[1].pos)
        if name in self.motifs or name in self.funcs:
            raise CompileError(f"{name!r} is already defined", form.items[1].pos)
        rest = form.items[2:]
        params: dict[str, Const | None] = {}
        if _head(rest[0]) == "params":
            params = self.func_params(rest[0])
            rest = rest[1:]
        if len(rest) != 1:
            raise CompileError("a function body is exactly one expression", form.pos)
        # A function that hides a library function gets its own key in the model, so calls
        # written before it still reach the library one.
        key = f"{name} (user)" if name in LIBRARY_HEADS else name
        spec = FuncSpec(params, rest[0], dict(self.funcs), dict(self.consts), name, key)
        spec.funcs[name] = spec
        keys = {n: f.key for n, f in spec.funcs.items()}
        body = _store_body(spec.body, spec.consts, keys, set(params))
        self.functions[key] = Function(
            tuple((p, None if d is None else d.value) for p, d in params.items()), body
        )
        # With only value parameters the body can be checked now, before any call.
        if all(default is not None for default in params.values()):
            check: Env = {k: Dyn(v.type) for k, v in params.items() if v is not None}
            self.frames.append(Frame([]))
            try:
                self.infer(spec, check, form.pos)
            finally:
                self.frames.pop()
        self.funcs[name] = spec

    def func_params(self, node: Node) -> dict[str, Const | None]:
        assert isinstance(node, Form)
        params: dict[str, Const | None] = {}
        for item in node.items[1:]:
            name = _head(item)
            if name is None or not isinstance(item, Form) or len(item.items) > 2:
                raise CompileError("a parameter is (name) or (name default)", item.pos)
            _check_not_syntax(name, item.pos)
            if name in params:
                raise CompileError(f"parameter {name!r} is given twice", item.pos)
            if len(item.items) == 1:
                params[name] = None
                continue
            default = self.expr(item.items[1], {})
            if not isinstance(default, Const) or not _is_literal_type(default.type):
                raise CompileError(
                    "a parameter default must be a number, string, bool, or list known at "
                    "compile time",
                    item.items[1].pos,
                )
            params[name] = default
        return params

    def func_body(self, spec: FuncSpec, env: Env, guess: str, pos: Pos) -> Value:
        if self.depth >= RECURSION_LIMIT:
            raise CompileError(f"recursion is deeper than {RECURSION_LIMIT} calls", pos)
        saved = self.funcs, self.consts, self.active.get(id(spec))
        self.funcs, self.consts = spec.funcs, spec.consts
        self.active[id(spec)] = guess
        self.in_func += 1
        self.depth += 1
        # An empty scope hides the names of a motif body the call may sit in.
        self.scopes.append({})
        frame = Frame([])
        self.frames.append(frame)
        try:
            return self.expr(spec.body, env)
        finally:
            self.frames.pop()
            self.scopes.pop()
            self.depth -= 1
            self.in_func -= 1
            self.funcs, self.consts, previous = saved
            if previous is None:
                del self.active[id(spec)]
            else:
                self.active[id(spec)] = previous

    # The type a call returns when its arguments are not all known. Recursive calls inside the
    # body return the current guess, starting from "not known yet", until the guess settles.
    def infer(self, spec: FuncSpec, env: Env, pos: Pos) -> Value:
        guess = PENDING
        for _ in range(4):
            result = self.func_body(spec, env, guess, pos)
            if not isinstance(result, (Const, Dyn)):
                return result
            if result.type == guess:
                break
            guess = result.type
        if guess == PENDING:
            raise CompileError(f"cannot work out what {spec.name!r} returns", pos)
        return Dyn(guess)

    def func_call(self, name: str, node: Form, env: Env) -> Value:
        spec = self.funcs[name]
        args = node.items[1:]
        if len(args) > len(spec.params):
            raise CompileError(f"{name} takes at most {len(spec.params)} arguments", node.pos)
        outer = self.constants(env)
        inner: Env = {}
        known = True
        for i, (pname, default) in enumerate(spec.params.items()):
            if i >= len(args):
                if default is None:
                    raise CompileError(f"{name} needs an object for {pname!r}", node.pos)
                inner[pname] = default
                continue
            arg = args[i]
            value = self.expr(arg, env)
            if default is None:
                if not isinstance(value, (ObjRef, SelfRef)):
                    raise CompileError(f"{pname!r} takes an object", arg.pos)
                written = self.resolve_refs(_substitute(arg, outer, self.lets), env)
                assert isinstance(written, Name)
                inner[pname] = ArgRef(value, written)
                known = False
                continue
            if isinstance(value, (ObjRef, SelfRef, Spread)):
                raise CompileError(f"{pname!r} takes a value", arg.pos)
            if not _widens_to(value.type, default.type):
                raise CompileError(f"expected {default.type}, got {value.type}", arg.pos)
            if isinstance(value, Const):
                inner[pname] = Const(_convert(value.value, default.type), default.type)
            else:
                inner[pname] = Dyn(default.type)
                known = False
        stored = tuple(self.resolve_refs(_substitute(a, outer, self.lets), env) for a in args)
        self.lets[id(node)] = Form((Name((spec.key,), node.items[0].pos), *stored), node.pos)
        # A call inside its own body that cannot be folded, or that sits in a branch never taken,
        # stands for whatever the function turns out to return.
        if id(spec) in self.active and (not known or self.speculative):
            return Dyn(self.active[id(spec)])
        if known:
            return self.func_body(spec, inner, self.active.get(id(spec), PENDING), node.pos)
        return self.infer(spec, inner, node.pos)

    def define_motif(self, form: Form):
        if len(form.items) < 2 or not isinstance(form.items[1], StrLit):
            raise CompileError("a motif needs a name given as a string", form.pos)
        kind = form.items[1].value
        _check_not_syntax(kind, form.items[1].pos)
        if kind in self.motifs or kind in self.funcs:
            raise CompileError(f"{kind!r} is already defined", form.items[1].pos)
        rest = form.items[2:]
        params: dict[str, Const] = {}
        if rest and _head(rest[0]) == "params":
            params = self.params(rest[0])
            rest = rest[1:]
        transform = None
        if rest and isinstance(rest[0], Form) and _head(rest[0]) == "transform":
            transform, rest = rest[0], rest[1:]
        spec = MotifSpec(params, tuple(rest), dict(self.motifs), transform)
        # Compiling the body once with the defaults reports its errors even if it is never used.
        self.frames.append(Frame([], inside=True))
        try:
            self.body(spec, dict(params), None)
        finally:
            self.frames.pop()
        self.motifs[kind] = spec

    def params(self, node: Node) -> dict[str, Const]:
        assert isinstance(node, Form)
        params: dict[str, Const] = {}
        for item in node.items[1:]:
            name = _head(item)
            if name is None or not isinstance(item, Form) or len(item.items) != 2:
                raise CompileError("a parameter is (name default)", item.pos)
            _check_not_syntax(name, item.pos)
            if name in attributes(Motif):
                raise CompileError(f"every motif already has {name!r}", item.pos)
            if name in params:
                raise CompileError(f"parameter {name!r} is given twice", item.pos)
            default = self.expr(item.items[1], {})
            if not isinstance(default, Const) or not _is_literal_type(default.type):
                raise CompileError(
                    "a parameter default must be a number, string, bool, or list known at "
                    "compile time",
                    item.items[1].pos,
                )
            params[name] = default
        return params

    def body(
        self, spec: MotifSpec, scope: Scope, owner: str | None
    ) -> tuple[list[Visual], Free | Bound | None]:
        pool: list[Obj] = []
        self.scopes.append(scope)
        self.pools.append(pool)
        outer, self.motifs = self.motifs, spec.motifs
        transform = None
        try:
            if spec.transform is not None:
                transform = self.default_transform(spec.transform)
            for node in spec.body:
                pool.extend(self.body_item(node))
        finally:
            self.motifs = outer
            self.scopes.pop()
            self.pools.pop()
        label = repr(owner) if owner is not None else "an anonymous motif"
        members: list[Visual] = []
        for obj in pool:
            assert isinstance(obj, Visual)
            self.parents[id(obj)] = (obj, label)
            members.append(obj)
        return members, transform

    def default_transform(self, node: Form) -> Free | Bound:
        composed = Form((Name(("transform",), node.pos), *node.items[1:]), node.pos)
        value = self.value_arg(composed, {})
        if isinstance(value, Const):
            return Free(value.value)
        return Bound(Name((self.hidden_value("transform", composed, {}, "transform"),), node.pos))

    def body_item(self, node: Node, env: Env | None = None) -> list[Obj]:
        env = env or {}
        head = _head(node)
        if isinstance(node, Form) and head == "repeat":
            return self.repeat(node, env, self.body_item)
        if isinstance(node, Form) and head == "let":
            return self.let_items(node, env, self.body_item)
        if isinstance(node, Form) and (head in FORMS or head in self.motifs):
            obj = self.definition(node, env)
            if not isinstance(obj, Visual):
                raise CompileError(f"{head} cannot be in the body of a motif", node.pos)
            return [obj]
        if head == "params":
            raise CompileError("params must come right after the motif's name", node.pos)
        if head == "transform":
            raise CompileError("a motif's transform must come before its members", node.pos)
        if head == "motif":
            raise CompileError("motifs are defined at the top level", node.pos)
        raise CompileError("the body of a motif holds only definitions", node.pos)

    def instance(self, form: Form, env: Env) -> Motif:
        kind = _head(form)
        assert kind is not None
        spec = self.motifs[kind]
        name = self.object_name(form, env)
        outer = env | {"self": SelfRef(Motif)}
        attrs = attributes(Motif)
        values: dict[str, Any] = {}
        params: dict[str, Free | Bound] = {}
        written: dict[str, tuple[Free | Bound, Pos]] = {}
        attr_frame = Frame([])
        self.frames.append(attr_frame)
        for node in form.items[2:]:
            head = _head(node)
            if head in FORMS or head in self.motifs or head == "repeat":
                raise CompileError(f"an instance of {kind} takes no members", node.pos)
            if head is None or not isinstance(node, Form) or head == "members":
                raise CompileError(f"unexpected value in {kind}", node.pos)
            if head not in attrs and head not in spec.params and head != "pos":
                raise CompileError(f"{head!r} is not an attribute of {kind}", node.pos)
            _check_pos(head, {a: p for a, (_, p) in written.items()}, node.pos)
            if head in written:
                raise CompileError(f"attribute {head!r} is given twice", node.pos)
            if head == "transform":
                composed = Form(
                    (Name(("transform",), node.items[0].pos), *node.items[1:]), node.pos
                )
                values["transform"] = self.attr_value(Motif, head, composed, outer)
                written[head] = (values["transform"], node.pos)
                continue
            if len(node.items) != 2:
                raise CompileError(f"attribute {head!r} takes exactly one value", node.pos)
            if head == "pos":
                values["x"], values["y"] = self.pos_value(node.items[1], outer)
                written["x"] = (values["x"], node.pos)
                written["y"] = (values["y"], node.pos)
                written["pos"] = (Free(None), node.pos)
            elif head in attrs:
                values[attrs[head].name] = self.attr_value(Motif, head, node.items[1], outer)
                written[head] = (values[attrs[head].name], node.pos)
            else:
                params[head] = self.param_value(spec.params[head].type, node.items[1], outer)
                written[head] = (params[head], node.pos)
        self.frames.pop()
        _check_cycles(name, written, attr_frame.locals)
        if self.scopes:
            for attr in INHERITED:
                values.setdefault(attrs[attr].name, Inherit())
        scope: Scope = {}
        path: tuple[str, ...] | None = None
        if name is not None and all(p is not None for p in self.instance_path):
            path = (*(p for p in self.instance_path if p is not None), name)
        for pname, default in spec.params.items():
            given = params.setdefault(pname, Free(default.value))
            controlled = pname in self.written_anywhere or (
                path is not None and (*path, pname) in self.written
            )
            known = isinstance(given, Free) and not controlled
            scope[pname] = Const(given.value, default.type) if known else Dyn(default.type)
        body_frame = Frame([], inside=True)
        self.frames.append(body_frame)
        self.instance_path.append(name)
        try:
            members, default = self.body(spec, scope, name)
        finally:
            self.instance_path.pop()
            self.frames.pop()
        if default is not None and "transform" not in values:
            values["transform"] = default
        types = {pname: default.type for pname, default in spec.params.items()}
        obj = Motif(
            name=name, kind=kind, params=dict(params), param_types=types, members=members, **values
        )
        self.settle(attr_frame, obj)
        self.settle(body_frame, obj)
        self.register(obj, form.pos)
        return obj

    def param_value(self, expected: str, node: Node, env: Env) -> Free | Bound:
        value = self.value_arg(node, env)
        if not _widens_to(value.type, expected):
            raise CompileError(f"expected {expected}, got {value.type}", node.pos)
        if isinstance(value, Const):
            return Free(_convert(value.value, expected))
        return Bound(self.resolve_refs(_substitute(node, self.constants(env), self.lets), env))

    # Loop variables and parameters known at compile time are written into stored expressions.
    def constants(self, env: Env) -> Env:
        scope = self.scopes[-1] if self.scopes else {}
        consts: Env = {k: v for k, v in self.consts.items() if k not in scope}
        consts |= {k: v for k, v in scope.items() if isinstance(v, Const)}
        return consts | env

    def definition(self, form: Form, env: Env) -> Obj:
        head = _head(form)
        assert head is not None
        if head in self.motifs:
            return self.instance(form, env)
        spec = FORMS[head]
        name = self.object_name(form, env)
        frame = Frame([])
        self.frames.append(frame)
        try:
            obj = self.library_definition(form, env, head, spec, name, frame)
        finally:
            self.frames.pop()
        self.settle(frame, obj)
        return obj

    def library_definition(
        self, form: Form, env: Env, head: str, spec: FormSpec, name: str | None, frame: Frame
    ) -> Obj:
        env = env | {"self": SelfRef(spec.cls)}
        attrs = attributes(spec.cls)
        var = variadic(spec.cls)
        settable = {a for a in attrs if a not in spec.positional and (var is None or a != var.name)}
        if {"x", "y"} <= attrs.keys():
            settable.add("pos")
        shapes = PROPERTIES.get(spec.cls, {})
        settable |= shapes.keys()
        extra: dict[str, tuple[Const | Dyn, Node]] = {}
        rest = list(form.items[2:])
        values: dict[str, Free | Bound] = {}
        positions: dict[str, Pos] = {}

        for field_name in spec.positional:
            if rest and _head(rest[0]) not in settable:
                if _head(rest[0]) == field_name:
                    raise CompileError(
                        f"the {field_name} of {head} is given by position", rest[0].pos
                    )
                node = rest.pop(0)
                values[field_name] = self.attr_value(spec.cls, field_name, node, env)
                positions[field_name] = node.pos

        while rest and _head(rest[0]) in settable:
            node = rest.pop(0)
            assert isinstance(node, Form)
            attr = _head(node)
            assert attr is not None
            _check_pos(attr, positions, node.pos)
            if attr in positions:
                raise CompileError(f"attribute {attr!r} is given twice", node.pos)
            positions[attr] = node.pos
            if attr == "pos":
                if len(node.items) != 2:
                    raise CompileError("attribute 'pos' takes exactly one value", node.pos)
                values["x"], values["y"] = self.pos_value(node.items[1], env)
                positions["x"] = positions["y"] = node.pos
                continue
            if attr in shapes:
                if len(node.items) != 2:
                    raise CompileError(f"attribute {attr!r} takes exactly one value", node.pos)
                value = self.value_arg(node.items[1], env)
                if not _widens_to(value.type, shapes[attr]):
                    raise CompileError(
                        f"{attr} takes a {shapes[attr]}, got {value.type}", node.items[1].pos
                    )
                extra[attr] = (value, node.items[1])
                continue
            if _expected_type(spec.cls, attr) == "transform":
                head_name = Name(("transform",), node.items[0].pos)
                composed = Form((head_name, *node.items[1:]), node.pos)
                values[attr] = self.attr_value(spec.cls, attr, composed, env)
                continue
            if len(node.items) != 2:
                raise CompileError(f"attribute {attr!r} takes exactly one value", node.pos)
            values[attr] = self.attr_value(spec.cls, attr, node.items[1], env)

        if extra:
            self.construct(spec.cls, extra, values, positions, env)
        _check_cycles(
            name,
            {a: (values[a], positions[a]) for a in values},
            frame.locals,
            PROPERTY_READS.get(spec.cls, {}),
        )
        kwargs: dict[str, Any] = {attrs[attr].name: value for attr, value in values.items()}
        if self.scopes and issubclass(spec.cls, Styled):
            for attr in INHERITED:
                kwargs.setdefault(attrs[attr].name, Inherit())
        if var is not None:
            members: list[Visual] = []
            for node in rest:
                members.extend(self.member(node, env, head, settable, name))
            kwargs[var.name] = members
        elif rest:
            node = rest[0]
            attr = _head(node)
            if attr is not None and attr not in FORMS:
                raise CompileError(f"{attr!r} is not an attribute of {head}", node.pos)
            raise CompileError(f"unexpected value in {head}", node.pos)

        obj = spec.cls(name=name, **kwargs)
        self.register(obj, form.pos)
        return obj

    # Fills a shape's stored attributes from its other constructors, such as a rect's center and
    # size. Giving a stored attribute that a constructor also fills is an error.
    def construct(
        self,
        cls: type[Obj],
        extra: dict[str, tuple[Const | Dyn, Node]],
        values: dict[str, Free | Bound],
        positions: dict[str, Pos],
        env: Env,
    ):
        hidden: dict[str, str] = {}

        def part(name: str, i: int | None = None) -> Node:
            value, node = extra[name]
            if isinstance(value, Const):
                v = value.value
                if i is not None:
                    assert isinstance(v, tuple)
                    v = v[i]
                assert isinstance(v, (int, float, Fraction))
                return RealLit(float(v), node.pos)
            if name not in hidden:
                hidden[name] = self.hidden_value(name, node, env, value.type)
            axis = () if i is None else ("xyz"[i],)
            return Name((hidden[name], *axis), node.pos)

        def stored(attr: str) -> Node:
            value = values.get(attr, attributes(cls)[attr].default)
            if isinstance(value, Free):
                assert isinstance(value.value, (int, float))
                return RealLit(float(value.value))
            return Name(("self", attr))

        def call(op: str, *args: Node) -> Form:
            return Form((Name((op,)), *args))

        def conflict(name: str, *attrs: str):
            for attr in attrs:
                if attr in positions and attr != name:
                    raise CompileError(
                        f"{name} cannot be given together with {attr}", extra[name][1].pos
                    )

        def put(attr: str, node: Node, source: str):
            values[attr] = self.attr_value(cls, attr, node, env)
            positions[attr] = extra[source][1].pos

        def need(*names: str):
            for name in names:
                if name not in extra:
                    given = next(n for n in names if n in extra)
                    raise CompileError(f"{given} needs {name}", extra[given][1].pos)

        if cls is Rect and ("from" in extra or "to" in extra):
            need("from", "to")
            for name in ("from", "to"):
                conflict(name, "x", "y", "pos", "width", "height", "size", "center")
            put("x", part("from", 0), "from")
            put("y", part("from", 1), "from")
            put("width", call("-", part("to", 0), part("from", 0)), "to")
            put("height", call("-", part("to", 1), part("from", 1)), "to")
            return
        if cls is Line:
            need("from", "to")
            for name in ("from", "to"):
                conflict(name, "x1", "y1", "x2", "y2", "x", "y", "pos")
            put("x1", part("from", 0), "from")
            put("y1", part("from", 1), "from")
            put("x2", part("to", 0), "to")
            put("y2", part("to", 1), "to")
            return
        if cls is Triangle:
            if "center" in extra:
                conflict("center", "x", "y", "pos")
                put("x", part("center", 0), "center")
                put("y", part("center", 1), "center")
            source = "r" if "r" in extra else "center"
            conflict(source, "a", "b", "c")
            radius = part("r") if "r" in extra else RealLit(1.0)
            for corner, angle in (("a", 90.0), ("b", 210.0), ("c", 330.0)):
                put(corner, call("polar", radius, RealLit(angle)), source)
            return
        sizes = ("width", "height") if cls is Rect else ("rx", "ry")
        if "size" in extra:
            conflict("size", *sizes)
            halve = (lambda n: n) if cls is Rect else (lambda n: call("/", n, RealLit(2.0)))
            put(sizes[0], halve(part("size", 0)), "size")
            put(sizes[1], halve(part("size", 1)), "size")
        if "center" in extra:
            conflict("center", "x", "y", "pos")
            if cls is Rect:
                put(
                    "x",
                    call("-", part("center", 0), call("/", stored("width"), RealLit(2.0))),
                    "center",
                )
                put(
                    "y",
                    call("-", part("center", 1), call("/", stored("height"), RealLit(2.0))),
                    "center",
                )
            else:
                put("x", part("center", 0), "center")
                put("y", part("center", 1), "center")

    def member(
        self, node: Node, env: Env, container: str, settable, owner: str | None
    ) -> list[Visual]:
        head = _head(node)
        if isinstance(node, Form) and head == "repeat":
            return self.repeat(
                node, env, lambda n, e: self.member(n, e, container, settable, owner)
            )
        if isinstance(node, Form) and head == "let":
            return self.let_items(
                node, env, lambda n, e: self.member(n, e, container, settable, owner)
            )
        if isinstance(node, Form) and head == "ref":
            node = self.ref_name(node, env)
        elif isinstance(node, Form) and (head in FORMS or head in self.motifs):
            obj = self.definition(node, env)
            if not isinstance(obj, Visual):
                raise CompileError(f"{head} cannot be a member of {container}", node.pos)
            if issubclass(FORMS[container].cls, View):
                raise CompileError(
                    "visual objects are defined inside the scene; a canvas only shows them",
                    node.pos,
                )
            self.adopt(obj, container, owner, node.pos)
            return [obj]
        if isinstance(node, Form):
            if head in settable:
                raise CompileError(f"attribute {head!r} must come before the members", node.pos)
            raise CompileError(
                f"{head!r} is not an attribute of {container} and not a recognized form", node.pos
            )
        if isinstance(node, Name):
            value = self.name(node, env)
            if isinstance(value, ObjRef) and isinstance(value.obj, Visual):
                if self.scopes and not any(
                    v.obj is value.obj for v in self.scopes[-1].values() if isinstance(v, ObjRef)
                ):
                    raise CompileError(
                        "a member in a motif body must be defined in that body", node.pos
                    )
                if not issubclass(FORMS[container].cls, View):
                    self.adopt(value.obj, container, owner, node.pos)
                return [value.obj]
        raise CompileError(f"not a valid member of {container}", node.pos)

    # A view only shows objects, but any other container becomes the object's one parent.
    def adopt(self, obj: Obj, container: str, owner: str | None, pos: Pos):
        label = repr(obj.name) if obj.name is not None else "an anonymous object"
        known = self.parents.get(id(obj))
        if known is not None and known[0] is obj:
            raise CompileError(f"{label} already belongs to {known[1]}", pos)
        parent = repr(owner) if owner is not None else f"an anonymous {container}"
        self.parents[id(obj)] = (obj, parent)
        pool = self.pools[-1]
        pool[:] = [item for item in pool if item is not obj]

    def attr_value(self, cls: type[Obj], attr: str, node: Node, env: Env):
        expected = _expected_type(cls, attr)
        value = self.expr(node, env)
        if isinstance(value, (ObjRef, SelfRef)):
            raise CompileError("expected a value, got an object", node.pos)
        if isinstance(value, Spread):
            raise CompileError(
                "a group attribute gives several values where one is expected", node.pos
            )
        if not _widens_to(value.type, expected):
            raise CompileError(f"expected {expected}, got {value.type}", node.pos)
        if isinstance(value, Const):
            return Free(_convert(value.value, expected))
        return Bound(self.resolve_refs(_substitute(node, self.constants(env), self.lets), env))

    def resolve_refs(self, node: Node, env: Env) -> Node:
        if isinstance(node, Form) and _head(node) == "ref":
            return self.ref_name(node, env)
        if isinstance(node, Form):
            return Form(tuple(self.resolve_refs(item, env) for item in node.items), node.pos)
        if isinstance(node, ListLit):
            return ListLit(tuple(self.resolve_refs(item, env) for item in node.items), node.pos)
        return node

    def expr(self, node: Node, env: Env) -> Value:
        match node:
            case IntLit(value=v):
                return Const(v, "int")
            case RatioLit(value=v):
                return Const(v, "ratio")
            case RealLit(value=v):
                return Const(v, "real")
            case ComplexLit(value=v):
                return Const(v, "complex")
            case BoolLit(value=v):
                return Const(v, "bool")
            case StrLit(value=v):
                return Const(v, "str")
            case InterpStrLit():
                return self.interp(node, env)
            case ListLit():
                return self.list_value(node, env)
            case Name():
                return self.name(node, env)
            case Form():
                return self.call(node, env)

    def list_value(self, node: ListLit, env: Env) -> Value:
        if not node.items:
            raise CompileError("a list needs at least one number", node.pos)
        known: list[float] = []
        for item in node.items:
            value = self.value_arg(item, env)
            if value.type not in ("int", "ratio", "real", PENDING):
                raise CompileError(f"a list holds only real numbers, got {value.type}", item.pos)
            if isinstance(value, Const):
                assert isinstance(value.value, (int, Fraction, float))
                known.append(float(value.value))
        kind = f"list{len(node.items)}"
        return Const(tuple(known), kind) if len(known) == len(node.items) else Dyn(kind)

    def list_part(self, value: Value, part: str | Node, env: Env, pos: Pos) -> Value:
        assert isinstance(value, (Const, Dyn))
        n = _list_len(value.type)
        if n is None:
            raise CompileError(f"a {value.type} has no parts", pos)
        if isinstance(part, str):
            if part not in AXES:
                raise CompileError(f"a list has no part {part!r}; use x, y, z, or an index", pos)
            i = AXES[part]
        else:
            index = self.expr(part, env)
            if not (isinstance(index, Const) and index.type == "int"):
                raise CompileError("an index must be an int known at compile time", part.pos)
            assert isinstance(index.value, int)
            i = index.value + n if index.value < 0 else index.value
        if not 0 <= i < n:
            raise CompileError(f"a list of {n} numbers has no part {part!r}", pos)
        if isinstance(value, Const):
            assert isinstance(value.value, tuple)
            return Const(value.value[i], "real")
        return Dyn("real")

    def interp(self, node: InterpStrLit, env: Env) -> Value:
        text: list[str] = []
        constant = True
        for part in node.parts:
            if isinstance(part, str):
                text.append(part)
                continue
            name = part.name if isinstance(part, Field) else part
            value = self.name(name, env)
            if isinstance(value, (ObjRef, SelfRef)):
                raise CompileError("cannot put an object in a string", part.pos)
            if isinstance(value, Spread):
                if isinstance(part, Field):
                    raise CompileError("a group attribute cannot take a format spec", part.pos)
                constant = False
                continue
            spec = part.spec if isinstance(part, Field) else None
            if spec:
                _check_spec(spec, value.type, part.pos)
            if isinstance(value, Const):
                text.append(_format(value.value, value.type, spec))
            else:
                constant = False
        return Const("".join(text), "str") if constant else Dyn("str")

    def name(self, node: Name, env: Env) -> Value:
        first, *rest = node.parts
        assert isinstance(first, str)
        local = env.get(first)
        if isinstance(local, int):
            if rest:
                raise CompileError(f"{first!r} is a number and has no attributes", node.pos)
            return Const(local, "int")
        if isinstance(local, (Const, Dyn, LetRef)):
            value: Value = Dyn(local.type) if isinstance(local, LetRef) else local
            for part in rest:
                value = self.list_part(value, part, env, node.pos)
            return value
        scope = self.scopes[-1] if self.scopes else {}
        if local is None and first in scope:
            current: Value = scope[first]
            if isinstance(current, (Const, Dyn)):
                for part in rest:
                    current = self.list_part(current, part, env, node.pos)
                return current
        elif local is None and first in self.consts:
            value = self.consts[first]
            if rest and _list_len(value.type) is None:
                raise CompileError(f"{first!r} is a const {value.type} and has no parts", node.pos)
            for part in rest:
                value = self.list_part(value, part, env, node.pos)
            return value
        elif local is None and first not in self.names:
            raise CompileError(f"undefined name {first!r}", node.pos)
        elif local is None and self.in_func and first not in self.builtin_names:
            raise CompileError(
                f"undefined name {first!r}: a function sees only its parameters, consts, "
                "and functions",
                node.pos,
            )
        elif isinstance(local, ArgRef):
            current = local.value
        else:
            current = local if local is not None else ObjRef(self.names[first])
        for part in rest:
            current = self.access(current, part, env, node.pos)
        if isinstance(current, ObjRef) and isinstance(current.obj, Real):
            return Dyn("real")
        if isinstance(current, ObjRef) and isinstance(current.obj, Local):
            return Dyn(current.obj.type)
        return current

    def access(self, current: Value, part: str | Node, env: Env, pos: Pos) -> Value:
        if isinstance(current, SelfRef):
            return self.self_access(current.cls, part, pos)
        if isinstance(current, (Const, Dyn)) and _list_len(current.type) is not None:
            return self.list_part(current, part, env, pos)
        if not isinstance(current, ObjRef):
            raise CompileError("only objects and lists have parts", pos)
        obj = current.obj
        if not isinstance(part, str):
            return self.index(obj, part, env)
        if isinstance(obj, Motif):
            params = self.motifs[obj.kind].params
            if part in params:
                return Dyn(params[part].type)
            names = local_names(obj)
            if part in names:
                return ObjRef(names[part])
        if isinstance(obj, Group) and part not in attributes(type(obj)):
            types = []
            for member in obj.members:
                if part not in attributes(type(member)):
                    raise CompileError(f"a member of {obj.name!r} has no attribute {part!r}", pos)
                types.append(_expected_type(type(member), part))
            return Spread(tuple(types))
        attrs = attributes(type(obj))
        if part == "pos" and {"x", "y"} <= attrs.keys():
            return Dyn("list2")
        if isinstance(obj, Local):
            return self.list_part(Dyn(obj.type), part, env, pos)
        if part in PROPERTIES.get(type(obj), {}):
            return Dyn(PROPERTIES[type(obj)][part])
        if part not in attrs or variadic(type(obj)) is attrs[part]:
            raise CompileError(f"{obj.name!r} has no attribute {part!r}", pos)
        return Dyn(_expected_type(type(obj), part))

    def self_access(self, cls: type[Obj], part: str | Node, pos: Pos) -> Value:
        attrs = attributes(cls)
        if part == "pos" and {"x", "y"} <= attrs.keys():
            return Dyn("list2")
        if isinstance(part, str) and part in PROPERTIES.get(cls, {}):
            return Dyn(PROPERTIES[cls][part])
        if not isinstance(part, str) or part not in attrs or variadic(cls) is attrs[part]:
            raise CompileError(f"self ({cls.__name__.lower()}) has no attribute {part!r}", pos)
        return Dyn(_expected_type(cls, part))

    def index(self, obj: Obj, node: Node, env: Env) -> Value:
        if not isinstance(obj, Group):
            raise CompileError("only groups can be indexed", node.pos)
        value = self.expr(node, env)
        if not (isinstance(value, Const) and value.type == "int"):
            raise CompileError("an index must be an int known at compile time", node.pos)
        i = value.value
        assert isinstance(i, int)
        if not -len(obj.members) <= i < len(obj.members):
            raise CompileError(f"index {i} is out of range for {obj.name!r}", node.pos)
        return ObjRef(obj.members[i])

    def call(self, node: Form, env: Env) -> Value:
        head = _head(node)
        if head in self.funcs:
            return self.func_call(head, node, env)
        if head in ARITHMETIC:
            return self.arithmetic(head, node, env)
        if head in COMPARISONS:
            return self.compare(head, node, env)
        if head == "^":
            return self.power(node, env)
        if head == "mod":
            return self.modulo(node, env)
        if head == "abs":
            return self.absolute(node, env)
        if head == "if":
            return self.if_(node, env)
        if head == "cond":
            return self.cond(node, env)
        if head in STDLIB:
            return self.library(head, node, env)
        if head == "ref":
            return self.name(self.ref_name(node, env), env)
        if head == "transform":
            return self.transform(node, env)
        if head == "let":
            if len(node.items) != 3:
                raise CompileError("let in an expression takes bindings and one value", node.pos)
            inner = self.bindings(node, env)
            self.lets[id(node)] = inner
            return self.expr(node.items[2], inner)
        if head in FORMS or head in self.motifs or head in ("repeat", "motif"):
            raise CompileError(f"{head} cannot be used in an expression", node.pos)
        raise CompileError(f"unknown function {head!r}", node.pos)

    def ref_name(self, node: Form, env: Env) -> Name:
        if len(node.items) != 2:
            raise CompileError("ref takes one string", node.pos)
        arg = node.items[1]
        value = self.expr(arg, env)
        if not (isinstance(value, Const) and value.type == "str"):
            raise CompileError("ref takes a string known at compile time", arg.pos)
        assert isinstance(value.value, str)
        try:
            return parse_name(value.value, arg.pos)
        except ParseError as e:
            raise CompileError(e.msg, e.pos) from None

    def value_arg(self, node: Node, env: Env) -> Const | Dyn:
        value = self.expr(node, env)
        if isinstance(value, (ObjRef, SelfRef)):
            raise CompileError("expected a value, got an object", node.pos)
        if isinstance(value, Spread):
            raise CompileError("a group attribute gives several values here", node.pos)
        return value

    def args(self, node: Form, count: int, env: Env) -> list[Const | Dyn]:
        args = node.items[1:]
        if len(args) != count:
            raise CompileError(f"{_head(node)} takes {count} arguments", node.pos)
        return [self.value_arg(arg, env) for arg in args]

    def compare(self, op: str, node: Form, env: Env) -> Value:
        a, b = self.args(node, 2, env)
        ordered = op in ("<", "<=", ">", ">=")
        if PENDING in (a.type, b.type):
            return Dyn("bool")
        numeric = a.type in NUMERIC and b.type in NUMERIC
        if ordered and not (numeric and "complex" not in (a.type, b.type)):
            raise CompileError(f"{op} compares real numbers", node.pos)
        if not ordered and not numeric and a.type != b.type:
            raise CompileError(f"cannot compare {a.type} with {b.type}", node.pos)
        if isinstance(a, Const) and isinstance(b, Const):
            return Const(COMPARISONS[op](a.value, b.value), "bool")
        return Dyn("bool")

    # The remainder with the sign of the divisor, as in mathematics and Python's %.
    def modulo(self, node: Form, env: Env) -> Value:
        a, b = self.args(node, 2, env)
        if PENDING in (a.type, b.type):
            return Dyn(PENDING)
        if not {a.type, b.type} <= {"int", "ratio", "real"}:
            raise CompileError("mod takes real numbers", node.pos)
        result = NUMERIC[max(NUMERIC.index(a.type), NUMERIC.index(b.type))]
        if not (isinstance(a, Const) and isinstance(b, Const)):
            return Dyn(result)
        x, y = a.value, b.value
        assert isinstance(x, (int, Fraction, float)) and isinstance(y, (int, Fraction, float))
        if y == 0:
            raise CompileError("mod by zero", node.pos)
        return Const(_convert(x % y, result), result)

    # The size of a number: |x| for reals, the modulus for complex numbers.
    def absolute(self, node: Form, env: Env) -> Value:
        (a,) = self.args(node, 1, env)
        if a.type == PENDING:
            return Dyn(PENDING)
        if a.type not in NUMERIC:
            raise CompileError("abs takes a number", node.pos)
        result = "real" if a.type == "complex" else a.type
        if isinstance(a, Const):
            assert isinstance(a.value, (int, Fraction, float, complex))
            return Const(_convert(abs(a.value), result), result)
        return Dyn(result)

    def power(self, node: Form, env: Env) -> Value:
        base, exp = self.args(node, 2, env)
        if PENDING in (base.type, exp.type):
            return Dyn(PENDING)
        if base.type not in NUMERIC or exp.type not in NUMERIC:
            raise CompileError("^ takes numbers", node.pos)
        if "complex" in (base.type, exp.type):
            result = "complex"
        elif exp.type == "int":
            known = isinstance(exp, Const) and isinstance(exp.value, int)
            negative = not (known and exp.value >= 0)
            result = "ratio" if base.type == "int" and negative else base.type
        else:
            result = "real"
        if not (isinstance(base, Const) and isinstance(exp, Const)):
            return Dyn(result)
        try:
            value = power(base.value, exp.value)
        except ZeroDivisionError:
            raise CompileError("division by zero", node.pos) from None
        if result != "complex" and isinstance(value, complex):
            raise CompileError("the result is not a real number", node.pos)
        return Const(_convert(value, result), result)

    def if_(self, node: Form, env: Env) -> Value:
        if len(node.items) != 4:
            raise CompileError("if takes 3 arguments", node.pos)
        test = self.value_arg(node.items[1], env)
        if test.type not in ("bool", PENDING):
            raise CompileError("the condition of if must be a bool", node.items[1].pos)
        branches: list[Const | Dyn] = []
        for i, branch in enumerate(node.items[2:]):
            taken = not isinstance(test, Const) or bool(test.value) == (i == 0)
            self.speculative += 0 if taken else 1
            try:
                branches.append(self.value_arg(branch, env))
            finally:
                self.speculative -= 0 if taken else 1
        then, other = branches
        result = _unify(then.type, other.type, node.pos)
        if isinstance(test, Const):
            return _retype(then if test.value else other, result)
        return Dyn(result)

    def cond(self, node: Form, env: Env) -> Value:
        clauses = node.items[1:]
        result: str | None = None
        chosen: Const | Dyn | None = None
        dynamic = False
        for i, clause in enumerate(clauses):
            if not (isinstance(clause, Form) and len(clause.items) == 2):
                raise CompileError("a cond clause is (condition value)", clause.pos)
            test_node, value_node = clause.items
            last = i == len(clauses) - 1
            is_else = isinstance(test_node, Name) and test_node.parts == ("else",)
            if is_else != last:
                raise CompileError("cond must end with exactly one else clause", clause.pos)
            settled = chosen is not None and not dynamic
            self.speculative += settled
            try:
                test = Const(True, "bool") if is_else else self.value_arg(test_node, env)
            finally:
                self.speculative -= settled
            if test.type not in ("bool", PENDING):
                raise CompileError("a cond condition must be a bool", test_node.pos)
            skipped = settled or (not dynamic and isinstance(test, Const) and not test.value)
            self.speculative += skipped
            try:
                value = self.value_arg(value_node, env)
            finally:
                self.speculative -= skipped
            result = value.type if result is None else _unify(result, value.type, clause.pos)
            if chosen is None and not dynamic:
                if isinstance(test, Dyn):
                    dynamic = True
                elif test.value:
                    chosen = value
        if result is None:
            raise CompileError("cond needs an else clause", node.pos)
        return _retype(chosen, result) if chosen is not None else Dyn(result)

    def library(self, name: str, node: Form, env: Env) -> Value:
        fn = STDLIB[name]
        kinds: list[str] = []
        values: list[Value] = []
        for arg in node.items[1:]:
            value = self.expr(arg, env)
            if isinstance(value, SelfRef):
                point = {"x", "y"} <= attributes(value.cls).keys()
            elif isinstance(value, ObjRef):
                point = {"x", "y"} <= attributes(type(value.obj)).keys()
            else:
                point = None
            if isinstance(value, (Const, Dyn)) and _list_len(value.type) is not None:
                point = True
            if point is None and isinstance(value, (Const, Dyn)) and _widens_to(value.type, "real"):
                kinds.append("real")
            elif point:
                kinds.append("point")
            else:
                kinds.append("invalid")
            values.append(value)
        sig = fn.find(kinds)
        if sig is None:
            raise CompileError(f"no form of {name} takes these arguments", node.pos)
        sizes = {
            _list_len(v.type) if isinstance(v, (Const, Dyn)) else 2
            for v, kind in zip(values, kinds, strict=True)
            if kind == "point"
        }
        if len(sizes) > 1:
            raise CompileError(f"the points given to {name} have different sizes", node.pos)
        result = f"list{sizes.pop()}" if sig.result == "point" else sig.result
        consts = [v.value for v in values if isinstance(v, Const)]
        if fn.pure and len(consts) == len(values):
            try:
                return Const(stdlib_call(fn, sig, consts), result)
            except (ValueError, ZeroDivisionError) as e:
                raise CompileError(str(e) or "invalid argument", node.pos) from None
        return Dyn(result)

    def transform(self, node: Form, env: Env) -> Value:
        values = [self.value_arg(arg, env) for arg in node.items[1:]]
        for arg, value in zip(node.items[1:], values, strict=True):
            if value.type != "transform":
                raise CompileError(f"expected a transform, got {value.type}", arg.pos)
        matrices = [v.value for v in values if isinstance(v, Const) and isinstance(v.value, Matrix)]
        if len(matrices) == len(values):
            return Const(compose(*matrices), "transform")
        return Dyn("transform")

    def arithmetic(self, op: str, node: Form, env: Env) -> Value:
        types: list[str] = []
        consts: list[Const] = []
        dynamic = False
        for arg in node.items[1:]:
            value = self.expr(arg, env)
            if isinstance(value, (ObjRef, SelfRef)):
                raise CompileError("expected a number, got an object", arg.pos)
            arg_types = value.types if isinstance(value, Spread) else (value.type,)
            for t in arg_types:
                if t not in NUMERIC and _list_len(t) is None and t != PENDING:
                    raise CompileError(f"expected a number, got {t}", arg.pos)
            types.extend(arg_types)
            if isinstance(value, Const):
                consts.append(value)
            else:
                dynamic = True
        if op in "-/" and not types:
            raise CompileError(f"{op} needs at least one argument", node.pos)
        if op == "/" and len(types) < 2:
            raise CompileError("/ needs at least two arguments", node.pos)
        if any(_list_len(t) is not None for t in types):
            return self.list_arithmetic(
                op, node, [t for t in types if t != PENDING], consts, dynamic
            )
        if types and all(t == PENDING for t in types):
            return Dyn(PENDING)
        rank = max((NUMERIC.index(t) for t in types if t != PENDING), default=0)
        if op == "/":
            rank = max(rank, NUMERIC.index("ratio"))
        result = NUMERIC[rank]
        if dynamic:
            return Dyn(result)
        values = [_convert(c.value, result) for c in consts]
        try:
            return Const(_fold(op, values), result)
        except ZeroDivisionError:
            raise CompileError("division by zero", node.pos) from None

    def list_arithmetic(
        self, op: str, node: Form, types: list[str], consts: list[Const], dynamic: bool
    ) -> Value:
        lists = [i for i, t in enumerate(types) if _list_len(t) is not None]
        if "complex" in types:
            raise CompileError("lists hold only real numbers", node.pos)
        if op in "+-" and len(set(types)) != 1:
            raise CompileError(f"{op} takes lists of the same size, or only numbers", node.pos)
        if op == "*" and len(lists) != 1:
            raise CompileError("* scales one list by numbers", node.pos)
        if op == "/" and lists != [0]:
            raise CompileError("/ divides one list by numbers", node.pos)
        result = types[lists[0]]
        if dynamic:
            return Dyn(result)
        try:
            return Const(_fold(op, [c.value for c in consts]), result)
        except ZeroDivisionError:
            raise CompileError("division by zero", node.pos) from None


# The heads the standard library already uses; a user function with one of these names gets its
# own key in the model.
LIBRARY_HEADS = set(STDLIB) | {"mod", "abs"}


# A function body as the model stores it: consts written in, and calls to user functions named
# by their key. Names bound by parameters or lets hide consts and functions of the same name.
def _store_body(node: Node, consts: dict, keys: dict[str, str], bound: set[str]) -> Node:
    if isinstance(node, Name):
        first = node.parts[0]
        value = consts.get(first) if isinstance(first, str) and first not in bound else None
        if value is None:
            return node
        if len(node.parts) == 1:
            return _literal(value, node.pos)
        return RealLit(_take(value.value, node.parts[1:]), node.pos)
    if isinstance(node, Form) and _head(node) == "let" and len(node.items) == 3:
        pairs, inner = [], set(bound)
        assert isinstance(node.items[1], Form)
        for pair in node.items[1].items:
            assert isinstance(pair, Form)
            key, expr = pair.items
            pairs.append(Form((key, _store_body(expr, consts, keys, inner)), pair.pos))
            if isinstance(key, Name) and isinstance(key.parts[0], str):
                inner.add(key.parts[0])
        body = _store_body(node.items[2], consts, keys, inner)
        return Form((node.items[0], Form(tuple(pairs), node.items[1].pos), body), node.pos)
    if isinstance(node, Form):
        items = [_store_body(item, consts, keys, bound) for item in node.items]
        head = _head(node)
        if head in keys and head not in bound:
            items[0] = Name((keys[head],), node.items[0].pos)
        return Form(tuple(items), node.pos)
    if isinstance(node, ListLit):
        return ListLit(tuple(_store_body(i, consts, keys, bound) for i in node.items), node.pos)
    return node


# Loop variables and known parameters do not exist after compiling, so bound expressions get
# their values instead.
def _substitute(node: Node, env: dict, lets: dict[int, dict | Node]) -> Node:
    if isinstance(node, Form) and id(node) in lets:
        entry = lets[id(node)]
        if not isinstance(entry, dict):
            return entry
        return _substitute(node.items[2], env | entry, lets)
    if isinstance(node, Name):
        first = node.parts[0]
        local = env.get(first) if isinstance(first, str) and len(node.parts) == 1 else None
        if isinstance(local, Const):
            return _literal(local, node.pos)
        if isinstance(local, LetRef):
            return Name((local.hidden,), node.pos)
        whole = env.get(first) if isinstance(first, str) and len(node.parts) > 1 else None
        if isinstance(whole, (Const, LetRef)):
            rest = tuple(
                p if isinstance(p, str) else _substitute(p, env, lets) for p in node.parts[1:]
            )
            if isinstance(whole, LetRef):
                return Name((whole.hidden, *rest), node.pos)
            return RealLit(_take(whole.value, rest), node.pos)
        if isinstance(local, int):
            return IntLit(local, node.pos)
        parts = tuple(p if isinstance(p, str) else _substitute(p, env, lets) for p in node.parts)
        return Name(parts, node.pos)
    if isinstance(node, Form):
        return Form(tuple(_substitute(item, env, lets) for item in node.items), node.pos)
    if isinstance(node, ListLit):
        return ListLit(tuple(_substitute(item, env, lets) for item in node.items), node.pos)
    if isinstance(node, InterpStrLit):
        out: list[str | Name | Field] = []
        for part in node.parts:
            spec = part.spec if isinstance(part, Field) else None
            name = part.name if isinstance(part, Field) else part
            sub = name if isinstance(name, str) else _substitute(name, env, lets)
            if isinstance(sub, (IntLit, RatioLit, RealLit, ComplexLit, BoolLit, StrLit)):
                kind = "int" if isinstance(sub, IntLit) else "real"
                sub = _format(sub.value, kind, spec) if spec else str(sub.value)
            elif isinstance(sub, ListLit):
                sub = show(tuple(item.value for item in sub.items if isinstance(item, RealLit)))
            elif isinstance(sub, Name) and spec:
                sub = Field(sub, spec, part.pos if isinstance(part, Field) else sub.pos)
            if isinstance(sub, str) and out and isinstance(out[-1], str):
                out[-1] += sub
            elif isinstance(sub, (str, Name, Field)):
                out.append(sub)
        return InterpStrLit(tuple(out), node.pos)
    return node


def _unify(a: str, b: str, pos: Pos) -> str:
    if PENDING in (a, b):
        return b if a == PENDING else a
    if a in NUMERIC and b in NUMERIC:
        return NUMERIC[max(NUMERIC.index(a), NUMERIC.index(b))]
    if a != b:
        raise CompileError(f"the branches have different types: {a} and {b}", pos)
    return a


def _retype(value: Const | Dyn, result: str) -> Value:
    return Const(_convert(value.value, result), result) if isinstance(value, Const) else Dyn(result)


def _fold(op: str, values: list):
    if op == "-" and len(values) == 1:
        return negate(values[0])
    if not values:
        return 0 if op == "+" else 1
    step = {"+": add, "-": subtract, "*": multiply, "/": divide_any}[op]
    return functools.reduce(step, values)


# A part of a known list, from parts that are x, y, z, or index literals.
def _take(value, parts) -> float:
    for part in parts:
        if isinstance(part, IntLit):
            value = value[part.value]
        else:
            assert isinstance(part, str)
            value = value[AXES[part]]
    return value
