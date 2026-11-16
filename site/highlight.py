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

PRE = re.compile(r'(<pre class="mtp" data-src="([^"]+)">)(.*?)(</pre>)', re.S)


def fill(match: re.Match) -> str:
    src = (SITE / match.group(2)).read_text(encoding="utf-8").rstrip("\n")
    code = highlight(src, MtpLexer(), HtmlFormatter(nowrap=True)).rstrip("\n")
    return match.group(1) + code + match.group(4)


page = SITE / "index.html"
page.write_text(PRE.sub(fill, page.read_text(encoding="utf-8")), encoding="utf-8")
