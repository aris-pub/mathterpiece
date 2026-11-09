"""The .mtpc writer: the world model as JSON, in the form docs/mtpc.md gives and
docs/mtpc.schema.json checks. The same model always gives the same bytes."""

import json
import math
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

VERSION = 4
# The operations written as ["builtin", T, name, arg…]; every other operation has its own form.
OWN_FORM = {
    "lit", "list", "format", "read", "obj", "check", "local", "call", "apply", "func",
    "builtinfunc", "part", "member", "spread", "if", "and", "or", "rand", "anchor", "wrap",
    "rand-int", "pick", "shuffle",
}  # fmt: skip


def write(model: Model) -> str:
    """Keys sorted, no whitespace between tokens, non-ASCII characters as themselves, and one
    newline at the end (mtpc.md, "Same source, same bytes")."""
    doc = Writer(model).doc()
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


class Writer:
    def __init__(self, model: Model):
        self.model = model
        # Each structured type, written once, by its position (mtpc.md, "Top level").
        self.table: list = []
        self.table_index: dict[str, int] = {}

    def doc(self) -> dict:
        m = self.model
        doc = {
            "mtpc": VERSION,
            "types": [self.declared(name, t) for name, t in m.types.items()],
            "objects": [self.obj(o) for o in m.objects],
            "functions": [self.function(f) for f in m.functions],
            "names": dict(m.names),
        }
        if self.table:
            doc["type-table"] = self.table
        return _shared(_only_used(doc))

    def ref(self, t: Type, own: bool = False) -> object:
        """t where a type is written at the top of something: a plain name as it is, and a
        structured type by its position in the type table, written there once."""
        j = self.type(t, own)
        if isinstance(j, str):
            return j
        key = json.dumps(j, sort_keys=True)
        if key not in self.table_index:
            self.table_index[key] = len(self.table)
            self.table.append(j)
        return self.table_index[key]

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
                "base": self.ref(base),
                "fixed": sorted(self.fixed_of(name)),
            }
        return {"name": name, "kind": "type", "type": self.ref(t, own=True)}

    def fixed_of(self, name: str) -> set:
        v = self.model.variants.get(name)
        return set() if v is None else set(v.fixed) | self.fixed_of(v.base)

    def params(self, params: tuple[Param, ...]) -> list:
        out = []
        for p in params:
            d = {"name": p.name, "type": self.ref(p.type)}
            # A function given as a default is not a value the .mtpc writes.
            if p.default is not None and not hasattr(p.value, "op"):
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
        d: dict = {"type": self.ref(p.type)}
        if p.bound:
            assert p.expr is not None
            d["bound"] = self.expr(p.expr)
            d["deps"] = _deps(p.deps)
        elif p.start is not None:
            d["start"] = self.expr(p.start)
            d["deps"] = _deps(p.deps)
        else:
            d["free"] = self.value(p.type, p.value)
        if p.fixed:
            d["fixed"] = True
        return d

    def expr(self, e: Expr) -> list:
        t = self.ref(e.type)
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
        if op == "wrap":
            return ["wrap", t, self.expr(a[0]), _number(a[1]), _number(a[2])]
        if op == "local":
            return ["local", t, a[0]]
        if op == "let":
            return ["let", t, [[n, self.expr(x)] for n, x in a[0]], self.expr(a[1])]
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
        if op == "anchor":
            return ["anchor", t, a[0], self.expr(a[1]), self.expr(a[2]), a[3]]
        if op in ("rand", "rand-int", "pick", "shuffle"):
            # The place it is written, then the seed it follows, then its arguments (mtp-bjn0).
            return [op, t, a[0], *(self.expr(x) for x in a[1:])]
        return ["builtin", t, op, *(self.expr(x) for x in a)]

    # Objects -----------------------------------------------------------------------------

    def obj(self, o: Obj) -> dict:
        d = {
            "kind": o.kind,
            "type": self.ref(o.type),
            "access": o.access,
            "name": o.name,
        }
        if o.data.get("doc") is not None:
            d["doc"] = o.data["doc"]
        attrs = {k: self.attribute(p) for k, p in o.attrs.items()}
        kind = o.kind
        if kind == "variable":
            d["value"] = self.attribute(o.value)
            d["token"] = _core(o.value.type) in (COLOR, FONT)
            if "let" in o.data:
                d["let"] = o.data["let"]
            if o.data.get("links"):
                d["links"] = dict(o.data["links"])
        elif kind in ("scene", "group"):
            d["members"] = list(o.members)
            d["attrs"] = attrs
            if "clip" in o.data:
                d["clip"] = o.data["clip"]
            if o.data.get("fixed-size"):
                d["fixed-size"] = True
            if "layout" in o.data:
                layout = o.data["layout"]
                d["layout"] = {
                    "axis": layout["axis"],
                    "gap": self.attribute(layout["gap"]),
                    "align": self.attribute(layout["align"]),
                }
        elif kind == "namespace":
            d["members"] = list(o.members)
        elif kind == "formula":
            d["tex"] = o.data["tex"]
            d["members"] = list(o.members)
        elif kind == "term":
            d["term"] = o.data["term"]
            d["formula"] = o.parent
            d["attrs"] = attrs
        elif kind == "display":
            d["formula"] = o.data["formula"]
            d["as"] = o.data["as"]
        elif kind == "instance":
            d["of"] = o.of
            d["members"] = list(o.members)
            d["attrs"] = attrs
            if "clip" in o.data:
                d["clip"] = o.data["clip"]
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
            if "names" in o.data:
                d["names"] = o.data["names"]
        elif kind == "canvas":
            d["shows"] = [s if isinstance(s, int) else self.attribute(s) for s in o.data["shows"]]
            d["transition"] = o.data["transition"]
            d["attrs"] = attrs
        elif kind == "readout":
            d["attrs"] = attrs
        elif kind in ("slider", "button", "play"):
            if kind == "play":
                d["autoplay"] = o.data["autoplay"]
                if "rest" in o.data:
                    d["rest"] = _number(o.data["rest"])
            d["animation"] = o.data["animation"]
            d["attrs"] = attrs
            d["conditions"] = self.conditions(o)
            d["active"] = self.attribute(o.data["active"]) if o.data["active"] is not None else None
        elif kind == "toggle":
            target = o.data["target"]
            d["target"] = list(target) if target is not None else None
            d["animation"] = o.data["animation"]
            d["attrs"] = attrs
            d["conditions"] = self.conditions(o)
            d["active"] = self.attribute(o.data["active"]) if o.data["active"] is not None else None
        elif kind == "on-drag":
            d["shape"] = o.data["shape"]
            d["target"] = list(o.data["target"])
            if "map" in o.data:
                d["map"] = self.attribute(o.data["map"])
            d["conditions"] = self.conditions(o)
            d["active"] = self.attribute(o.data["active"]) if o.data["active"] is not None else None
        elif kind in ("on-view", "on-live", "on-quiet"):
            d["view"] = o.data["view"]
            d["animation"] = o.data["animation"]
            d["active"] = self.attribute(o.data["active"]) if o.data["active"] is not None else None
            d["conditions"] = self.conditions(o)
        elif kind == "on-pointermove":
            d["shape"] = o.data["shape"]
            d["view"] = o.data["view"]
            d["target"] = list(o.data["target"])
            d["conditions"] = self.conditions(o)
            d["active"] = self.attribute(o.data["active"]) if o.data["active"] is not None else None
            d["stop-propagation"] = self.stop(o)
        elif kind in ("on-click", "on-release", "on-dragstart", "on-dragend"):
            d["shape"] = o.data["shape"]
            d["animation"] = o.data["animation"]
            d["active"] = self.attribute(o.data["active"]) if o.data["active"] is not None else None
            d["conditions"] = self.conditions(o)
            d["stop-propagation"] = self.stop(o)
        elif kind in ("on-enter", "on-leave"):
            d["shape"] = o.data["shape"]
            d["animation"] = o.data["animation"]
            d["active"] = self.attribute(o.data["active"]) if o.data["active"] is not None else None
            d["conditions"] = self.conditions(o)
        # Written only when given, so a figure that ties nothing is as small as before.
        if o.data.get("in") is not None:
            d["in"] = list(o.data["in"])
        return d

    def stop(self, o: Obj):
        stop = o.data["stop-propagation"]
        return self.attribute(stop) if stop is not None else None

    def conditions(self, o: Obj) -> list:
        return [
            {"target": list(c["target"]), "op": c["op"], "limit": self.attribute(c["limit"])}
            for c in o.data["conditions"]
        ]

    def function(self, f: FuncDef) -> dict:
        assert f.body is not None
        d = {
            "params": self.params(f.params),
            "result": self.ref(f.result),
            "body": self.expr(f.body),
        }
        doc = self.model.docs.get(("func", f.name)) if f.name else None
        if doc is not None:
            d["doc"] = doc
        return d


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


