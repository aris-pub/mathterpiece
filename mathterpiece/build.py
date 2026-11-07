"""Building an .mtp (docs/data-model.md, "The mtp command"): parsing, compiling, writing the
.mtpc, and writing the inventory page, which shows every component live with the HTML that places
it. mtp build dial.mtp writes the folder build_dial/: the .mtpc, the runtime, and index.html, which
holds the compiled model, the runtime and the inventory's script, since a browser loads no module
and fetches no file for a page opened as a file."""

import html
import shutil
import subprocess
from pathlib import Path

from mathterpiece.compiler import compile_model
from mathterpiece.mtpc import write
from mathterpiece.parse import parse

WEB = Path(__file__).parent.parent / "web"


class BuildError(Exception):
    pass


def compiled(src: str, path: Path | None = None) -> str:
    """The .mtpc of a source read from path: parsing, compiling and writing. A parse or compile
    error is raised."""
    return write(compile_model(parse(src), path))


def _bundle(file: str) -> str:
    """One of the scripts in web/dist, built with pnpm when the source is newer than the build."""
    built = [WEB / "dist" / f for f in ("mathterpiece.js", "inventory.js")]
    sources = [p for p in (WEB / "src").rglob("*") if p.is_file()]
    if not sources:
        raise BuildError(f"the runtime's source is not in {WEB / 'src'}")
    newest = max(p.stat().st_mtime for p in sources)
    if any(not b.exists() or b.stat().st_mtime < newest for b in built):
        if shutil.which("pnpm") is None:
            raise BuildError(
                "building the runtime needs Node and pnpm: install them, then try again"
            )
        done = subprocess.run(["pnpm", "build"], cwd=WEB, capture_output=True, text=True)
        if done.returncode != 0:
            raise BuildError(f"building the runtime failed:\n{done.stdout}{done.stderr}")
    return (WEB / "dist" / file).read_text(encoding="utf-8")


def runtime() -> str:
    """The runtime as one ES module."""
    return _bundle("mathterpiece.js")


def inventory_script() -> str:
    """The script of the inventory page, as one ES module: it fills the page's inventory."""
    return _bundle("inventory.js")


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


# BRAIID, the design system of RSM documents, which draws the controls (web/src/controls-style.ts).
BRAIID = "https://cdn.jsdelivr.net/gh/aris-pub/rsm@main/braiid/braiid.css"


def page(
    name: str, mtpc: str, js: str, inv: str, text: list[str] | None = None, extra: str = ""
) -> str:
    """The inventory page (mtp-4he1): the source's opening comment, then what an author needs to
    put the world model on a page, every component live with its name and the HTML that places it.
    The inventory script builds all but the comment, from the compiled model's block."""
    model = html.escape(name)
    # Inside a script, only </ could end it early.
    data = mtpc.strip().replace("</", "<\\/")
    code, inv_code = js.replace("</", "<\\/"), inv.replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{model}</title>
<link rel="stylesheet" href="{BRAIID}">
<style>
  body {{ font: 16px/1.55 system-ui, sans-serif; margin: 2rem auto; max-width: 880px;
         padding: 0 1.25rem; }}
  .about {{ color: #555; margin: 0 0 0.6em; }}
</style>
</head>
<body>
<h1>{model}</h1>
{chr(10).join(f'<p class="about">{html.escape(p)}</p>' for p in text or [])}
<mtp-model id="{model}" src="#{model}-data"></mtp-model>
<div data-mtp-inventory="{model}" data-file="{model}.mtpc"></div>
<script type="application/json" id="{model}-data">{data}</script>
<script type="module">
{code}
</script>
<script type="module">
{inv_code}
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
    inv = inventory_script()
    out = path.parent / f"build_{path.stem}"
    out.mkdir(exist_ok=True)
    (out / f"{path.stem}.mtpc").write_text(mtpc, encoding="utf-8")
    (out / "mathterpiece.js").write_text(js, encoding="utf-8")
    (out / "index.html").write_text(page(path.stem, mtpc, js, inv, about(src)), encoding="utf-8")
    return out
