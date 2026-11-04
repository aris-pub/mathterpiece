"""The mtp command (docs/data-model.md, "The mtp command"): each subcommand takes one source file
and runs the steps of building it up to a point: parsing, compiling, writing the .mtpc, writing
the page."""

import argparse
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

from mathterpiece import nodes
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.log import setup
from mathterpiece.mtpc import write
from mathterpiece.parse import ParseError, parse

logger = logging.getLogger(__name__)

COMMANDS = {
    "parse": "print the forms the parser reads",
    "check": "report the first error, if any, and write nothing",
    "compile": "write the .mtpc",
    "fmt": "rewrite the file in the house layout, keeping its comments",
}


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(prog="mtp", description="Build a mathterpiece figure.")
    commands = ap.add_subparsers(dest="command", required=True)
    for name, help in COMMANDS.items():
        sub = commands.add_parser(name, help=help)
        sub.add_argument("file")
        if name == "compile":
            sub.add_argument("-o", "--output", help="where to write (default: next to the file)")
        sub.add_argument(
            "-v", "--verbose", action="count", default=0, help="-v info, -vv debug, -vvv trace"
        )
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    setup(args.verbose)
    path = Path(args.file)
    src = _read(path, args.file)
    if args.command == "fmt":
        from mathterpiece.fmt import layout

        _parsed(src, args.file)
        out = layout(src)
        if out != src:
            path.write_text(out, encoding="utf-8")
        return
    forms = _parsed(src, args.file)
    if args.command == "parse":
        for form in forms:
            for line in _tree(form, 0):
                print(line)
        return
    try:
        model = compile_model(forms)
    except CompileError as e:
        _fail(f"{args.file}:{e}")
    if args.command == "check":
        print(f"{args.file}: no errors")
        return
    out = Path(args.output) if args.output else path.with_suffix(".mtpc")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(write(model))
    logger.info("wrote %s", out)


def _read(path: Path, shown: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _fail(f"{shown}: no such file")
    except IsADirectoryError:
        _fail(f"{shown}: cannot be read: it is a folder")
    except UnicodeDecodeError:
        _fail(f"{shown}: cannot be read: it is not UTF-8 text")
    except OSError as e:
        _fail(f"{shown}: cannot be read: {e.strerror}")


def _parsed(src: str, shown: str) -> tuple:
    try:
        return parse(src)
    except ParseError as e:
        _fail(f"{shown}:{e}")


def _tree(node, depth: int) -> Iterator[str]:
    """A node and what it holds, one per line: its position, its kind and its value, indented by
    its depth."""
    pad = "  " * depth
    match node:
        case nodes.Form(items) | nodes.ListLit(items) | nodes.Brackets(items) | nodes.Bar(items):
            kinds = {nodes.Form: "form", nodes.ListLit: "list", nodes.Brackets: "brackets"}
            yield f"{pad}{node.pos} {kinds.get(type(node), 'bar')}"
            for item in items:
                yield from _tree(item, depth + 1)
        case nodes.Name(parts):
            shown = ".".join(p if isinstance(p, str) else "[…]" for p in parts)
            yield f"{pad}{node.pos} name {shown}"
            for part in parts:
                if not isinstance(part, str):
                    yield from _tree(part, depth + 1)
        case nodes.InterpStrLit(parts):
            yield f"{pad}{node.pos} string with values"
            for part in parts:
                if isinstance(part, str):
                    yield f"{pad}  text {part!r}"
                else:
                    yield from _tree(part, depth + 1)
        case nodes.Field(expr, spec):
            yield f"{pad}{node.pos} value{f' :{spec}' if spec else ''}"
            yield from _tree(expr, depth + 1)
        case nodes.StrLit(value):
            yield f"{pad}{node.pos} string {value!r}"
        case nodes.NoneLit():
            yield f"{pad}{node.pos} none"
        case nodes.BoolLit(value):
            yield f"{pad}{node.pos} bool {'true' if value else 'false'}"
        case _:
            kind = {
                nodes.IntLit: "int",
                nodes.RatioLit: "ratio",
                nodes.RealLit: "real",
                nodes.ComplexLit: "complex",
            }[type(node)]
            yield f"{pad}{node.pos} {kind} {node.value}"


def _fail(msg: str) -> NoReturn:
    print(msg, file=sys.stderr)
    sys.exit(1)
