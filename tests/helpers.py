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
    for o in d["objects"]:
        group = o["kind"] if o["kind"] != "instance" else f"instance:{o.get('of')}"
        if "attrs" in o and group in d.get("shared", {}):
            o["attrs"] = {**d["shared"][group], **o["attrs"]}
    return d
