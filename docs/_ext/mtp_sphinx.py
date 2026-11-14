"""The Sphinx extension of the mtp site.

- The lexer `mtp` highlights code blocks written ```mtp.
- The directive `rule` states one rule of the spec. Rules are numbered by part, as 4.2 for the
  second rule of part 4, and cited by label with {numref}`label`, so a citation keeps working when
  rules are added or moved.
- The directive `mtp-example` compiles its source while the site is built and shows it highlighted,
  then live. A source that does not compile fails the build, so an example never goes stale.
"""

import html
import json
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
from sphinx.application import Sphinx
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
NAME = r"[^\s()\[\]'\";.]+"


def _word(lexer, match):
    word = match.group(0)
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
    yield match.start(), kind, word


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
            (r"'(\\.|[^'\\])*'", String),
            (r"-?\d+/\d+", Number),
            (r"-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?i?(?![^\s()\[\]'\";.])", Number),
            (r"(\.)(" + NAME + ")", bygroups(Punctuation, Name.Attribute)),
            (r"[()\[\]]", Punctuation),
            (NAME, _word),
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
        parts += [f'<mtp-{placeable[n]} model="{mid}" name="{html.escape(n)}"></mtp-{placeable[n]}>' for n in wanted]
        parts.append(f'<script type="application/json" id="{mid}-data">{data}</script>')

        code = nodes.literal_block(src, src, language="mtp")
        live = nodes.raw("", '<div class="mtp-live">' + "\n".join(parts) + "</div>", format="html")
        box = nodes.container(classes=["mtp-example"])
        box += [code, live]
        return [box]


PLACED_CONTROLS = ("slider", "button", "play", "stepper", "toggle")


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
    app.add_enumerable_node(
        rule_node, "rule", _rule_title, html=(visit_rule, depart_rule)
    )
    app.add_directive("rule", Rule)
    app.add_directive("mtp-example", MtpExample)
    app.add_js_file("mathterpiece.js", type="module")
    # The design system that draws the controls, as on the inventory page.
    app.add_css_file(BRAIID)
    app.connect("builder-inited", copy_runtime)
    return {"version": "0.1", "parallel_read_safe": True}

