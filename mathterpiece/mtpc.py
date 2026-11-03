"""The .mtpc writer: the world model as JSON, in the form docs/mtpc.md gives and
docs/mtpc.schema.json checks. The same model always gives the same bytes."""

import json
from fractions import Fraction

from mathterpiece.model import Attribute, Expr, FuncDef, Model, Obj, Param
from mathterpiece.types import (
    BOOL,
    COLOR,
    COMPLEX,
    FONT,
    INT,
    POINT,
    RATIO,
    REAL,
    SHAPES,
    TRANSFORM,
    ComponentT,
    FuncT,
    Interface,
    ListT,
    Maybe,
    Prim,
    Refine,
    ShapeT,
    Type,
)

VERSION = 2
# The operations written as ["builtin", T, name, arg…]; every other operation has its own form.
OWN_FORM = {
    "lit", "list", "format", "read", "obj", "check", "local", "call", "apply", "func",
    "builtinfunc", "part", "member", "spread", "if", "and", "or", "rand",
}  # fmt: skip


def write(model: Model) -> str:
    """Keys sorted, no whitespace between tokens, non-ASCII characters as themselves, and one
    newline at the end (mtpc.md, "Same source, same bytes")."""
    doc = Writer(model).doc()
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


class Writer:
    def __init__(self, model: Model):
        self.model = model

    def doc(self) -> dict:
        m = self.model
        return _only_used(
            {
                "mtpc": VERSION,
                "types": [self.declared(name, t) for name, t in m.types.items()],
                "objects": [self.obj(o) for o in m.objects],
                "functions": [self.function(f) for f in m.functions],
                "names": dict(m.names),
            }
        )

    # Types -------------------------------------------------------------------------------

    def declared(self, name: str, t: Type) -> dict:
        m = self.model
        if name in m.motifs:
            return {"name": name, "kind": "motif", "params": self.params(m.motifs[name].params)}
        if name in m.variants:
            v = m.variants[name]
            base = m.types.get(v.base, ShapeT(v.base))
            return {
                "name": name,
                "kind": "variant",
                "params": self.params(v.params),
                "base": self.type(base),
                "fixed": sorted(self.fixed_of(name)),
            }
        return {"name": name, "kind": "type", "type": self.type(t, own=True)}

    def fixed_of(self, name: str) -> set:
        v = self.model.variants.get(name)
        return set() if v is None else set(v.fixed) | self.fixed_of(v.base)

    def params(self, params: tuple[Param, ...]) -> list:
        out = []
        for p in params:
            d = {"name": p.name, "type": self.type(p.type)}
            if p.default is not None:
                d["default"] = self.value(p.type, p.value)
            out.append(d)
        return out

    def type(self, t: Type, own: bool = False) -> object:
        """t as JSON. A named type is written by its name, except as its own declaration."""
        if isinstance(t, Prim):
            return t.name
        if isinstance(t, ShapeT):
            return {"shape": t.name} if t.name in SHAPES else {"named": t.name}
        if isinstance(t, ComponentT):
            return {"component": t.name}
        if isinstance(t, Interface):
            if t.of is None:
                return {"interface": t.name}
            return {"interface": t.name, "of": self.type(t.of)}
        if isinstance(t, ListT):
            return {"list": self.type(t.item)}
        if isinstance(t, FuncT):
            return {"func": [self.type(p) for p in t.params], "result": self.type(t.result)}
        if isinstance(t, Maybe):
            return {"union": [self.type(t.inner), "none"]}
        if isinstance(t, Refine):
            if t.name and not own:
                return {"named": t.name}
            return {
                "refine": self.type(t.base),
                "constraints": [_constraint(c) for c in t.constraints],
            }
        raise TypeError(f"no .mtpc form for the type {t}")

    # Values ------------------------------------------------------------------------------

    def value(self, t: Type, v) -> object:
        """A value as plain JSON, read by its type (mtpc.md, "Values")."""
        if v is None:
            return None
        while isinstance(t, (Maybe, Refine)):
            t = t.inner if isinstance(t, Maybe) else t.base
        if t == RATIO:
            f = Fraction(v)
            return [f.numerator, f.denominator]
        if t == COMPLEX:
            c = complex(v)
            return [_number(c.real), _number(c.imag)]
        if t in (INT, REAL):
            return _number(v)
        if t in (POINT, TRANSFORM):
            return [_number(x) for x in v]
        if isinstance(t, ListT):
            return [self.value(t.item, x) for x in v]
        if t == FONT:
            return {
                k: _number(x) if isinstance(x, (int, float, Fraction)) else x for k, x in v.items()
            }
        if t in (BOOL, COLOR) or isinstance(v, (bool, str)):
            return v
        return v

    # Attributes and expressions --------------------------------------------------------------

    def attribute(self, p: Attribute) -> dict:
        d: dict = {"type": self.type(p.type)}
        if p.bound:
            assert p.expr is not None
            d["bound"] = self.expr(p.expr)
            d["deps"] = _deps(p.deps)
        else:
            d["free"] = self.value(p.type, p.value)
        if p.fixed:
            d["fixed"] = True
        return d

    def expr(self, e: Expr) -> list:
        t = self.type(e.type)
        op, a = e.op, e.args
        if op == "lit":
            return ["lit", t, self.value(e.type, e.value)]
        if op == "list":
            return ["list", t, *(self.expr(x) for x in a)]
        if op == "format":
            parts = [p if isinstance(p, str) else [self.expr(p[0]), p[1]] for p in a]
            return ["format", t, *parts]
        if op == "read":
            return ["read", t, a[0], a[1], a[2]]
        if op == "obj":
            return ["obj", t, a[0]]
        if op == "check":
            return ["check", t, self.expr(a[0]), [_constraint(c) for c in a[1]]]
        if op == "local":
            return ["local", t, a[0]]
        if op == "call":
            return ["call", t, a[0], *(self.expr(x) for x in a[1:])]
        if op == "apply":
            return ["apply", t, self.expr(a[0]), *(self.expr(x) for x in a[1:])]
        if op == "func":
            return ["func", t, a[0], list(a[1])]
        if op == "builtinfunc":
            return ["builtinfunc", t, a[0]]
        if op == "part":
            whole = self.expr(a[0])
            return ["part", t, whole, a[1] if isinstance(a[1], str) else self.expr(a[1])]
        if op == "member":
            # A member found while drawing; with no index, it only stands for what it wraps.
            if a[1] is None:
                return self.expr(a[0])
            return ["part", t, self.expr(a[0]), self.expr(a[1])]
        if op == "spread":
            return ["spread", t, self.expr(a[0]), a[1]]
        if op == "if":
            return ["if", t, *(self.expr(x) for x in a)]
        if op in ("and", "or"):
            return [op, "bool", *(self.expr(x) for x in a)]
        if op == "rand":
            return ["rand", "real", a[0], *(self.expr(x) for x in a[1:])]
        return ["builtin", t, op, *(self.expr(x) for x in a)]

    # Objects -----------------------------------------------------------------------------

    def obj(self, o: Obj) -> dict:
        d = {
            "kind": o.kind,
            "type": self.type(o.type),
            "access": o.access,
            "name": o.name,
        }
        attrs = {k: self.attribute(p) for k, p in o.attrs.items()}
        kind = o.kind
        if kind == "variable":
            d["value"] = self.attribute(o.value)
            d["token"] = _core(o.value.type) in (COLOR, FONT)
        elif kind in ("scene", "group"):
            d["members"] = list(o.members)
            d["attrs"] = attrs
        elif kind == "instance":
            d["of"] = o.of
            d["members"] = list(o.members)
            d["attrs"] = attrs
        elif kind in SHAPES:
            d["attrs"] = attrs
            if o.of is not None:
                d["of"] = o.of
        elif kind == "transition":
            for end in ("from", "to"):
                d[end] = attrs.get(end)
            d["duration"] = _number(o.attrs["duration"].value) if "duration" in o.attrs else None
            d["ease"] = _ease(_ease_of(o.attrs["ease"])) if "ease" in o.attrs else None
            d["path"] = _path(o.attrs.get("path"))
        elif kind == "animation":
            d["steps"] = _step(o.data["steps"])
        elif kind == "canvas":
            d["shows"] = [
                s if isinstance(s, int) else [self.attribute(s[0]), list(s[1])]
                for s in o.data["shows"]
            ]
            d["transition"] = o.data["transition"]
            d["attrs"] = attrs
        elif kind == "readout":
            d["attrs"] = attrs
        elif kind in ("slider", "button", "play"):
            d["animation"] = o.data["animation"]
            d["attrs"] = attrs
            d["conditions"] = self.conditions(o)
            d["when"] = self.attribute(o.data["when"]) if o.data["when"] is not None else None
        elif kind == "toggle":
            target = o.data["target"]
            d["target"] = list(target) if target is not None else None
            d["attrs"] = attrs
            d["conditions"] = self.conditions(o)
            d["when"] = self.attribute(o.data["when"]) if o.data["when"] is not None else None
        elif kind == "on-drag":
            d["shape"] = o.data["shape"]
            d["target"] = list(o.data["target"])
            d["conditions"] = self.conditions(o)
            d["when"] = self.attribute(o.data["when"]) if o.data["when"] is not None else None
        elif kind == "on-click":
            d["shape"] = o.data["shape"]
            d["animation"] = o.data["animation"]
            d["when"] = self.attribute(o.data["when"]) if o.data["when"] is not None else None
            d["conditions"] = self.conditions(o)
        return d

    def conditions(self, o: Obj) -> list:
        return [
            {"target": list(c["target"]), "op": c["op"], "limit": self.attribute(c["limit"])}
            for c in o.data["conditions"]
        ]

    def function(self, f: FuncDef) -> dict:
        assert f.body is not None
        return {
            "params": self.params(f.params),
            "result": self.type(f.result),
            "body": self.expr(f.body),
        }


