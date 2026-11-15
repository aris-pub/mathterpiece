"""Helpers for the conformance tests of the spec (docs/spec).

These tests check only what the spec makes normative (rule what-is-normative): which sources are
accepted and which are rejected, the meaning of the .mtpc, and what the runtime does. A rejection
test checks that compiling fails, and the kind of the error (a syntax error of the parse step, or
a compile error of a later step), and never the wording of the error."""

import json
from pathlib import Path

import pytest
from helpers import doc as _doc

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.model import Model
from mathterpiece.mtpc import write
from mathterpiece.nodes import Form, Name
from mathterpiece.parse import ParseError, parse

ROOT = Path(__file__).parent.parent.parent
SPEC = ROOT / "docs" / "spec"
# What a step of compiling raises when it rejects a source.
REJECTION = (ParseError, CompileError)


def forms(src: str) -> tuple:
    """The expressions that the parser produces for a source."""
    return parse(src)


def items(src: str) -> tuple:
    """The items after the head of the one form of a source such as (f a b)."""
    (form,) = parse(src)
    return form.items[1:]


def syntax_error(src: str) -> None:
    """The parse step rejects the source."""
    with pytest.raises(ParseError):
        parse(src)


def compile_error(src: str, path: Path | None = None) -> None:
    """The parse step passes the source, and a later step rejects it."""
    parse(src)
    with pytest.raises(CompileError):
        compile_source(src, path=path)


def rejected(src: str, path: Path | None = None) -> None:
    """Some step rejects the source."""
    with pytest.raises((ParseError, CompileError)):
        compile_source(src, path=path)


def accepted(src: str, path: Path | None = None) -> Model:
    return compile_source(src, path=path)


def mtpc(src: str, path: Path | None = None) -> dict:
    """The .mtpc of a source, as JSON, with its type table and shared values put back in place."""
    return _doc(src, path=path)


def raw_mtpc(src: str, path: Path | None = None) -> dict:
    """The .mtpc of a source, as JSON, as the compiler writes it."""
    return json.loads(write(compile_source(src, path=path)))


def same_meaning(written: str, rewrite: str, path: Path | None = None) -> None:
    """The two sources give the same .mtpc, read as JSON."""
    assert mtpc(written, path) == mtpc(rewrite, path)


def value(src: str, name: str, path: Path | None = None):
    """The folded value of a variable known when compiling."""
    attribute = compile_source(src, path=path).get(name).value
    assert not attribute.bound, f"{name} is not known when compiling"
    return attribute.value


def is_bound(src: str, name: str) -> bool:
    return compile_source(src).get(name).value.bound


def obj(d: dict, name: str) -> dict:
    """The object of a .mtpc by its name."""
    return d["objects"][d["names"][name]]


def free(d: dict, name: str, attr: str | None = None):
    """The free value of a variable, or of an attribute of an object, in a .mtpc."""
    o = obj(d, name)
    slot = o["value"] if attr is None else o["attrs"][attr]
    assert "free" in slot, f"{name} {attr or ''} is bound"
    return slot["free"]


def in_folder(folder: Path, files: dict[str, str], main: str) -> Model:
    """Writes each file into the folder, then compiles the source main from a file there."""
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    path = folder / "main.mtp"
    path.write_text(main, encoding="utf-8")
    return compile_source(main, path=path)


def name(*parts) -> Name:
    return Name(tuple(parts))


def form(*items) -> Form:
    return Form(tuple(items))
