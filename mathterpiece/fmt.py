"""mtp fmt: a source file in the house layout (docs/data-model.md, "The mtp command"). Each line
is indented as the Emacs mode (editors/mtp-mode.el) indents it, trailing spaces are dropped, at
most one blank line is kept in a row, (doc 'text') is written doc@'text', and nothing else
changes: it works on lines, not on parsed forms, so comments and how the author broke the lines
stay as written."""

import re
from dataclasses import dataclass, field

# How many positional arguments each form takes before its body, counting its name: their lines go
# 4 in from the form's opening parenthesis, its body's 2. The same table as the Emacs mode's.
INDENT = {
    **dict.fromkeys(
        ["scene", "group", "row", "column", "circle", "rect", "ellipse", "line", "triangle"], 1
    ),
    **dict.fromkeys(
        ["polyline", "polygon", "arc", "ring", "font", "animation", "canvas", "namespace"], 1
    ),
    **dict.fromkeys(["palette", "curve", "formula", "term"], 1),
    **dict.fromkeys(["button", "play", "stepper", "interface"], 1),
    "text": 2,
    **dict.fromkeys(
        ["real", "int", "ratio", "complex", "bool", "string", "point", "list", "transform"], 2
    ),
    "rand-seed": 2,
    **dict.fromkeys(["color", "type", "motif", "variant", "func", "transition", "readout"], 2),
    "slider": 2,
    "display": 2,
    "colormap": 2,
    "toggle": 2,
    **dict.fromkeys(["move", "on-click", "on-release", "on-dragend", "on-view", "exists-when"], 1),
    **dict.fromkeys(["on-dragstart", "on-enter", "on-leave", "on-live", "on-quiet"], 1),
    **dict.fromkeys(["at-once", "in-order", "defaults"], 0),
    "step": 1,
    "on-drag": 2,
    "on-pointermove": 2,
    "when": 1,
    "foreach": 2,
    "let": 1,
    "fn": 1,
    "if": 2,
}
# Forms that take a name, so that (head_ …), or one with a list where its name would be, has one
# positional argument fewer before its body.
NAMED = {
    *["scene", "group", "row", "column", "circle", "rect", "ellipse", "line", "triangle"],
    *[
        "polyline",
        "curve",
        "polygon",
        "arc",
        "ring",
        "text",
        "font",
        "real",
        "int",
        "ratio",
        "complex",
        "bool",
    ],
    *["string", "point", "list", "transform", "color", "type", "motif", "variant", "func"],
    *["transition", "animation", "canvas", "readout", "slider", "button", "play", "toggle"],
    "stepper",
    "namespace",
    "palette",
    "interface",
    "colormap",
    "formula",
    "display",
}
# Forms that take a body, and their keyword arguments. A keyword argument on a line of its own goes
# 4 in, like a positional argument, so it reads apart from the body at 2. The same table as the
# Emacs mode's.
_GROUP = {
    *["doc", "defaults", "clip", "fixed-size", "translate", "transform", "gap", "align", "opacity"],
    *["fill", "stroke"],
    *["stroke-width", "fill-opacity", "stroke-opacity", "dash", "line-cap", "line-join"],
    *["x", "y", "pos"],
}
_CANVAS = {
    *["doc", "x", "y", "width", "height", "transform", "pan", "zoom", "toggle-duration"],
    "toggle-ease",
}
_ANIMATION = {"loop", "duration", "ease", "defaults"}
KEYWORDS = {
    "scene": {"doc", "background", "transform"},
    **{head: _GROUP for head in ["group", "row", "column"]},
    "canvas": _CANVAS,
    "animation": _ANIMATION | {"doc"},
    **{head: _ANIMATION for head in ["at-once", "in-order"]},
    "step": {"defaults"},
    **{head: {"doc"} for head in ["motif", "variant", "func", "namespace", "palette"]},
    "formula": {"doc", "defaults"},
}
# Forms that take no body: every item after their positional arguments goes 4 in. The same list
# as the Emacs mode's.
NO_BODY = {
    *["circle", "rect", "ellipse", "line", "triangle", "polyline", "polygon", "arc", "ring"],
    *["curve"],
    *["text", "slider", "button", "play", "stepper", "toggle", "readout", "on-drag"],
    "on-click",
    *["on-release", "on-dragend", "on-view", "move", "transition", "font", "color"],
    *["on-dragstart", "on-enter", "on-leave", "on-pointermove", "on-live", "on-quiet"],
    *["real", "int", "ratio", "complex", "bool", "string", "point", "list", "transform"],
    *["colormap", "interface", "defaults", "term", "display", "rand-seed"],
}
OPEN, CLOSE = "([", ")]"
_DOC = re.compile(r"\(doc\s+('(?:[^'\\]|\\.)*')\s*\)")


