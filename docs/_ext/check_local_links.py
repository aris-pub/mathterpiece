"""Checks that every relative href and src in the built spec site names a file that exists.
Sphinx's linkcheck builder does not see links written in raw HTML, such as the frames of the
example pages."""

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

LINK = re.compile(r"""\b(?:href|src)=["']([^"']+)["']""")


def broken(site: Path) -> list[str]:
    found = []
    for page in sorted(site.rglob("*.html")):
        if page.relative_to(site).parts[0] == "_static":
            continue  # templates of the theme, not pages
        for target in LINK.findall(page.read_text(encoding="utf-8", errors="replace")):
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or target.startswith(("#", "mailto:", "data:")):
                continue
            if not parts.path:
                continue
            path = (page.parent / unquote(parts.path)).resolve()
            if not path.exists():
                found.append(f"{page.relative_to(site)}: {target}")
    return found


if __name__ == "__main__":
    bad = broken(Path(sys.argv[1]))
    print("\n".join(bad) if bad else "every local link resolves")
    sys.exit(1 if bad else 0)