def _function_id(x) -> int | None:
    """The function a part of the document refers to: a call or a function value, written
    ["call", T, id, …] or ["func", T, id, …], or {"func": id} (a value, an ease or a path)."""
    if isinstance(x, list) and len(x) > 2 and x[0] in ("call", "func"):
        f = x[2]
    elif isinstance(x, dict):
        f = x.get("func")
    else:
        return None
    return f if isinstance(f, int) and not isinstance(f, bool) else None


def _only_used(doc: dict) -> dict:
    """The document with only the functions and declared types its objects reach, directly or
    through other functions and types, the functions numbered again in their order (mtpc.md,
    "Top level")."""
    functions, types = doc["functions"], {t["name"]: t for t in doc["types"]}
    used_f: set[int] = set()
    used_t: set[str] = set()
    todo: list = [doc["objects"]]
    while todo:
        x = todo.pop()
        f = _function_id(x)
        if f is not None and f not in used_f:
            used_f.add(f)
            todo.append(functions[f])
        if isinstance(x, dict):
            for key in ("named", "of"):
                n = x.get(key)
                if isinstance(n, str) and n in types and n not in used_t:
                    used_t.add(n)
                    todo.append(types[n])
            todo.extend(x.values())
        elif isinstance(x, list):
            todo.extend(x)
    new = {old: k for k, old in enumerate(sorted(used_f))}

    def renumber(x):
        if isinstance(x, list):
            out = [renumber(y) for y in x]
            if _function_id(x) is not None:
                out[2] = new[x[2]]
            return out
        if isinstance(x, dict):
            out = {k: renumber(v) for k, v in x.items()}
            if _function_id(x) is not None:
                out["func"] = new[x["func"]]
            return out
        return x

    return {
        **doc,
        "types": [t for t in doc["types"] if t["name"] in used_t],
        "objects": renumber(doc["objects"]),
        "functions": [renumber(functions[old]) for old in sorted(used_f)],
    }


