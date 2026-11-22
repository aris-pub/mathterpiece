"""The Sphinx extension of the mtp site.

- The lexer `mtp` highlights code blocks written ```mtp.
- The directive `rule` states one rule of the spec. Rules are numbered by page, as 4.2 for the
  second rule of page 4, and cited by label with {numref}`label`, so a citation keeps working when
  rules are added or moved.
- The directive `mtp-example` compiles its source while the site is built and shows it highlighted,
  then live. A source that does not compile fails the build, so an example never goes stale.
- The directive `mtp-grammar` shows one section of the grammar, docs/spec/mtp.lark, as a list of
  productions in which each name links to its definition. tests/test_grammar.py checks the same
  file against the parser.
- The directive `diagram` shows one SVG file as a numbered figure with a caption and a label, so
  that {numref}`label` cites it, and a link to the label opens the page at the figure.
- A link to a term of the glossary shows the term and its definition in a box as soon as the mouse
  is over it, or the link has the keyboard focus (_static/mtp-terms.js). The page carries them in
  the link's title, which the script removes so that the browser shows no tooltip of its own.
"""

import html
import json
import re
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import directives
from pygments.lexer import RegexLexer, bygroups
from pygments.token import (
    STANDARD_TYPES,
    Comment,
    Error,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
)
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.domains.std import ProductionList
from sphinx.util.docutils import SphinxDirective

from mathterpiece import builtins, compiler, types
from mathterpiece.build import BRAIID, BuildError, compiled, runtime

# The lexer takes its words from the compiler, so it stays in step with the language.
DECLARING = {
    *types.PRIMS,
    *types.SHAPES,
    *compiler.LAYOUTS,
    *compiler.COMPONENTS,
    "list",
    "func",
    "motif",
    "variant",
    "type",
    "interface",
    "namespace",
    "record",
    "movement",
    "palette",
    "parametric",
    "formula",
    "term",
    "colormap",
    "choreo",
    "import",
    "rand-seed",
}
SPECIAL = {
    *compiler.SPECIAL,
    *(compiler.RESERVED - {"true", "false", "none", "self"}),
    "foreach",
    "exists-when",
    "defaults",
    "like",
    "wait",
    "loop",
}
BUILTIN = {
    *builtins.BUILTINS,
    *builtins.SPECIAL_BUILTINS,
    *builtins.PRIMITIVES,
    *compiler.COLLECTION,
}
CONSTANT = {*builtins.CONSTANTS, "true", "false", "none", "self"}
# A name part as docs/spec/lexical.md defines it (rule name-characters), and the _ that may end
# the head of a form (rule name-underscore).
NAME = r"[A-Za-z][A-Za-z0-9-]*\??_?"
OPERATOR = r"!=|<=|>=|[-+*/^<>=]"
UREAL = r"([0-9]+\.?[0-9]*|\.[0-9]+)([eE][-+]?[0-9]+)?"


def _word(lexer, match):
    word = match.group(0).removesuffix("_")
    if word in CONSTANT:
        kind = Keyword.Constant
    elif word in DECLARING:
        kind = Keyword.Declaration
    elif word in SPECIAL:
        kind = Keyword
    elif word in BUILTIN:
        kind = Name.Builtin
    elif word in {"+", "-", "*", "/", "^", "=", "!=", "<", "<=", ">", ">=", "mod"}:
        kind = Operator
    else:
        kind = Name.Variable
    yield match.start(), kind, match.group(0)


class MtpLexer(RegexLexer):
    name = "mtp"
    aliases = ["mtp"]
    filenames = ["*.mtp"]

    tokens = {
        "root": [
            (r"\s+", Whitespace),
            (r";.*$", Comment.Single),
            (r"f'(\\.|[^'\\])*'", String.Interpol),
            (r"@'(\\.|[^'\\])*'", String.Other),
            (r"#'(\\.|[^'\\])*'", String.Other),
            (r"\$'(\\.|[^'\\])*'", String),
            (r"'(\\.|[^'\\])*'", String),
            (r"(doc|free)@", Keyword),
            (r"[-+]?[0-9]+/[0-9]+", Number),
            (rf"[-+]?{UREAL}([-+]{UREAL}i|i)?", Number),
            (r"(\.)(" + NAME + ")", bygroups(Punctuation, Name.Attribute)),
            (r"[()\[\]|]", Punctuation),
            (NAME, _word),
            (OPERATOR, Operator),
            (r".", Text),
        ]
    }