def _shared(doc: dict) -> dict:
    """The document with each attribute's most common value among the shapes of one kind written
    once, in shared, and left out of the shapes that have it; the others keep their own.
    Instances are grouped by their motif (mtpc.md, "Top level"). The runtime puts each back in
    every shape of its kind that does not give it when it loads the file."""
    groups: dict[str, list[dict]] = {}
    for o in doc["objects"]:
        if "attrs" in o:
            key = o["kind"] if o["kind"] != "instance" else f"instance:{o['of']}"
            groups.setdefault(key, []).append(o)
    shared: dict[str, dict] = {}
    for key, objs in sorted(groups.items()):
        if len(objs) < 2:
            continue
        table: dict[str, object] = {}
        common: dict[str, str] = {}
        # Only an attribute every shape of the kind has: one that a shape lacks must stay lacking.
        for attr in sorted(set.intersection(*(set(o["attrs"]) for o in objs))):
            counts: dict[str, int] = {}
            for o in objs:
                text = json.dumps(o["attrs"][attr], sort_keys=True)
                counts[text] = counts.get(text, 0) + 1
            text, n = max(sorted(counts.items()), key=lambda kv: kv[1])
            if n >= 2:
                table[attr], common[attr] = json.loads(text), text
        if table:
            shared[key] = table
            for o in objs:
                o["attrs"] = {
                    k: v
                    for k, v in o["attrs"].items()
                    if common.get(k) != json.dumps(v, sort_keys=True)
                }
    return {**doc, "shared": shared} if shared else doc


def _only_used(doc: dict) -> dict:
    """The document with only the functions and declared types its objects reach, directly or
    through other functions and types, the functions numbered again in their order (mtpc.md,
    "Top level")."""
    functions, types = doc["functions"], {t["name"]: t for t in doc["types"]}
    used_f: set[int] = set()
    used_t: set[str] = set()
    # A declared type may be named only in the type table, where structured types are written.
    todo: list = [doc["objects"], doc.get("type-table", [])]
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
    if isinstance(v, float) and math.isinf(v):
        # JSON has no infinity (mtpc.md, "Values").
        return "infty" if v > 0 else "-infty"
    if isinstance(v, float) and v.is_integer() and abs(v) < 2**53:
        return int(v)
    return v


def _constraint(c: tuple) -> list:
    if c[0] == "one-of":
        return ["one-of", list(c[1])]
    if c[0] in (">=", ">", "<=", "<"):
        return [c[0], _number(c[1])]
    if c[0] == "wrap":
        return ["wrap", _number(c[1]), _number(c[2])]
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
