"""The sidebar of the spec groups its pages into parts, one toctree with a caption for each part.
Sphinx starts the page numbers again at 1 in each numbered toctree, but the numbers of rules,
sections and tables come from the page numbers, so one count runs across all the parts: page
numbering sees the numbered toctrees of a page as one toctree."""

from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.environment.collectors.toctree import TocTreeCollector

_assign = TocTreeCollector.assign_section_numbers


def _one_count(self, env):
    get = env.get_doctree

    def merged(docname):
        doctree = get(docname)
        numbered = [t for t in doctree.findall(addnodes.toctree) if t.get("numbered")]
        for toctree in numbered[1:]:
            numbered[0]["entries"] += toctree["entries"]
            toctree["numbered"] = 0
        return doctree

    env.get_doctree = merged
    try:
        return _assign(self, env)
    finally:
        del env.get_doctree


def setup(app: Sphinx):
    TocTreeCollector.assign_section_numbers = _one_count
    return {"parallel_read_safe": True, "parallel_write_safe": True}