def _core(t: Type) -> Type:
    while isinstance(t, (Maybe, Refine)):
        t = t.inner if isinstance(t, Maybe) else t.base
    return t


def _number(v):
    """A number in its shortest form that reads back exactly: an int when it is a whole number
    small enough to be exact, else the float's shortest digits."""
    if isinstance(v, bool):
        return v
    if isinstance(v, Fraction):
        v = v.numerator if v.denominator == 1 else float(v)
    if isinstance(v, float) and v.is_integer() and abs(v) < 2**53:
        return int(v)
    return v


def _constraint(c: tuple) -> list:
    if c[0] == "one-of":
        return ["one-of", list(c[1])]
    if c[0] in (">=", ">", "<=", "<"):
        return [c[0], _number(c[1])]
    return list(c)


def _deps(deps) -> list:
    return [list(d) for d in sorted(deps, key=lambda d: (d[0], d[1] or ""))]


def _ease_of(attribute: Attribute):
    return ("func", attribute.expr.args[0]) if attribute.expr is not None else attribute.value


def _ease(e) -> object:
    if isinstance(e, str):
        return e
    if e[0] == "func":
        return {"func": e[1]}
    return [e[0], _number(e[1])]


def _path(attribute: Attribute | None) -> object:
    if attribute is None:
        return None
    assert attribute.expr is not None
    return {"func": attribute.expr.args[0]}


def _step(step: tuple) -> list:
    if step[0] == "move":
        _, (i, attr), tid, duration, ease = step
        return ["move", [i, attr], tid, _number(duration), _ease(ease)]
    if step[0] == "wait":
        return ["wait", _number(step[1])]
    if step[0] == "loop":
        return ["loop", step[1], _step(step[2])]
    return [step[0], *(_step(s) for s in step[1:])]
