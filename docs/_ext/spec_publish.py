"""The published spec at spec.mtp-lang.org shows only the pages that the author has approved.

just spec-publish builds the whole draft first, and this extension writes down, for every label of
the spec, the page that holds it and the text that a reference to it shows, such as "Rule 4.9".
Then it builds again with MTP_SPEC_APPROVED_ONLY=1: each page not in spec_approved keeps only its
title, so every link to it still works, and a reference to a rule or a section on such a page
shows, without a link, the text that the whole draft gives it."""

import json
import os
from pathlib import Path

from docutils import nodes
from sphinx.application import Sphinx

LABELS = Path(__file__).parent.parent / "_build" / "spec-labels.json"
STUB = "\n\nThis page is not yet published.\n"


def approved_only() -> bool:
    return os.environ.get("MTP_SPEC_APPROVED_ONLY") == "1"


def _unapproved(app: Sphinx, docname: str) -> bool:
    return docname.startswith("spec/") and docname.split("/", 1)[1] not in app.config.spec_approved


def _stub(app: Sphinx, docname: str, source: list[str]) -> None:
    """An unapproved page keeps its labels and its title, up to its first heading, and nothing else."""
    if not approved_only() or not _unapproved(app, docname):
        return
    head = []
    for line in source[0].splitlines():
        head.append(line)
        if line.startswith("# "):
            break
    source[0] = "\n".join(head) + STUB


def _record(app: Sphinx, exception) -> None:
    """After a build of the whole draft, the page and the reference text of every label."""
    if exception or approved_only():
        return
    env = app.env
    out = {}
    for label, (docname, ident, sectname) in env.domaindata["std"]["labels"].items():
        if not docname.startswith("spec/"):
            continue
        number = None
        kind = None
        for figtype, idents in env.toc_fignumbers.get(docname, {}).items():
            if ident in idents:
                number, kind = ".".join(map(str, idents[ident])), figtype
        if number is None:
            sec = env.toc_secnumbers.get(docname, {}).get("#" + ident)
            if sec:
                number, kind = ".".join(map(str, sec)), "section"
        fmt = app.config.numfig_format.get(kind or "", "Section %s")
        out[label] = {
            "doc": docname,
            "number": number,
            "numref": fmt % number if number else sectname,
            "ref": sectname or (fmt % number if number else label),
        }
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    LABELS.write_text(json.dumps(out, indent=1), encoding="utf-8")


def _resolve(app: Sphinx, env, node, contnode):
    """A reference to a label that a stub no longer holds, as plain text."""
    if not approved_only() or node.get("refdomain") != "std":
        return None
    if node.get("reftype") not in ("ref", "numref") or not LABELS.is_file():
        return None
    info = json.loads(LABELS.read_text(encoding="utf-8")).get(node["reftarget"])
    if info is None or not _unapproved(app, info["doc"]):
        return None
    if node.get("refexplicit") and info["number"]:
        text = contnode.astext().replace("%s", info["number"]).replace("{number}", info["number"])
    else:
        text = info["numref"] if node["reftype"] == "numref" else info["ref"]
    return nodes.inline(text, text)


def setup(app: Sphinx):
    app.add_config_value("spec_approved", [], "env")
    app.connect("source-read", _stub)
    app.connect("build-finished", _record)
    app.connect("missing-reference", _resolve)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
