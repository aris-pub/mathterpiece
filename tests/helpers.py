"""Helpers shared by the compiler tests."""

import json

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.mtpc import write


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def value(src, name="v"):
    """The folded value of a variable known when compiling."""
    attribute = model(src).get(name).value
    assert not attribute.bound, f"{name} is not known when compiling"
    return attribute.value


def bound(src, name="v"):
    """The expression of a variable known only while drawing."""
    attribute = model(src).get(name).value
    assert attribute.bound
    return attribute.expr


def typ(src, name="v"):
    attribute = model(src).get(name).value
    return attribute.expr.type if attribute.bound else attribute.type


def doc(src, path=None):
    """The .mtpc document written for a source, as JSON, with each shape's shared attribute
    values put back in its attrs as the runtime does when it loads the file (mtp-jru8)."""
    d = json.loads(write(compile_source(src, path=path)))
    expand_types(d)
    for o in d["objects"]:
        group = o["kind"] if o["kind"] != "instance" else f"instance:{o.get('of')}"
        if "attrs" in o and group in d.get("shared", {}):
            o["attrs"] = {**d["shared"][group], **o["attrs"]}
    return d


# The expression forms, whose second item is always the expression's type (docs/mtpc.md).
OPS = {
    "lit", "list", "format", "read", "obj", "check", "wrap", "local", "call", "apply", "func",
    "builtinfunc", "part", "spread", "if", "and", "or", "anchor", "rand", "builtin",
}  # fmt: skip


def expand_types(d: dict) -> None:
    """Puts each type written by its position in type-table back in its place, as the runtime
    does when it loads the file (mtp-qje3)."""
    table = d.pop("type-table", [])

    def at(t):
        return table[t] if isinstance(t, int) and not isinstance(t, bool) else t

    def walk(x):
        if isinstance(x, dict):
            for key in ("type", "result", "base"):
                if key in x:
                    x[key] = at(x[key])
            # A type's constraints hold no expression, and ["wrap", lo, hi] is not one.
            for key, v in x.items():
                if key != "constraints":
                    walk(v)
        elif isinstance(x, list):
            if len(x) >= 2 and isinstance(x[0], str) and x[0] in OPS:
                x[1] = at(x[1])
            for v in x:
                walk(v)

    if table:
        for key in ("types", "objects", "functions", "shared"):
            if key in d:
                walk(d[key])
