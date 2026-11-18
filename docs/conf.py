"""Sphinx configuration of the spec, served at spec.mtp-lang.org. just spec serves it while it is
being written. The docs are a second project in guide/, with a configuration of their own."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "_ext"))

project = "mathterpiece"
author = "Leo Torres"
copyright = "2026, Leo Torres"

extensions = ["myst_parser", "sphinxcontrib.mermaid", "mtp_sphinx", "spec_publish"]
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
html_theme = "pydata_sphinx_theme"
html_title = "mathterpiece"
html_static_path = ["_static"]
# The Aris fonts, as on mtp-lang.org.
FONTS = (
    "https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500"
    "&family=Source+Code+Pro:wght@400;500&family=Source+Sans+3:wght@300;400;600&display=swap"
)
html_css_files = [FONTS, "mtp.css"]
html_theme_options = {
    "logo": {
        "image_light": "_static/mtp-logo-light.svg",
        "image_dark": "_static/mtp-logo-dark.svg",
        "text": "spec",
    },
}
# Netlify reads _redirects, which sends the root of spec.mtp-lang.org to the spec.
html_extra_path = ["_root"]

# The guides written before the spec are read only through the spec's parts that include them,
# until the spec takes their place.
exclude_patterns = [
    "_build",
    "guide",
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

# The pages of the spec that the author has approved. just spec-publish publishes these in full, the
# glossary and the index of rules with them, and every other page as a stub with its title only
# (docs/_ext/spec_publish.py).
spec_approved = ["index", "overview", "compiler-runtime", "lexical", "grammar", "glossary", "rules"]