class rule_node(nodes.General, nodes.Element):
    pass


def _rule_title(node):
    return node.get("label", "")


def visit_rule(self, node):
    self.body.append(self.starttag(node, "div", CLASS="mtp-rule"))
    self.body.append('<p class="mtp-rule-head">')
    self.add_fignumber(node)
    self.body.append(f'<span class="mtp-rule-label">{html.escape(node.get("label", ""))}</span>')
    self.body.append("</p>")


def depart_rule(self, node):
    self.body.append("</div>\n")


class Rule(SphinxDirective):
    """```{rule} label
    The text of the rule.
    ```"""

    required_arguments = 1
    has_content = True

    def run(self):
        label = self.arguments[0]
        node = rule_node(label=label)
        node["names"].append(label)
        self.state.document.note_explicit_target(node)
        self.state.nested_parse(self.content, self.content_offset, node)
        first = node.next_node(nodes.paragraph)
        text = first.astext() if first is not None else ""
        if not hasattr(self.env, "mtp_rules"):
            self.env.mtp_rules = {}
        self.env.mtp_rules[label] = (self.env.docname, node["ids"][0], text)
        return [node]


class diagram_node(nodes.General, nodes.Element):
    pass


def visit_diagram(self, node):
    extra = {"style": f"max-width: {node['max_width']}"} if node.get("max_width") else {}
    self.body.append(self.starttag(node, "figure", CLASS="mtp-diagram", **extra))
    self.body.append(node["svg"])
    self.body.append("<figcaption>")
    self.add_fignumber(node)


def depart_diagram(self, node):
    self.body.append("</figcaption></figure>\n")


class Diagram(SphinxDirective):
    """```{diagram} label
    :file: diagrams/name.svg
    :max-width: 35rem

    The caption.
    ```"""

    required_arguments = 1
    has_content = True
    option_spec = {"file": directives.unchanged_required, "max-width": directives.unchanged}

    def run(self):
        label = self.arguments[0]
        rel, path = self.env.relfn2path(self.options["file"], self.env.docname)
        self.env.note_dependency(rel)
        node = diagram_node(label=label, svg=Path(path).read_text().strip(), max_width=self.options.get("max-width"))
        node["names"].append(label)
        self.state.document.note_explicit_target(node)
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


class rule_index_node(nodes.General, nodes.Element):
    pass


class RuleIndex(SphinxDirective):
    """```{rule-index}
    ```
    Every rule of the spec, in order, with its number, its label and its first sentence, so that
    rules that overlap or repeat each other can be seen side by side."""

    def run(self):
        return [rule_index_node()]


def _purge_rules(app, env, docname):
    rules = getattr(env, "mtp_rules", {})
    for label in [k for k, v in rules.items() if v[0] == docname]:
        del rules[label]


def _merge_rules(app, env, docnames, other):
    if not hasattr(env, "mtp_rules"):
        env.mtp_rules = {}
    env.mtp_rules.update(getattr(other, "mtp_rules", {}))


def _fill_rule_index(app, doctree, fromdoc):
    env = app.builder.env
    rules = getattr(env, "mtp_rules", {})

    def number(item):
        docname, ident, _ = item[1]
        return env.toc_fignumbers.get(docname, {}).get("rule", {}).get(ident, (999,))

    for placeholder in list(doctree.findall(rule_index_node)):
        table = nodes.bullet_list(classes=["mtp-rule-index"])
        for label, (docname, ident, text) in sorted(rules.items(), key=number):
            num = ".".join(map(str, number((label, (docname, ident, text)))))
            uri = app.builder.get_relative_uri(fromdoc, docname) + "#" + ident
            sentence = text.split(". ")[0].strip().rstrip(".") + "."
            para = nodes.paragraph()
            para += nodes.reference("", f"Rule {num}", refuri=uri)
            para += nodes.Text(" ")
            para += nodes.literal("", label)
            para += nodes.Text(" " + sentence)
            table += nodes.list_item("", para)
        placeholder.replace_self(table)