@dataclass
class _Frame:
    col: int
    bracket: str
    # The columns and lines where its items start, in order: the head first.
    items: list[tuple[int, int]] = field(default_factory=list)
    head: str | None = None
    second: str = ""


def layout(src: str) -> str:
    out: list[str] = []
    stack: list[_Frame] = []
    in_string = False
    blank = 0
    for number, raw in enumerate(src.split("\n")):
        line = raw.rstrip()
        if not in_string:
            if not line.strip():
                blank += 1
                continue
            text = _doc_sugar(line.lstrip())
            line = " " * (_indent(stack, text) if stack else 0) + text
        if out and blank:
            out.append("")
        blank = 0
        out.append(line)
        in_string = _scan(line, number, stack, in_string)
    return "\n".join(out) + "\n"


def _doc_sugar(line: str) -> str:
    """The line with each (doc 'text') outside strings and comments written doc@'text'. It starts
    outside a string: a line that starts inside one is left as it is."""
    out, i, in_string = [], 0, False
    while i < len(line):
        c = line[i]
        if in_string:
            out.append(line[i : i + 2] if c == "\\" else c)
            i += 2 if c == "\\" else 1
            in_string = c != "'"
            continue
        if c == ";":
            out.append(line[i:])
            break
        if m := _DOC.match(line, i):
            out.append("doc@" + m.group(1))
            i = m.end()
            continue
        in_string = c == "'"
        out.append(c)
        i += 1
    return "".join(out)


def _indent(stack: list[_Frame], text: str) -> int:
    f = stack[-1]
    if f.bracket == "[" or f.head is None:
        return f.col + 1
    # A docstring reads with the body, whatever form it documents.
    if text.startswith("doc@"):
        return f.col + 2
    unnamed = f.head.endswith("_")
    base = f.head.removesuffix("_").split("|")[0]
    count = INDENT.get(base)
    if count is None:
        # A call: under its first argument, when that is on the head's line.
        if len(f.items) > 1 and f.items[1][1] == f.items[0][1]:
            return f.items[1][0]
        return f.col + 1
    # The item after the head is this line's first when the head ends its own line.
    second = f.second if len(f.items) > 1 else text[:1]
    if base in NAMED and (unnamed or (second != "" and second in OPEN)):
        count = max(0, count - 1)
    # (foreach ((i n) (j m)) …) has its bindings in one list, where (foreach i n …) has two items.
    if base == "foreach" and second == "(":
        count = 1
    before = len(f.items) - 1
    if before < count or base in NO_BODY:
        return f.col + 4
    head = re.match(r"\(([^\s()\[\]';]+)", text)
    if head is not None and head.group(1) in KEYWORDS.get(base, ()):
        return f.col + 4
    return f.col + 2


def _scan(line: str, number: int, stack: list[_Frame], in_string: bool) -> bool:
    """Follows the line's brackets, strings and comments into stack; gives whether a string is
    still open at its end."""
    i, atom = 0, False
    while i < len(line):
        c = line[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == "'":
                in_string = False
            i += 1
            continue
        if c == ";":
            break
        if c.isspace():
            atom = False
        elif c == "'" or (c == "$" and line[i + 1 : i + 2] == "'"):
            # The text of doc@'text' is part of the same item.
            if not atom:
                _item(stack, i, number, line)
            in_string, atom = True, False
            i += 2 if c == "$" else 1
            continue
        elif c in OPEN:
            # g[0] indexes g: the bracket is part of the name, not an item of its own.
            if not (c == "[" and atom):
                _item(stack, i, number, line)
            stack.append(_Frame(i, c))
            atom = False
        elif c in CLOSE:
            if stack:
                stack.pop()
            atom = True
        else:
            if not atom:
                _item(stack, i, number, line)
            atom = True
        i += 1
    return in_string


def _item(stack: list[_Frame], col: int, number: int, line: str) -> None:
    if not stack:
        return
    f = stack[-1]
    f.items.append((col, number))
    word = line[col:]
    end = next((k for k, ch in enumerate(word) if ch.isspace() or ch in OPEN + CLOSE), len(word))
    if len(f.items) == 1 and f.bracket == "(" and word[:1] not in OPEN + "'$":
        f.head = word[:end]
    elif len(f.items) == 2:
        f.second = word[:1]
