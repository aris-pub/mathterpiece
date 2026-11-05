"""Building an .mtp (docs/data-model.md, "The mtp command"): parsing, compiling, writing the
.mtpc, and writing a minimal page that shows the live figure. mtp build dial.mtp writes the folder
build_dial/: the .mtpc, the runtime, and index.html, which holds both, since a browser loads no
module and fetches no file for a page opened as a file."""

import html
import json
import shutil
import subprocess
from pathlib import Path

from mathterpiece.compiler import compile_model
from mathterpiece.mtpc import write
from mathterpiece.parse import parse

WEB = Path(__file__).parent.parent / "web"
CONTROLS = ("slider", "toggle", "button", "play")


class BuildError(Exception):
    pass


def compiled(src: str, path: Path | None = None) -> str:
    """The .mtpc of a source read from path: parsing, compiling and writing. A parse or compile
    error is raised."""
    return write(compile_model(parse(src), path))


def runtime() -> str:
    """The runtime as one ES module, built with pnpm when its source is newer than its build."""
    built = WEB / "dist" / "mathterpiece.js"
    sources = [p for p in (WEB / "src").rglob("*") if p.is_file()]
    if not sources:
        raise BuildError(f"the runtime's source is not in {WEB / 'src'}")
    if not built.exists() or built.stat().st_mtime < max(p.stat().st_mtime for p in sources):
        if shutil.which("pnpm") is None:
            raise BuildError(
                "building the runtime needs Node and pnpm: install them, then try again"
            )
        done = subprocess.run(["pnpm", "build"], cwd=WEB, capture_output=True, text=True)
        if done.returncode != 0:
            raise BuildError(f"building the runtime failed:\n{done.stdout}{done.stderr}")
    return built.read_text(encoding="utf-8")


def about(src: str) -> list[str]:
    """The comment the source starts with, as paragraphs: its lines run together, and an empty
    comment line starts a new paragraph."""
    paragraphs: list[list[str]] = [[]]
    for line in src.split("\n"):
        if not line.startswith(";"):
            break
        text = line.lstrip(";").strip()
        if text:
            paragraphs[-1].append(text)
        elif paragraphs[-1]:
            paragraphs.append([])
    return [" ".join(p) for p in paragraphs if p]


def page(name: str, mtpc: str, js: str, text: list[str] | None = None, extra: str = "") -> str:
    """A minimal page: the source's opening comment, then every canvas, control and readout, in the
    order the source declares them."""
    doc = json.loads(mtpc)
    parts = []
    for o in doc["objects"]:
        kind, n = o["kind"], html.escape(o.get("name") or "")
        if kind == "canvas":
            parts.append(f'<mtp-canvas model="model" name="{n}"></mtp-canvas>')
        elif kind in CONTROLS:
            parts.append(f'<div><mtp-{kind} model="model" name="{n}"></mtp-{kind}></div>')
        elif kind == "readout":
            parts.append(f'<p><mtp-readout model="model" name="{n}"></mtp-readout></p>')
    # Inside a script, only </ could end it early.
    data = mtpc.strip().replace("</", "<\\/")
    code = js.replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 680px; }}
  mtp-canvas {{ display: block; width: min(90vw, 640px); margin: 1rem 0; }}
  mtp-canvas svg {{ width: 100%; height: auto; }}
  .about {{ color: #555; font-size: 16px; line-height: 1.55; margin: 0 0 0.6em; }}
</style>
</head>
<body>
<h1>{html.escape(name)}</h1>
{chr(10).join(f'<p class="about">{html.escape(p)}</p>' for p in text or [])}
<mtp-model id="model" src="#model-data"></mtp-model>
{chr(10).join(parts)}
<script type="application/json" id="model-data">{data}</script>
<script type="module">
{code}
</script>
{extra}
</body>
</html>
"""


def build(path: Path) -> Path:
    """Builds the .mtp at path into build_<name>/ next to it, and gives that folder. Nothing is
    written when the source has an error."""
    src = path.read_text(encoding="utf-8")
    mtpc = compiled(src, path)
    js = runtime()
    out = path.parent / f"build_{path.stem}"
    out.mkdir(exist_ok=True)
    (out / f"{path.stem}.mtpc").write_text(mtpc, encoding="utf-8")
    (out / "mathterpiece.js").write_text(js, encoding="utf-8")
    (out / "index.html").write_text(page(path.stem, mtpc, js, about(src)), encoding="utf-8")
    return out