class MtpExample(SphinxDirective):
    """```{mtp-example}
    :show: v spin
    (scene …)
    ```
    show lists the views and controls to place, in order. Without it, every one is placed, in
    the order the source declares them."""

    has_content = True
    option_spec = {"show": directives.unchanged, "source": directives.flag}

    def run(self):
        src = "\n".join(self.content)
        try:
            mtpc = compiled(src)
        except Exception as e:  # a parse or compile error, with its line and column
            raise self.error(f"the example does not compile: {e}") from None
        model = json.loads(mtpc)
        placeable = {
            o["name"]: o["kind"]
            for o in model["objects"]
            if o.get("name") and o["kind"] in compiler.VIEWS + PLACED_CONTROLS
        }
        wanted = self.options.get("show", "").split() or list(placeable)
        unknown = [n for n in wanted if n not in placeable]
        if unknown:
            raise self.error(f"the example has no view or control named {', '.join(unknown)}")

        number = self.env.new_serialno("mtp-example")
        mid = f"ex-{self.env.docname.replace('/', '-')}-{number}"
        data = mtpc.strip().replace("</", "<\\/")
        parts = [f'<mtp-model id="{mid}" src="#{mid}-data"></mtp-model>']
        for n in wanted:
            tag = f"mtp-{placeable[n]}"
            parts.append(f'<{tag} model="{mid}" name="{html.escape(n)}"></{tag}>')
        parts.append(f'<script type="application/json" id="{mid}-data">{data}</script>')

        code = nodes.literal_block(src, src, language="mtp")
        live = nodes.raw("", '<div class="mtp-live">' + "\n".join(parts) + "</div>", format="html")
        box = example_node()
        box["names"].append(f"example-{mid}")
        self.state.document.note_explicit_target(box)
        box += [code, live]
        return [box]


class example_node(nodes.General, nodes.Element):
    pass


def visit_example(self, node):
    self.body.append(self.starttag(node, "div", CLASS="mtp-example"))
    self.body.append('<p class="mtp-example-head">')
    self.add_fignumber(node)
    self.body.append('</p><div class="mtp-example-body">')


def depart_example(self, node):
    self.body.append("</div></div>\n")


def _readable_json(value, indent: str = "") -> str:
    """JSON with one line for each value that is short enough, and otherwise one line for each
    member or item."""
    flat = json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    if len(indent) + len(flat) <= 96 or not isinstance(value, (dict, list)) or not value:
        return flat
    inner = indent + "  "
    if isinstance(value, dict):
        lines = [f"{inner}{json.dumps(k)}: {_readable_json(v, inner)}" for k, v in value.items()]
        return "{\n" + ",\n".join(lines) + f"\n{indent}}}"
    lines = [inner + _readable_json(v, inner) for v in value]
    return "[\n" + ",\n".join(lines) + f"\n{indent}]"


class MtpcOf(SphinxDirective):
    """```{mtpc-of} pages/name/name.mtp
    ```
    The .mtpc of a source file, compiled while the spec is built, with its size in bytes as
    written, and shown with line breaks added so that it can be read."""

    required_arguments = 1

    def run(self):
        rel, path = self.env.relfn2path(self.arguments[0])
        self.env.note_dependency(rel)
        src = Path(path)
        try:
            mtpc = compiled(src.read_text(encoding="utf-8"), src)
        except Exception as e:  # a parse or compile error, with its line and column
            raise self.error(f"{src.name} does not compile: {e}") from None
        size = len(mtpc.encode("utf-8"))
        para = nodes.paragraph()
        para += nodes.Text(
            f"The compiler compiles {src.name} into {src.stem}.mtpc, {size:,} bytes, shown here"
            " whole with line breaks added:"
        )
        shown = _readable_json(json.loads(mtpc))
        code = nodes.literal_block(shown, shown, language="json", classes=["mtpc-whole"])
        return [para, code]


PLACED_CONTROLS = ("slider", "button", "play", "stepper", "toggle")

GRAMMAR = Path(__file__).parent.parent / "spec" / "mtp.lark"
# A string in quotes, a regular expression between slashes, or a name of a rule or a token.
GRAMMAR_PIECE = re.compile(r'"(?:\\.|[^"\\])*"|/(?:\\.|[^/\\])*/|[A-Za-z_][A-Za-z_0-9]*')


