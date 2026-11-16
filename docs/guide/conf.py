"""Sphinx configuration of the docs, served at docs.mtp-lang.org: the guides for the people who
make figures with mtp and for the authors who place them on a page. just docs serves it while it
is being written. It shares the extension, the theme and the styles of the spec in docs/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "_ext"))

project = "mathterpiece"
author = "Leo Torres"
copyright = "2026, Leo Torres"

extensions = ["myst_parser", "sphinx.ext.intersphinx", "mtp_sphinx"]
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

# A guide links to a rule of the spec by its label, as {ref}`spec:name-lookup`.
intersphinx_mapping = {"spec": ("https://spec.mtp-lang.org/", None)}

highlight_language = "mtp"
html_theme = "pydata_sphinx_theme"
html_title = "mathterpiece docs"
html_static_path = ["../_static"]
html_css_files = ["https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500&family=Source+Code+Pro:wght@400;500&family=Source+Sans+3:wght@300;400;600&display=swap", "mtp.css"]
html_theme_options = {
    "logo": {
        "image_light": "_static/mtp-logo-light.svg",
        "image_dark": "_static/mtp-logo-dark.svg",
        "text": "docs",
    },
}
exclude_patterns = ["_build", "conf.py"]
