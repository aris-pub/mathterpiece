"""Fill each <pre class="mtp" data-src="FILE"> of the landing page with FILE, highlighted by the
mtp lexer that the spec and the docs use. Run by just site-build, so the page shows each figure's
source as it is.

data-mark="3,7" marks those lines. data-diff="OTHER" shows FILE as one side of a diff against
OTHER, which has the same number of lines: each line that differs is marked, and the characters
that FILE has and OTHER lacks are marked again."""

import html
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from pygments import highlight, lex
from pygments.formatters import HtmlFormatter
from pygments.token import STANDARD_TYPES

SITE = Path(__file__).parent
sys.path.insert(0, str(SITE.parent / "docs" / "_ext"))
from mtp_sphinx import MtpLexer  # noqa: E402

PRE = re.compile(
    r'(<pre class="mtp[^"]*" data-src="([^"]+)"(?: data-mark="([^"]*)")?(?: data-diff="([^"]*)")?>)'
    r"(.*?)(</pre>)",
    re.S,
)


def short(token) -> str:
    while token not in STANDARD_TYPES:
        token = token.parent
    return STANDARD_TYPES[token]


def diffed(line: str, other: str) -> str:
    """One line, highlighted, with the characters that it has and other lacks in chg spans."""
    changed = [False] * len(line)
    for op, _, _, j1, j2 in SequenceMatcher(None, other, line, autojunk=False).get_opcodes():
        if op in ("insert", "replace"):
            for j in range(j1, j2):
                changed[j] = True
    chars = []
    for token, text in lex(line, MtpLexer()):
        for ch in text:
            if len(chars) < len(line):
                chars.append((short(token), ch, changed[len(chars)]))
    out, run = [], []
    for c in chars + [None]:
        if run and (c is None or (c[0], c[2]) != (run[0][0], run[0][2])):
            classes = " ".join(x for x in (run[0][0], "chg" if run[0][2] else "") if x)
            text = html.escape("".join(r[1] for r in run))
            out.append(f'<span class="{classes}">{text}</span>' if classes else text)
            run = []
        if c is not None:
            run.append(c)
    return "".join(out)


def fill(match: re.Match) -> str:
    src = (SITE / match.group(2)).read_text(encoding="utf-8").rstrip("\n")
    marked = {int(n) for n in (match.group(3) or "").split(",") if n}
    if match.group(4):
        mine = src.split("\n")
        others = (SITE / match.group(4)).read_text(encoding="utf-8").rstrip("\n").split("\n")
        lines = [diffed(a, b) for a, b in zip(mine, others)]
        marked |= {i for i, (a, b) in enumerate(zip(mine, others), 1) if a != b}
    else:
        code = highlight(src, MtpLexer(), HtmlFormatter(nowrap=True)).rstrip("\n")
        # The mtp lexer has no token that spans lines, so each line of the output is one source
        # line.
        lines = code.split("\n")
    width = len(str(len(lines)))
    # Each source line is a block of its own, so a narrow screen can wrap it and indent the rest
    # under its start.
    numbered = "".join(
        f'<span class="line{" mark" if i in marked else ""}">'
        + f'<span class="ln" aria-hidden="true">{i:>{width}}</span>{line or " "}</span>'
        for i, line in enumerate(lines, 1)
    )
    return match.group(1) + numbered + match.group(6)


page = SITE / "index.html"
page.write_text(PRE.sub(fill, page.read_text(encoding="utf-8")), encoding="utf-8")
