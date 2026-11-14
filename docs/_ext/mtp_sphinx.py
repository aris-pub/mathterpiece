"""The Sphinx extension of the mtp site.

- The lexer `mtp` highlights code blocks written ```mtp.
- The directive `rule` states one rule of the spec. Rules are numbered by part, as 4.2 for the
  second rule of part 4, and cited by label with {numref}`label`, so a citation keeps working when
  rules are added or moved.
- The directive `mtp-example` compiles its source while the site is built and shows it highlighted,
  then live. A source that does not compile fails the build, so an example never goes stale.
- The directive `mtp-grammar` shows one section of the reader grammar, docs/spec/mtp.lark, as a
  list of productions in which each name links to its definition. tests/test_grammar.py checks the
  same file against the reader.
"""

import html
import json
import re
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import directives
from pygments.lexer import RegexLexer, bygroups
from pygments.token import (
    Comment,
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
    "palette",
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
BUILTIN = {*builtins.BUILTINS, *builtins.SPECIAL_BUILTINS, *compiler.COLLECTION}
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
            (r"\$'(\\.|[^'\\])*'", String.Interpol),
            (r"#'(\\.|[^'\\])*'", String.Other),
            (r"tex'(\\.|[^'\\])*'", String),
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
        return [node]


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
        box = nodes.container(classes=["mtp-example"])
        box += [code, live]
        return [box]


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


def copy_runtime(app: Sphinx):
    """The runtime is built from web/src when it is older than its source (mathterpiece.build)."""
    static = Path(app.outdir) / "_static"
    static.mkdir(parents=True, exist_ok=True)
    try:
        (static / "mathterpiece.js").write_text(runtime(), encoding="utf-8")
    except BuildError as e:
        raise RuntimeError(str(e)) from None


def setup(app: Sphinx):
    app.add_lexer("mtp", MtpLexer)
    app.add_enumerable_node(rule_node, "rule", _rule_title, html=(visit_rule, depart_rule))
    app.add_directive("rule", Rule)
    app.add_directive("mtp-example", MtpExample)
    app.add_directive("mtp-grammar", MtpGrammar)
    app.add_js_file("mathterpiece.js", type="module")
    # The design system that draws the controls, as on the inventory page.
    app.add_css_file(BRAIID)
    app.connect("builder-inited", copy_runtime)
    return {"version": "0.1", "parallel_read_safe": True}
