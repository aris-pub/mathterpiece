"""Writes docs/spec/diagrams/builtin-types.svg, the figure of the built-in types as sets on the
spec page docs/spec/types.md.

Each box is a set, and a box inside another box is a subset. The layout below gives each box a
title, optional lines of text and children, and computes every size and position from the text
widths, the gaps and the paddings. Two kinds of box overlap other boxes instead of nesting:

- a band crosses the bottom edges of its targets and has its label below them (unit, instant),
- a frame encloses its targets and has its label below them (writer).

Run: uv run --no-project python scripts/diagrams/builtin_types.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parents[2] / "docs" / "spec" / "diagrams" / "builtin-types.svg"

CODE, SUB, NAME, LABEL = "mtp-d-code", "mtp-d-sub", "mtp-d-name", "mtp-d-label"

# The widths are estimates for the fonts of the spec site (Source Code Pro at 14px, Source Sans 3
# at 12.5px and 15px semibold). The code font is monospace, so its estimate is exact.
CHAR_W = {CODE: 8.4, SUB: 6.2, LABEL: 6.2, NAME: 8.6}
LINE_H = {CODE: 18, SUB: 16, LABEL: 16, NAME: 18}
BASELINE = {CODE: 14, SUB: 12, LABEL: 12, NAME: 14}

MARGIN = 10
PAD = 12
HEADER_TOP = 6
HEADER_GAP = 8
LEAF_PAD = (12, 12)
TINY_PAD = (8, 3)
OPACITY_STEP = 0.021

BAND_INSET = 10
BAND_DEPTH = 14
BAND_LABEL_GAP = 6
BAND_PAD = 10
FRAME_MARGIN = 6
FRAME_LABEL_H = 24

PART_STYLE = "fill: currentColor; fill-opacity: {:.3f}; stroke: currentColor; stroke-opacity: 0.3"
OVERLAP_STYLE = "fill: none; stroke: currentColor; stroke-opacity: 0.6; stroke-width: 1.5"


def text_width(text: str, cls: str) -> float:
    return sum(10.0 if ch == "…" else CHAR_W[cls] for ch in text)


def lines_size(lines: list[tuple[str, str]]) -> tuple[float, float]:
    if not lines:
        return 0.0, 0.0
    return max(text_width(t, c) for c, t in lines), sum(LINE_H[c] for c, _ in lines)


@dataclass(eq=False)
class Code:
    """A line in code font below a box title, such as rand-seed below int."""

    text: str


@dataclass(eq=False)
class Node:
    lx: float = 0.0
    ly: float = 0.0
    w: float = 0.0
    h: float = 0.0
    x: float = 0.0
    y: float = 0.0
    parent: Box | None = None


@dataclass(eq=False)
class Text(Node):
    """A line of text with no box around it, such as the … after list[T2]."""

    text: str = ""
    cls: str = SUB


@dataclass(eq=False)
class Box(Node):
    """A set. A box with no title draws nothing and only lays out its children."""

    title: str | None = None
    children: list[Node] = field(default_factory=list)
    sub: tuple[str | Code, ...] = ()
    title_cls: str = CODE
    direction: str = "column"
    cols: int = 0
    gap: float = 10
    tiny: bool = False
    align: str = "middle"
    uniform: bool = False
    stretch: bool | None = None
    align_with: str | None = None
    overlaps: list[Overlap] = field(default_factory=list)
    min_w: float = 0.0
    extra_bottom: float = 0.0

    def lines(self) -> list[tuple[str, str]]:
        out = [(self.title_cls, self.title)] if self.title is not None else []
        for s in self.sub:
            out.append((CODE, s.text) if isinstance(s, Code) else (SUB, s))
        return out


@dataclass(eq=False)
class Overlap:
    title: str
    targets: tuple[str, ...]
    sub: tuple[str, ...] = ()
    lx: float = 0.0
    ly: float = 0.0
    w: float = 0.0
    h: float = 0.0
    x: float = 0.0
    y: float = 0.0

    def lines(self) -> list[tuple[str, str]]:
        return [(CODE, self.title)] + [(SUB, s) for s in self.sub]


class Band(Overlap):
    pass


class Frame(Overlap):
    pass


def box(title, *children, **kw) -> Box:
    return Box(title=title, children=list(children), **kw)


def group(*children, **kw) -> Box:
    return Box(title=None, children=list(children), **kw)


def tiny(title: str) -> Box:
    return Box(title=title, tiny=True)


def dots() -> Text:
    return Text(text="…")


def subtree(node: Node):
    yield node
    if isinstance(node, Box):
        for c in node.children:
            yield from subtree(c)


def find(root: Box, title: str) -> Box:
    for n in subtree(root):
        if isinstance(n, Box) and n.title == title:
            return n
    raise KeyError(title)


def is_inside(inner: Node, outer: Node) -> bool:
    n = inner.parent
    while n is not None:
        if n is outer:
            return True
        n = n.parent
    return False


def leaf_targets(container: Box, ov: Overlap) -> tuple[list[Box], list[Box]]:
    targets = [find(container, t) for t in ov.targets]
    leaves = [t for t in targets if not any(is_inside(o, t) for o in targets if o is not t)]
    return targets, leaves


def prepare(node: Node, parent: Box | None = None) -> None:
    node.parent = parent
    if not isinstance(node, Box):
        return
    for c in node.children:
        prepare(c, node)
    for ov in node.overlaps:
        if not isinstance(ov, Band):
            continue
        # A band enters the bottom of each innermost target, so those targets get room below their
        # text, and together they must be wide enough for the band's label.
        _, leaves = leaf_targets(node, ov)
        label_w, _ = lines_size(ov.lines())
        need = label_w + 2 * BAND_PAD + 2 * BAND_INSET
        gaps = sum(leaf.parent.gap for leaf in leaves[1:])
        for leaf in leaves:
            leaf.extra_bottom = BAND_DEPTH
            leaf.min_w = max(leaf.min_w, (need - gaps) / len(leaves))


def rel_rect(node: Node, container: Box) -> tuple[float, float, float, float]:
    x, y, n = 0.0, 0.0, node
    while n is not container:
        x, y, n = x + n.lx, y + n.ly, n.parent
    return x, y, x + node.w, y + node.h


def measure(node: Node) -> None:
    if isinstance(node, Text):
        node.w, node.h = text_width(node.text, node.cls), LINE_H[node.cls]
        return
    assert isinstance(node, Box)
    tw, th = lines_size(node.lines())
    if not node.children:
        px, py = TINY_PAD if node.tiny else LEAF_PAD
        node.w = max(tw, node.min_w) + 2 * px
        node.h = th + 2 * py + node.extra_bottom
        return
    for c in node.children:
        measure(c)
    arrange(node)
    rects = [(c.lx, c.ly, c.lx + c.w, c.ly + c.h) for c in node.children]
    for ov in node.overlaps:
        place_overlap(node, ov)
        rects.append((ov.lx, ov.ly, ov.lx + ov.w, ov.ly + ov.h))
    x0, y0 = min(r[0] for r in rects), min(r[1] for r in rects)
    x1, y1 = max(r[2] for r in rects), max(r[3] for r in rects)
    if node.title is None:
        pad, header = 0.0, 0.0
    else:
        pad, header = PAD, HEADER_TOP + th + HEADER_GAP
    for item in [*node.children, *node.overlaps]:
        item.lx += pad - x0
        item.ly += header - y0
    node.w = max(x1 - x0, tw) + 2 * pad
    node.h = header + (y1 - y0) + pad


def arrange(node: Box) -> None:
    kids = node.children
    boxes = [k for k in kids if isinstance(k, Box) and k.title is not None]
    if node.direction == "grid":
        cw, ch = max(k.w for k in kids), max(k.h for k in kids)
        for k in boxes:
            k.w, k.h = cw, ch
        for i, k in enumerate(kids):
            k.lx = (i % node.cols) * (cw + node.gap)
            k.ly = (i // node.cols) * (ch + node.gap)
        return
    row = node.direction == "row"
    if node.uniform:
        size = max(k.w if row else k.h for k in boxes)
        for k in boxes:
            if row:
                k.w = size
            else:
                k.h = size
    cross = max(k.h if row else k.w for k in kids)
    stretch = node.stretch if node.stretch is not None else not row
    pos = 0.0
    for k in kids:
        if stretch and k in boxes:
            if row:
                k.h = cross
            else:
                k.w = cross
        k_cross = k.h if row else k.w
        offset = (cross - k_cross) / 2 if isinstance(k, Text) else 0.0
        if row:
            k.lx, k.ly = pos, offset
            pos += k.w + node.gap
        else:
            k.lx, k.ly = offset, pos
            pos += k.h + node.gap
    # A box in a row can line up with a box inside one of its siblings, so that a frame around both
    # of them stays clear of the titles of the boxes that hold the first one.
    for k in kids:
        if isinstance(k, Box) and k.align_with is not None and row:
            target = next(t for c in kids if c is not k for t in subtree(c)
                          if isinstance(t, Box) and t.title == k.align_with)
            k.ly = rel_rect(target, node)[1]


def place_overlap(container: Box, ov: Overlap) -> None:
    targets, leaves = leaf_targets(container, ov)
    _, th = lines_size(ov.lines())
    if isinstance(ov, Band):
        leaf_rects = [rel_rect(t, container) for t in leaves]
        x0 = min(r[0] for r in leaf_rects) + BAND_INSET
        x1 = max(r[2] for r in leaf_rects) - BAND_INSET
        y0 = min(r[3] for r in leaf_rects) - BAND_DEPTH
        low = max(rel_rect(t, container)[3] for t in targets)
        y1 = low + BAND_LABEL_GAP + th + BAND_PAD
    else:
        rects = [rel_rect(t, container) for t in targets]
        x0 = min(r[0] for r in rects) - FRAME_MARGIN
        x1 = max(r[2] for r in rects) + FRAME_MARGIN
        y0 = min(r[1] for r in rects) - FRAME_MARGIN
        y1 = max(r[3] for r in rects) + FRAME_MARGIN + FRAME_LABEL_H
    ov.lx, ov.ly, ov.w, ov.h = x0, y0, x1 - x0, y1 - y0


def place(node: Node, x: float, y: float) -> None:
    node.x, node.y = x, y
    if isinstance(node, Box):
        for c in node.children:
            place(c, x + c.lx, y + c.ly)
        for ov in node.overlaps:
            ov.x, ov.y = x + ov.lx, y + ov.ly


def num(v: float) -> str:
    return f"{round(v, 1):g}"


def rect(x, y, w, h, style) -> str:
    return (
        f'<rect class="mtp-d-part" x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" '
        f'rx="6" style="{style}"/>'
    )


def text(cls, x, y, s, anchor) -> str:
    return (
        f'<text class="{cls}" x="{num(x)}" y="{num(y)}" text-anchor="{anchor}">{escape(s)}</text>'
    )


def draw_lines(out, lines, x, top, anchor) -> None:
    y = top
    for cls, s in lines:
        out.append(text(cls, x, y + BASELINE[cls], s, anchor))
        y += LINE_H[cls]


def draw(node: Node, depth: int, out: list[str], overlaps: list[Overlap]) -> None:
    if isinstance(node, Text):
        out.append(text(node.cls, node.x + node.w / 2, node.y + BASELINE[node.cls], node.text,
                        "middle"))
        return
    assert isinstance(node, Box)
    overlaps.extend(node.overlaps)
    if node.title is None:
        for c in node.children:
            draw(c, depth, out, overlaps)
        return
    out.append(rect(node.x, node.y, node.w, node.h, PART_STYLE.format(OPACITY_STEP * depth)))
    lines = node.lines()
    if node.children:
        draw_lines(out, lines, node.x + PAD, node.y + HEADER_TOP, "start")
    else:
        px, _ = TINY_PAD if node.tiny else LEAF_PAD
        _, th = lines_size(lines)
        top = node.y + (node.h - node.extra_bottom - th) / 2
        if node.align == "start":
            draw_lines(out, lines, node.x + px, top, "start")
        else:
            draw_lines(out, lines, node.x + node.w / 2, top, "middle")
    for c in node.children:
        draw(c, depth + 1, out, overlaps)


def draw_overlap(ov: Overlap, container_targets: list[Box], out: list[str]) -> None:
    out.append(rect(ov.x, ov.y, ov.w, ov.h, OVERLAP_STYLE))
    lines = ov.lines()
    if isinstance(ov, Band):
        low = max(t.y + t.h for t in container_targets)
        draw_lines(out, lines, ov.x + ov.w / 2, low + BAND_LABEL_GAP, "middle")
    else:
        draw_lines(out, lines, ov.x + ov.w - 8, ov.y + ov.h - FRAME_LABEL_H + 1, "end")


def motif(name: str) -> Box:
    return box(f"motif {name}", tiny(f"variant {name}1"), tiny(f"variant {name}2"), dots(),
               gap=6)


def animation(name: str) -> Box:
    return box(f"animation {name}", tiny(f"variant {name}1"), tiny(f"variant {name}2"), dots(),
               gap=6)


SHAPE_KINDS = ["circle", "rect", "ellipse", "line", "triangle", "polyline", "polygon", "bezier",
               "arc", "ring", "text", "group"]

PRIMITIVES = box(
    "primitives",
    box("complex",
        box("real",
            box("ratio",
                box("int", sub=("same set:", Code("rand-seed")), align="start")),
            overlaps=[Band("unit", ("int", "ratio"), ("the reals from 0 to 1",))])),
    group(
        group(*(box(t) for t in ["bool", "string", "color", "point", "none"]), direction="row",
              uniform=True),
        group(box("list[T1]"), box("list[T2]"), dots(), direction="row"),
        group(box("angle", sub=("(mod real 0 360)",)), box("(mod int 0 12)"), dots(),
              direction="row", stretch=True),
        gap=14),
    title_cls=NAME, direction="row", gap=16)

OBJECTS = box(
    "objects",
    group(
        box("shape",
            group(*(tiny(k) for k in SHAPE_KINDS), direction="grid", cols=4, gap=6),
            group(motif("M1"), motif("M2"), dots(), direction="row"),
            gap=12),
        box("movement",
            group(box("score"), direction="row",
                  overlaps=[Band("instant", ("score",),
                                 ("the movements that", "take no time"))]),
            group(animation("A1"), animation("A2"), dots(), direction="row"),
            gap=12),
        direction="row", gap=16),
    group(
        box("page-object",
            group(
                box("component",
                    box("view", sub=("canvas", "readout", "display"), align="start"),
                    box("control",
                        box("jumper", sub=("slider, dial, toggle, …",), align="start"),
                        box("mover", sub=("button, play, stepper",), align="start")),
                    direction="row", gap=18),
                box("listener", sub=("on-drag", "on-click", "…"), align="start",
                    align_with="control"),
                direction="row",
                overlaps=[Frame("writer", ("control", "listener"))])),
        group(
            group(box("func", tiny("ease"), tiny("curve"), tiny("colormap"), gap=6),
                  box("record", box("font")), direction="row"),
            group(box("scene"), box("formula"), box("term"), direction="row", gap=8)),
        direction="row", gap=16),
    title_cls=NAME, gap=16)

VALUES = box("values", PRIMITIVES, OBJECTS, title_cls=LABEL, gap=14)

DESCRIPTION = (
    "The built-in types as sets. Values are primitives or objects. Among the primitives, int is "
    "inside ratio, inside real, inside complex. rand-seed is the same set as int. unit, the reals "
    "from 0 to 1, is inside real and overlaps int and ratio. bool, string, color, point and none "
    "are separate, and so is each list type, such as list[T1] and list[T2], and each modular "
    "type, such as angle, which is (mod real 0 360), and (mod int 0 12). Among the objects, shape "
    "holds a box for each shape type (circle, rect, ellipse, line, triangle, polyline, polygon, "
    "bezier, arc, ring, text and group) and every motif type, and each motif holds its variants: "
    "motif M1 holds variants M11 and M12, and motif M2 holds variants M21 and M22. movement "
    "holds score and every animation type, and each animation holds its variants: "
    "animation A1 holds variants A11 and A12, and animation A2 holds variants A21 and A22. instant is inside movement and overlaps score. "
    "ease, curve and colormap are "
    "inside func, font is inside record, and scene, formula and term are separate. page-object "
    "holds component, which holds view and control, and listener. control holds jumper and "
    "mover. writer holds control and listener."
)


def build(root: Box) -> str:
    prepare(root)
    measure(root)
    place(root, MARGIN, MARGIN)
    out: list[str] = []
    overlaps: list[Overlap] = []
    draw(root, 0, out, overlaps)
    for ov in overlaps:
        container = next(n for n in subtree(root) if isinstance(n, Box) and ov in n.overlaps)
        targets, _ = leaf_targets(container, ov)
        draw_overlap(ov, targets, out)
    width, height = root.w + 2 * MARGIN, root.h + 2 * MARGIN
    head = (
        f'<svg viewBox="0 0 {num(width)} {num(height)}" role="img" '
        f'aria-labelledby="mtp-bt-title"><title id="mtp-bt-title">{escape(DESCRIPTION)}</title>'
    )
    return head + "".join(out) + "</svg>\n"


def main() -> None:
    OUT.write_text(build(VALUES))
    print(OUT)


if __name__ == "__main__":
    main()