def grammar_sections(text: str) -> dict[str, list[tuple[str, str]]]:
    """The rules of each section of the grammar, as (name, definition), in order. A line that
    goes on with another alternative of the rule above has the name ""."""
    sections: dict[str, list[tuple[str, str]]] = {}
    current: list[tuple[str, str]] | None = None
    for line in text.splitlines():
        if line.startswith("//:"):
            current = sections.setdefault(line[3:].strip(), [])
        elif not line.strip() or line.lstrip().startswith("//"):
            continue
        elif current is None:
            raise ValueError(f"a rule before the first section of {GRAMMAR.name}: {line}")
        elif line[0].isspace():
            current.append(("", line.strip()))
        else:
            name, _, definition = line.partition(":")
            current.append((name.strip(), definition.strip()))
    return sections


def _defined(name: str) -> str:
    """The name that a rule's head defines: form for form{w}, INT for INT.2, operator for
    !operator."""
    return re.sub(r"[{.].*$", "", name).lstrip("!?")


class MtpGrammar(ProductionList):
    """```{mtp-grammar} section
    ```
    The productions of one section of docs/spec/mtp.lark."""

    required_arguments = 1
    final_argument_whitespace = False
    has_content = True

    def run(self):
        sections = grammar_sections(GRAMMAR.read_text(encoding="utf-8"))
        self.env.note_dependency(str(GRAMMAR))
        section = self.arguments[0]
        if section not in sections:
            raise self.error(f"{GRAMMAR.name} has no section {section!r}")
        names = {_defined(n) for rules in sections.values() for n, _ in rules if n}

        def linked(definition: str) -> str:
            def link(m: re.Match) -> str:
                word = m.group(0)
                return f"`{word}`" if word in names else word

            return GRAMMAR_PIECE.sub(link, definition)

        lines = ["mtp"]
        for name, definition in sections[section]:
            lines.append(f"{name}: {linked(definition)}")
        self.arguments = ["\n".join(lines)]
        return super().run()

    def make_name_target(self, *, name, production_group, location):
        # The target is the name that the rule defines, so that form{w} and INT.2 are found as
        # form and INT, while the list shows the head as the grammar writes it.
        name_node = addnodes.literal_strong(name, name)
        defined = _defined(name)
        node_id = f"grammar-token-{production_group}-{defined}"
        name_node["ids"].append(node_id)
        self.state.document.note_implicit_target(name_node, name_node)
        std = self.env.domains.standard_domain
        std.note_object("token", f"{production_group}:{defined}", node_id, location=location)
        return name_node


def _definition_text(node) -> str:
    # Citations are left out, since a tooltip cannot link anywhere.
    if isinstance(node, addnodes.pending_xref) and node.get("reftype") in ("numref", "ref", "doc"):
        return ""
    if isinstance(node, nodes.Text):
        return str(node)
    return "".join(_definition_text(child) for child in node.children)


def _collect_terms(app, doctree):
    env = app.env
    if not hasattr(env, "mtp_terms"):
        env.mtp_terms = {}
    for glossary in doctree.findall(addnodes.glossary):
        for item in glossary.findall(nodes.definition_list_item):
            text = " ".join(_definition_text(item.next_node(nodes.definition)).split())
            text = re.sub(r"\s*Defined in .*$", "", text)
            text = re.sub(r"\s*\((\s|,|and)*\)", "", text)
            for term in item.findall(nodes.term):
                for ident in term["ids"]:
                    env.mtp_terms[ident] = (env.docname, f"{term.astext()}: {text}")


def _purge_terms(app, env, docname):
    terms = getattr(env, "mtp_terms", {})
    for ident in [k for k, v in terms.items() if v[0] == docname]:
        del terms[ident]


def _merge_terms(app, env, docnames, other):
    if not hasattr(env, "mtp_terms"):
        env.mtp_terms = {}
    env.mtp_terms.update(getattr(other, "mtp_terms", {}))


def _title_term_links(app, doctree, fromdoc):
    terms = getattr(app.builder.env, "mtp_terms", {})
    for ref in doctree.findall(nodes.reference):
        inline = ref.next_node(nodes.inline)
        if inline is None or "std-term" not in inline["classes"]:
            continue
        ident = ref.get("refuri", "").rpartition("#")[2] or ref.get("refid", "")
        if ident in terms:
            ref["reftitle"] = terms[ident][1]


