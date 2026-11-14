"""Sphinx configuration of the mtp site: the landing page, the specification and, later, the
documentation. just spec serves it while it is being written."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "_ext"))

project = "mathterpiece"
author = "Leo Torres"
copyright = "2026, Leo Torres"

extensions = ["myst_parser", "sphinxcontrib.mermaid", "mtp_sphinx"]
myst_fence_as_directive = ["mermaid"]
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

# Sections, rules, figures, tables and listings are numbered across the whole spec.
numfig = True
numfig_secnum_depth = 1
numfig_format = {
    "rule": "Rule %s",
    "figure": "Figure %s",
    "table": "Table %s",
    "code-block": "Listing %s",
}

highlight_language = "mtp"
html_theme = "furo"
html_title = "mathterpiece"
html_static_path = ["_static"]
html_css_files = ["mtp.css"]

# The guides written before the spec are read only through the spec's parts that include them,
# until the spec takes their place.
exclude_patterns = [
    "_build",
    "canvas-lifecycle.md",
    "concurrency-model.md",
    "data-model.md",
    "figure-guidelines.md",
    "mtpc.md",
    "page-interface.md",
    "reference.md",
    "syntax.md",
    "type-system.md",
]
