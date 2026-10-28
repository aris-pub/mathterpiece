import math
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, get_args

from mathterpiece.nodes import (
    BoolLit,
    ComplexLit,
    Form,
    InterpStrLit,
    IntLit,
    Name,
    Node,
    Pos,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.scene import (
    Bound,
    Canvas,
    Circle,
    Free,
    Group,
    Obj,
    Real,
    Scene,
    Text,
    Visual,
    attributes,
    variadic,
)

BUILTINS = [
    (("pi", "π"), math.pi),
    (("tau", "τ"), math.tau),
    (("euler",), math.e),
    (("infty", "∞"), math.inf),
]

NUMERIC = ["int", "ratio", "real", "complex"]
PY_TYPES = {float: "real", str: "str", bool: "bool"}
ARITHMETIC = {"+", "-", "*", "/"}


@dataclass(frozen=True)
class FormSpec:
    cls: type[Obj]
    positional: tuple[str, ...] = ()


FORMS = {
    "circle": FormSpec(Circle),
    "text": FormSpec(Text, ("value",)),
    "real": FormSpec(Real, ("value",)),
    "group": FormSpec(Group),
    "canvas": FormSpec(Canvas),
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


Value = Const | Dyn | Spread | ObjRef


def compile_scene(forms: tuple[Form, ...]) -> Scene:
    return _Compiler(forms).compile()


def _head(node: Node) -> str | None:
    if isinstance(node, Form) and isinstance(node.items[0], Name):
        parts = node.items[0].parts
        if len(parts) == 1 and isinstance(parts[0], str):
            return parts[0]
    return None


def _defined_names(nodes) -> set[str]:
    names: set[str] = set()
    for node in nodes:
        if isinstance(node, Form):
            if _head(node) in FORMS and len(node.items) > 1 and isinstance(node.items[1], StrLit):
                names.add(node.items[1].value)
            names |= _defined_names(node.items)
    return names


def _widens_to(src: str, dst: str) -> bool:
    if src in NUMERIC and dst in NUMERIC:
        return NUMERIC.index(src) <= NUMERIC.index(dst)
    return src == dst


CONVERT = {"int": int, "ratio": Fraction, "real": float, "complex": complex}


def _convert(value, dst: str):
    return CONVERT[dst](value) if dst in CONVERT else value


def _expected_type(cls: type[Obj], attr: str) -> str:
    (arg,) = get_args(attributes(cls)[attr].type)
    return PY_TYPES[arg]


class _Compiler:
    def __init__(self, forms: tuple[Form, ...]):
        self.forms = forms
        self.names: dict[str, Obj] = {}
        self.builtins: list[tuple[Obj, tuple[str, ...]]] = []
        self.toplevel: list[Obj] = []

    def compile(self) -> Scene:
        self.add_builtins()
        for form in self.forms:
            self.toplevel.extend(self.toplevel_item(form, {}))
        scene = Scene()
        for obj, names in self.builtins:
            scene.add(obj)
            for alias in names[1:]:
                scene.alias(alias, names[0])
        for obj in self.toplevel:
            scene.add(obj)
        return scene

    def add_builtins(self):
        taken = _defined_names(self.forms)
        for names, value in BUILTINS:
            available = tuple(name for name in names if name not in taken)
            if not available:
                continue
            obj = Real(name=available[0], value=Free(value))
            self.builtins.append((obj, available))
            for name in available:
                self.names[name] = obj

    def register(self, obj: Obj, pos: Pos):
        if obj.name is None:
            return
        if obj.name in self.names:
            raise CompileError(f"name {obj.name!r} is already defined", pos)
        self.names[obj.name] = obj

    def toplevel_item(self, form: Form, env: dict[str, int]) -> list[Obj]:
        head = _head(form)
        if head == "repeat":
            return self.repeat(form, env, self.toplevel_item)
        if head in FORMS:
            return [self.definition(form, env)]
        if head is None:
            raise CompileError("expected a definition", form.pos)
        if head in ARITHMETIC or head == "rand" or head in self.names:
            raise CompileError(f"{head!r} is not a definition", form.pos)
        raise CompileError(f"unknown form {head!r}", form.pos)

    def repeat[T](
        self, form: Form, env: dict[str, int], item: Callable[[Form, dict[str, int]], list[T]]
    ) -> list[T]:
        if len(form.items) < 3:
            raise CompileError("repeat takes a variable, a count, and a body", form.pos)
        var, count_node, *body = form.items[1:]
        if not (isinstance(var, Name) and len(var.parts) == 1 and isinstance(var.parts[0], str)):
            raise CompileError("the repeat variable must be a name", var.pos)
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

    def object_name(self, form: Form, env: dict[str, int]) -> str | None:
        if len(form.items) < 2:
            raise CompileError(f"{_head(form)} needs a name", form.pos)
        node = form.items[1]
        if isinstance(node, StrLit):
            return node.value
        if isinstance(node, Name) and node.parts == ("_",):
            return None
        if isinstance(node, InterpStrLit):
            value = self.expr(node, env)
            if isinstance(value, Const):
                return str(value.value)
            raise CompileError("a name must be known at compile time", node.pos)
        raise CompileError("expected a name: a string, an interpolated string, or _", node.pos)

    def definition(self, form: Form, env: dict[str, int]) -> Obj:
        head = _head(form)
        assert head is not None
        spec = FORMS[head]
        name = self.object_name(form, env)
        attrs = attributes(spec.cls)
        var = variadic(spec.cls)
        settable = {a for a in attrs if a not in spec.positional and (var is None or a != var.name)}
        rest = list(form.items[2:])
        values: dict[str, Free | Bound] = {}

        for field_name in spec.positional:
            if rest and _head(rest[0]) not in settable:
                if _head(rest[0]) == field_name:
                    raise CompileError(
                        f"the {field_name} of {head} is given by position", rest[0].pos
                    )
                node = rest.pop(0)
                values[field_name] = self.attr_value(spec.cls, field_name, node, env)

        while rest and _head(rest[0]) in settable:
            node = rest.pop(0)
            assert isinstance(node, Form)
            attr = _head(node)
            assert attr is not None
            if attr in values:
                raise CompileError(f"attribute {attr!r} is given twice", node.pos)
            if len(node.items) != 2:
                raise CompileError(f"attribute {attr!r} takes exactly one value", node.pos)
            values[attr] = self.attr_value(spec.cls, attr, node.items[1], env)

        kwargs: dict[str, Any] = dict(values)
        if var is not None:
            members: list[Visual] = []
            for node in rest:
                members.extend(self.member(node, env, head, settable))
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

    def member(self, node: Node, env: dict[str, int], container: str, settable) -> list[Visual]:
        head = _head(node)
        if isinstance(node, Form) and head == "repeat":
            return self.repeat(node, env, lambda n, e: self.member(n, e, container, settable))
        if isinstance(node, Form) and head in FORMS:
            obj = self.definition(node, env)
            if not isinstance(obj, Visual):
                raise CompileError(f"{head} cannot be a member of {container}", node.pos)
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
                return [value.obj]
        raise CompileError(f"not a valid member of {container}", node.pos)

    def attr_value(self, cls: type[Obj], attr: str, node: Node, env: dict[str, int]):
        expected = _expected_type(cls, attr)
        value = self.expr(node, env)
        if isinstance(value, ObjRef):
            raise CompileError("expected a value, got an object", node.pos)
        if isinstance(value, Spread):
            raise CompileError(
                "a group attribute gives several values where one is expected", node.pos
            )
        if not _widens_to(value.type, expected):
            raise CompileError(f"expected {expected}, got {value.type}", node.pos)
        if isinstance(value, Const):
            return Free(_convert(value.value, expected))
        return Bound(node)

    def expr(self, node: Node, env: dict[str, int]) -> Value:
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
            case Name():
                return self.name(node, env)
            case Form():
                return self.call(node, env)

    def interp(self, node: InterpStrLit, env: dict[str, int]) -> Value:
        text: list[str] = []
        constant = True
        for part in node.parts:
            if isinstance(part, str):
                text.append(part)
                continue
            value = self.name(part, env)
            if isinstance(value, ObjRef):
                raise CompileError("cannot put an object in a string", part.pos)
            if isinstance(value, Const):
                text.append(str(value.value))
            else:
                constant = False
        return Const("".join(text), "str") if constant else Dyn("str")

    def name(self, node: Name, env: dict[str, int]) -> Value:
        first, *rest = node.parts
        assert isinstance(first, str)
        if first in env:
            if rest:
                raise CompileError(f"{first!r} is a number and has no attributes", node.pos)
            return Const(env[first], "int")
        if first not in self.names:
            raise CompileError(f"undefined name {first!r}", node.pos)
        current: Value = ObjRef(self.names[first])
        for part in rest:
            current = self.access(current, part, env, node.pos)
        if isinstance(current, ObjRef) and isinstance(current.obj, Real):
            return Dyn("real")
        return current

    def access(self, current: Value, part: str | Node, env: dict[str, int], pos: Pos) -> Value:
        if not isinstance(current, ObjRef):
            raise CompileError("only objects have attributes or members", pos)
        obj = current.obj
        if not isinstance(part, str):
            return self.index(obj, part, env)
        if isinstance(obj, Group) and part != "members":
            types = []
            for member in obj.members:
                if part not in attributes(type(member)):
                    raise CompileError(f"a member of {obj.name!r} has no attribute {part!r}", pos)
                types.append(_expected_type(type(member), part))
            return Spread(tuple(types))
        attrs = attributes(type(obj))
        if part not in attrs or variadic(type(obj)) is attrs[part]:
            raise CompileError(f"{obj.name!r} has no attribute {part!r}", pos)
        return Dyn(_expected_type(type(obj), part))

    def index(self, obj: Obj, node: Node, env: dict[str, int]) -> Value:
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

    def call(self, node: Form, env: dict[str, int]) -> Value:
        head = _head(node)
        args = node.items[1:]
        if head in ARITHMETIC:
            return self.arithmetic(head, node, env)
        if head == "rand":
            if len(args) not in (0, 2):
                raise CompileError("rand takes no arguments or two", node.pos)
            for arg in args:
                value = self.expr(arg, env)
                if isinstance(value, (ObjRef, Spread)) or not _widens_to(value.type, "real"):
                    raise CompileError("rand takes real numbers", arg.pos)
            return Dyn("real")
        if head in FORMS or head == "repeat":
            raise CompileError(f"{head} cannot be used in an expression", node.pos)
        raise CompileError(f"unknown function {head!r}", node.pos)

    def arithmetic(self, op: str, node: Form, env: dict[str, int]) -> Value:
        types: list[str] = []
        consts: list[Const] = []
        dynamic = False
        for arg in node.items[1:]:
            value = self.expr(arg, env)
            if isinstance(value, ObjRef):
                raise CompileError("expected a number, got an object", arg.pos)
            arg_types = value.types if isinstance(value, Spread) else (value.type,)
            for t in arg_types:
                if t not in NUMERIC:
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
        rank = max((NUMERIC.index(t) for t in types), default=0)
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


def _fold(op: str, values: list):
    if op == "+":
        return sum(values)
    if op == "*":
        return math.prod(values)
    if op == "-":
        return -values[0] if len(values) == 1 else values[0] - sum(values[1:])
    result = values[0]
    for v in values[1:]:
        result = result / v
    return result
