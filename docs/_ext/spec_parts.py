"""The sidebar of the spec groups its pages into parts, one toctree with a caption for each part.
Sphinx starts the page numbers again at 1 in each numbered toctree, but the numbers of rules,
sections and tables come from the page numbers, so one count runs across all the parts: page
numbering sees the numbered toctrees of a page as one toctree. The count starts at 0, so the
first page, mtp in one page, is page 0 and Overview is page 1."""

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
        changed = _assign(self, env)
    finally:
        del env.get_doctree
    for numbers in env.toc_secnumbers.values():
        for anchor, number in numbers.items():
            if number:
                numbers[anchor] = (number[0] - 1, *number[1:])
    for toc in [*env.tocs.values(), *env.titles.values()]:
        for node in toc.findall(lambda n: hasattr(n, "get") and n.get("secnumber")):
            number = node["secnumber"]
            node["secnumber"] = (number[0] - 1, *number[1:])
    return changed


def setup(app: Sphinx):
    TocTreeCollector.assign_section_numbers = _one_count
    return {"parallel_read_safe": True, "parallel_write_safe": True}