def copy_runtime(app: Sphinx):
    """The runtime is built from web/src when it is older than its source (mathterpiece.build)."""
    static = Path(app.outdir) / "_static"
    static.mkdir(parents=True, exist_ok=True)
    try:
        (static / "mathterpiece.js").write_text(runtime(), encoding="utf-8")
    except BuildError as e:
        raise RuntimeError(str(e)) from None


def write_pages(app: Sphinx):
    """Each folder of spec/pages holds a source and a page that places it. The page is written
    out with the compiled source and the runtime next to it, so it is served as an author would
    serve it, and a source that does not compile stops the build."""
    pages = Path(app.srcdir) / "spec" / "pages"
    # The docs are a second project that uses this extension and has no pages of its own.
    if not pages.is_dir():
        return
    for folder in sorted(pages.iterdir()):
        out = Path(app.outdir) / "spec" / "pages" / folder.name
        out.mkdir(parents=True, exist_ok=True)
        for src in sorted(folder.glob("*.mtp")):
            try:
                mtpc = compiled(src.read_text(encoding="utf-8"), src)
            except Exception as e:  # a parse or compile error, with its line and column
                raise RuntimeError(f"{src.name} does not compile: {e}") from None
            (out / f"{src.stem}.mtpc").write_text(mtpc, encoding="utf-8")
        for page in sorted(folder.glob("*.html")):
            (out / page.name).write_text(page.read_text(encoding="utf-8"), encoding="utf-8")
        (out / "mathterpiece.js").write_text(runtime(), encoding="utf-8")


def _highlight_inline(app: Sphinx, doctree, docname: str) -> None:
    """Inline code is highlighted as mtp, as code blocks are. Code that the lexer cannot read
    without an error, such as a file name or HTML, and code inside a cross-reference stay plain."""
    lexer = MtpLexer(ensurenl=False)
    for lit in list(doctree.findall(nodes.literal)):
        if "xref" in lit["classes"] or "mtp-inline" in lit["classes"]:
            continue
        if any(not isinstance(child, nodes.Text) for child in lit.children):
            continue
        tokens = list(lexer.get_tokens(lit.astext()))
        if not tokens or any(tok in Error for tok, _ in tokens):
            continue
        lit.children = []
        for tok, value in tokens:
            while tok not in STANDARD_TYPES:
                tok = tok.parent
            short = STANDARD_TYPES[tok]
            lit += nodes.inline(value, value, classes=[short]) if short else nodes.Text(value)
        lit["classes"] += ["highlight", "mtp-inline"]


def setup(app: Sphinx):
    app.add_lexer("mtp", MtpLexer)
    app.add_enumerable_node(rule_node, "rule", _rule_title, html=(visit_rule, depart_rule))
    app.add_directive("rule", Rule)
    app.add_enumerable_node(diagram_node, "diagram", lambda n: n.astext() or n.get("label", ""), html=(visit_diagram, depart_diagram))
    app.add_directive("diagram", Diagram)
    app.add_node(rule_index_node)
    app.add_directive("rule-index", RuleIndex)
    app.connect("env-purge-doc", _purge_rules)
    app.connect("env-merge-info", _merge_rules)
    app.connect("doctree-resolved", _fill_rule_index)
    app.connect("doctree-read", _collect_terms)
    app.connect("env-purge-doc", _purge_terms)
    app.connect("env-merge-info", _merge_terms)
    app.connect("doctree-resolved", _title_term_links)
    app.connect("doctree-resolved", _highlight_inline)
    app.add_enumerable_node(example_node, "example", lambda n: "example", html=(visit_example, depart_example))
    app.add_directive("mtp-example", MtpExample)
    app.add_directive("mtp-grammar", MtpGrammar)
    app.add_directive("mtpc-of", MtpcOf)
    app.add_js_file("mathterpiece.js", type="module")
    app.add_js_file("mtp-terms.js", defer="defer")
    # The design system that draws the controls, as on the inventory page.
    app.add_css_file(BRAIID)
    app.connect("builder-inited", copy_runtime)
    app.connect("builder-inited", write_pages)
    return {"version": "0.1", "parallel_read_safe": True}
