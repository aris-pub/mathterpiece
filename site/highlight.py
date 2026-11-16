"""Fill each <pre class="mtp" data-src="FILE"> of the landing page with FILE, highlighted by the
mtp lexer that the spec and the docs use. Run by just site-build, so the page shows each figure's
source as it is."""

import re
import sys
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter

SITE = Path(__file__).parent
sys.path.insert(0, str(SITE.parent / "docs" / "_ext"))
from mtp_sphinx import MtpLexer  # noqa: E402

PRE = re.compile(r'(<pre class="mtp[^"]*" data-src="([^"]+)"(?: data-mark="([^"]*)")?>)(.*?)(</pre>)', re.S)


def fill(match: re.Match) -> str:
    src = (SITE / match.group(2)).read_text(encoding="utf-8").rstrip("\n")
    code = highlight(src, MtpLexer(), HtmlFormatter(nowrap=True)).rstrip("\n")
    # The mtp lexer has no token that spans lines, so each line of the output is one source line.
    lines = code.split("\n")
    width = len(str(len(lines)))
    # data-mark="3,7" marks those lines, for a page that points at a line the reader should see.
    marked = {int(n) for n in (match.group(3) or "").split(",") if n}
    # Each source line is a block of its own, so a narrow screen can wrap it and indent the rest
    # under its start.
    numbered = "".join(
        f'<span class="line{" mark" if i in marked else ""}">'
        + f'<span class="ln" aria-hidden="true">{i:>{width}}</span>{line or " "}</span>'
        for i, line in enumerate(lines, 1)
    )
    return match.group(1) + numbered + match.group(5)


page = SITE / "index.html"
page.write_text(PRE.sub(fill, page.read_text(encoding="utf-8")), encoding="utf-8")
