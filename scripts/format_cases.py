"""Writes web/test/data/format-cases.json: each value and format spec in it, with the text the
compiler gives (mathterpiece.compiler._show_value), which the web runtime must give too.

Run: uv run python scripts/format_cases.py
"""

import json
from pathlib import Path

from mathterpiece.compiler import _show_value
from mathterpiece.types import INT, REAL

PATH = Path(__file__).parent.parent / "web" / "test" / "data" / "format-cases.json"


def main() -> None:
    cases = json.loads(PATH.read_text())
    out = []
    for x, spec, kind, _ in cases:
        if spec == "repr":
            text = repr(float(x))
        else:
            text = _show_value(INT if kind == "int" else REAL, x, spec)
        out.append([x, spec, kind, text])
    PATH.write_text(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
