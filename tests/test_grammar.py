"""The grammar of the spec (docs/spec/mtp.lark) against the parser (mathterpiece/parse.py).

The spec renders the grammar from the same file (docs/spec/grammar.md). Every source below must be
accepted by both or rejected by both, and where both accept it, the grammar's tree, built into the
parser's nodes by Reading below, must equal the parser's. Positions are not compared.

The grammar states the decided language. Where the parser does not follow it yet, the source is
listed in KNOWN_DIFFERENCES with the bead that will change the parser."""

import logging
import random
import re
from fractions import Fraction
from pathlib import Path

import pytest
from lark import Lark, Token, Transformer
from lark.exceptions import LarkError

from mathterpiece.nodes import (
    Bar,
    BoolLit,
    Brackets,
    ComplexLit,
    Field,
    Form,
    InterpStrLit,
    IntLit,
    ListLit,
    Name,
    NoneLit,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.parse import ParseError, _Parser, parse

ROOT = Path(__file__).parent.parent
GRAMMAR = ROOT / "docs" / "spec" / "mtp.lark"
SPEC = ROOT / "docs" / "spec"

CORPUS = sorted(
    p
    for folder in ("examples", "tests/shared", "tests/malformed", "web/test/fixtures", "web/demo")
    for p in (ROOT / folder).rglob("*.mtp")
) + sorted((ROOT / "mathterpiece" / "stdlib").glob("*.mtp"))


def _spec_examples() -> list[tuple[str, str]]:
    """Each {mtp-example} block and each ```mtp fence of the spec, with where it is."""
    found = []
    fence = re.compile(r"^(`{3,})(\{mtp-example\}|mtp)[ \t]*\n(.*?)^\1[ \t]*$", re.M | re.S)
    for page in sorted(SPEC.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        for k, m in enumerate(fence.finditer(text)):
            lines = m[3].splitlines()
            while lines and lines[0].startswith(":"):
                lines.pop(0)
            # In a template such as (H_ ITEMS…), … marks the place of more items. It is no
            # character of a source, so it is dropped.
            source = "\n".join(lines).replace("…", "")
            found.append((f"{page.name}#{k}", source + "\n"))
    return found


SPEC_EXAMPLES = _spec_examples()

# Sources that the parser accepts, for the corners of the grammar that the corpus does not reach.
ACCEPTED = [
    "",
    "  ; only a comment\n",
    "\n(f)\n",
    "(a)(b)",
    "(a (b)(c))",
    "(f a(b)c)",
    "(f (a)b)",
    "(f 'x'(b))",
    "(f [1](b))",
    "(f (b)'x')",
    "(f\t a\n\r b)",
    "(f\r\n a)",
    "(f 3 -2 +4 007)",
    "(f 1/3 -2/4 1/05)",
    "(f 2.5 1. .5 -.5 1e3 1.5E-3 +2e+2)",
    "(f 2i -1.5i 1e3i 1+2i 1-2.5e3i -1e+2+3i)",
    "(f true false none)",
    "(f truex the-true-value nonex true-x none? true? x.none? found?.x ball.on-floor?)",
    "(f + - * / ^ < <= > >= = != .)",
    "(f a-b a- a--b a? none? a?.b a1 a-1 Ab)",
    "(f p.r p.pos.x)",
    "(f xs[0] xs[-1] xs[(+ k 1)] g['m1'] xs[ 0 ] f[real real] xs[0][1])",
    "(f xs[0].a xs[0].a.b[1].c xs[0].truex xs[none])",
    "(f [] [ ] [1 2] [[1] [2]] [a b c][h] [a][0][1] [(f)(g)])",
    "(f real|none a|b|c 1|2 a[0]|b b|c[0] true|x .|a)",
    "(f 'a' 'it\\'s' 'back\\\\slash' 'line\\nbreak' '')",
    "(f tex'\\frac12' tex'f\\'(x)' tex'a\\\\' tex'\\q')",
    "(f $'x = {x}' $'{x:.2f}' $'{ x }' $'{x :>5}' $'{x:}' $'{{lit}}' $'}}' $'{(* 2 a)}')",
    "(f $'{[1 2]}' $'{'s'}' $'{a[0]}' $'{a|b}' $'{$'{a}' }')",
    "(f $'{(g ; a comment\n x)}')",
    "(f $'{a:b}' $'{a.b:c}' $'{a[0].b:c}' $'{#'n-{k}'.x :y}')",
    "(f #'dot-{k}' #'dot-{k}'.pos #'row-{i}'[0] #'a{b}'.c.d[0].e #'{k}')",
    "(f doc@'text')",
    "(real k free@(* 2 a))",
    "(f free@x free@[1] free@'s' free@free@(g))",
    "(f free@(g)x (h)free@x)",
    "(circle_ (r 1))",
    "(circle_(r 1))",
    "(line|none_ (r 1))",
    "(true|none_ x)",
    "(marks.grid_ a)",
    "(a.b-c_ x)",
    "(none_ a)",
    "(a_)",
    "(f (g_ x))",
    "(f)",
    "()",
]

# Sources that the parser rejects.
REJECTED = [
    "x",
    "'s'",
    "[1]",
    "(a)x",
    "(a",
    "(a))",
    ")",
    "(a]",
    "(a [1)",
    '(f "x")',
    "(f {a})",
    "(f })",
    "(f a {)",
    "(f 'a)",
    "(f $'a)",
    "(f tex'a)",
    "(f 'a\\q')",
    "(f 'a'b)",
    "(f 'a''b')",
    "(f 'a'[0])",
    "(f [1]x)",
    "(f [1].x)",
    "(f [1][])",
    "(f [1][0 1])",
    "(f (a).b)",
    "(f (a)[0])",
    "(f a [0]b)",
    "(f xs[])",
    "(f xs[ ])",
    "(f xs[0)",
    "(f xs[0]x)",
    "(f xs[0].)",
    "(f xs[0].1)",
    "(f 1[0])",
    "(f true[0])",
    "(f +[0])",
    "(f .[0])",
    "(f 12abc)",
    "(f 1/0)",
    "(f 1/٠)",
    "(f 1/2/3)",
    "(f 1-2)",
    "(f 1e)",
    "(f 1.5.x)",
    "(f -x)",
    "(f +a)",
    "(f <=x)",
    "(f ²x)",
    "(f a.)",
    "(f .a)",
    "(f a..b)",
    "(f a/b)",
    "(f a^b)",
    "(f a$b)",
    "(f a#b)",
    "(f a@b)",
    "(f free@)",
    "(f free@ x)",
    "(f doc@ 'x')",
    "(f doc@x)",
    "(f _)",
    "(_ x)",
    "(f a_b)",
    "(f _a)",
    "(f a|)",
    "(f a| b)",
    "(f a |b)",
    "(f a||b)",
    "(f a|'b')",
    "(f a|(b))",
    "(f a|[b])",
    "(f a|doc@'x')",
    "(f $'{}')",
    "(f $'{ }')",
    "(f $'{:x}')",
    "(f $'{a b}')",
    "(f $'{(g)x}')",
    "(f $'}')",
    "(f $'a}b')",
    "(f $'{x:{y}}')",
    "(f $'{x:a'b}')",
    "(f $'{(g a:b)}')",
    "(f $x)",
    "(f #x)",
    "(f #'plain')",
    "(f #'a{b}'x)",
    "(f #'a{b}'.)",
    "(f #'a{b}'[])",
    "(f 'a':b)",
    "(f none[0]x)",
]

BOM = "mtp-ydd4.7.1"
BLANKS = "mtp-ydd4.7.2"
NAMES = "mtp-ydd4.7.3"
DIGITS = "mtp-ydd4.7.4"
NESTED_BRACES = "mtp-kzx2"
BRACE_COMMENTS = "mtp-ydd4.7.31"
LITERAL_PARTS = "mtp-ydd4.7.32"

# Sources on which the grammar, which states the decided language, and today's parser differ.
# Each one names the bead that will change the parser. Once the parser follows the spec on a
# source, test_known_difference fails, and the entry is removed.
KNOWN_DIFFERENCES = {
    "﻿(f)": BOM,
    "﻿\n(f)": BOM,
    "(f a)": BLANKS,
    "(f a b)": BLANKS,
    "　(f)": BLANKS,
    "(f a!b)": NAMES,
    "(f a?b)": NAMES,
    "(f a*b)": NAMES,
    "(f a=b)": NAMES,
    "(f !=x)": NAMES,
    "(f a')": NAMES,
    "(f a'')": NAMES,
    "(f a'b)": NAMES,
    "(f f'(x))": NAMES,
    "(f a:b)": NAMES,
    "(f :a)": NAMES,
    "(f :)": NAMES,
    "(f θ)": NAMES,
    "(f ünï)": NAMES,
    "(f x²)": NAMES,
    "(f a\x00b)": NAMES,
    "(f a﻿b)": NAMES,
    "(f xs[0]._)": NAMES,
    "(f xs[0].tex'q')": NAMES,
    "(f a|tex'q')": NAMES,
    "(f a_)": NAMES,
    "(f a b_)": NAMES,
    "(f a|b_)": NAMES,
    "(f a_.b)": NAMES,
    "(f _.a)": NAMES,
    "(f a._)": NAMES,
    "(f _[0])": NAMES,
    "(a_.b x)": NAMES,
    "(f ٣)": DIGITS,
    "(f 1/٣)": DIGITS,
    "(f ١.٥)": DIGITS,
    # After a string nested in braces ends, the parser reads the rest of the braces as if it were
    # outside them.
    "(f $'{$'{a}'}')": NESTED_BRACES,
    "(f $'{#'n-{k}'.x:y}')": NESTED_BRACES,
    "(f $'{[$'{a}' b]}')": NESTED_BRACES,
    "(f $'{x ; a comment\n}')": BRACE_COMMENTS,
    "(f $'{ ;c\n x}')": BRACE_COMMENTS,
    "(f #'a{k ;c\n}')": BRACE_COMMENTS,
    "(f true.x)": LITERAL_PARTS,
    "(f none.x)": LITERAL_PARTS,
    "(f x.none)": LITERAL_PARTS,
    "(f p.true)": LITERAL_PARTS,
    "(f xs[0].false)": LITERAL_PARTS,
    "(f none[0])": LITERAL_PARTS,
    "(a.true_ x)": LITERAL_PARTS,
}

OPERATOR_NAMES = {"+", "-", "*", "/", "^", "<", "<=", ">", ">=", "=", "!=", ".", "free@"}
NAME_PART = re.compile(r"[A-Za-z][A-Za-z0-9-]*\??")


def _bad_name(node) -> bool:
    """Whether a node holds a name part that the rule name-characters does not allow."""
    if isinstance(node, Name):
        if len(node.parts) == 1 and node.parts[0] in OPERATOR_NAMES:
            return False
        return any(
            _bad_name(p) if not isinstance(p, str) else not NAME_PART.fullmatch(p)
            for p in node.parts
        )
    if isinstance(node, (Form, ListLit, Bar, Brackets)):
        return any(_bad_name(x) for x in node.items)
    if isinstance(node, InterpStrLit):
        return any(_bad_name(p) for p in node.parts if not isinstance(p, str))
    if isinstance(node, Field):
        return _bad_name(node.expr)
    return False


def _names_step(forms):
    return None if any(_bad_name(f) for f in forms) else forms


LITERALS = {"true", "false", "none"}


def _literal_part(node) -> bool:
    """Whether a node holds a name with a part that is exactly true, false or none."""
    if isinstance(node, Name):
        return any(p in LITERALS if isinstance(p, str) else _literal_part(p) for p in node.parts)
    if isinstance(node, (Form, ListLit, Bar, Brackets)):
        return any(_literal_part(x) for x in node.items)
    if isinstance(node, InterpStrLit):
        return any(_literal_part(p) for p in node.parts if not isinstance(p, str))
    if isinstance(node, Field):
        return _literal_part(node.expr)
    return False


def _literal_parts_step(forms):
    return None if any(_literal_part(f) for f in forms) else forms


class _NoCommentInBraces(_Parser):
    """The parser once BRACE_COMMENTS is done: around the expression in the braces of an
    interpolated string, whitespace and no comment."""

    def __init__(self, src: str):
        super().__init__(src)
        self.around: list[bool] = []

    def interp_part(self):
        self.around.append(True)
        try:
            return super().interp_part()
        finally:
            self.around.pop()

    def node(self):
        # Inside the expression, such as a form in the braces, comments are allowed again.
        saved, self.around = self.around, []
        try:
            return super().node()
        finally:
            self.around = saved

    def skip_blank(self):
        if not self.around:
            return super().skip_blank()
        while self.peek() and self.peek().isspace():
            self.advance()
        if self.peek() == ";":
            raise ParseError("a comment in braces", self.pos())


# For the random sources, which no list could name in advance: the parser as it will be once each
# bead is done. A step or a parser is removed together with the last KNOWN_DIFFERENCES entry of
# its bead.
PENDING_PARSERS = {BRACE_COMMENTS: _NoCommentInBraces}
PENDING_STEPS = {NAMES: _names_step, LITERAL_PARTS: _literal_parts_step}


def parser_after_beads(src: str):
    try:
        forms = _NoCommentInBraces(src).parse() if PENDING_PARSERS else parse(src)
    except ParseError:
        return None
    for step in PENDING_STEPS.values():
        if forms is not None:
            forms = step(forms)
    return forms


def _decoded(body: str, braces: bool = False) -> str:
    """The text of a string with its escapes undone, and with its doubled braces undone too when
    braces is true, as in an interpolated string."""
    escapes = {"'": "'", "\\": "\\", "n": "\n"}
    out, i = [], 0
    while i < len(body):
        ch = body[i]
        if ch == "\\":
            out.append(escapes[body[i + 1]])
            i += 2
        elif braces and ch in "{}":
            out.append(ch)
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _tex(body: str) -> str:
    out, i = [], 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body):
            out.append("'" if body[i + 1] == "'" else body[i : i + 2])
            i += 2
        else:
            out.append(body[i])
            i += 1
    return "".join(out)


def _without_underscore(text: str):
    """The head (head_ …) without its underscore (grammar.md, rule unnamed-head)."""
    if text == "none_":
        return NoneLit()
    return Name(tuple(text[:-1].split(".")))


def _dot(whole, part):
    return Form((Name((".",)), whole, part))


UREAL = r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?"
SPLIT_COMPLEX = re.compile(rf"([+-]?{UREAL})([+-]{UREAL})i")


def _flat(c):
    out = []
    for x in c:
        if isinstance(x, list):
            out.extend(x)
        elif not isinstance(x, Token):
            out.append(x)
    return out


class Reading(Transformer):
    """The grammar's tree as the parser's nodes."""

    def start(self, forms):
        return tuple(forms)

    def form(self, c):
        return Form(tuple(_flat(c)))

    list_items = items = head_items = touching = head_touching = lambda self, c: _flat(c)

    def head(self, c):
        *words, last = c
        head = _without_underscore(last.value)
        if words:
            head = Bar((*words, head))
        return [head, NoneLit()]

    def expression(self, c):
        return c[0]

    paren = plain = expression

    def free(self, c):
        return Form((Name(("free@",)), c[-1]))

    def list(self, c):
        whole = ListLit(tuple(c[0]))
        for index in c[1:]:
            whole = _dot(whole, index)
        return whole

    def list_brackets(self, c):
        return next(x for x in c if not isinstance(x, Token))

    def brackets(self, c):
        items = next(x for x in c if isinstance(x, list))
        return items[0] if len(items) == 1 else Brackets(tuple(items))

    def word(self, c):
        return c[0] if len(c) == 1 else Bar(tuple(c))

    def one_word(self, c):
        first = c[0]
        if isinstance(first, Token):
            if first.type == "NONE":
                return NoneLit()
            parts: list = first.value.split(".")
            for part in c[1:]:
                parts.extend(part)
            return Name(tuple(parts))
        return first

    def after_brackets(self, c):
        parts: list = []
        for x in c:
            if isinstance(x, Token):
                parts.extend(x.value.split("."))
            else:
                parts.append(x)
        return parts

    def name_string(self, c):
        whole = Form((Name(("name",)), c[0]))
        for x in c[1:]:
            if isinstance(x, Token):
                for part in x.value.split("."):
                    whole = _dot(whole, Name((part,)))
            else:
                whole = _dot(whole, x)
        return whole

    def number(self, c):
        (t,) = c
        text = t.value
        if t.type == "INT":
            return IntLit(int(text))
        if t.type == "RATIO":
            num, den = text.split("/")
            return RatioLit(Fraction(int(num), int(den)))
        if t.type == "REAL":
            return RealLit(float(text))
        if t.type == "IMAG":
            return ComplexLit(complex(0, float(text[:-1])))
        m = SPLIT_COMPLEX.fullmatch(text)
        assert m is not None
        return ComplexLit(complex(float(m[1]), float(m[2])))

    def bool(self, c):
        return BoolLit(c[0].value == "true")

    def operator(self, c):
        return Name((c[0].value,))

    def string(self, c):
        (t,) = c
        if t.type == "TEX":
            return StrLit(_tex(t.value[4:-1]), tex=True)
        return StrLit(_decoded(t.value[1:-1]))

    def doc(self, c):
        return Form((Name(("doc",)), self.string([c[1]])))

    def _pieces(self, c):
        parts = []
        for x in c:
            if isinstance(x, Token):
                if x.type == "TEXT":
                    parts.append(_decoded(x.value, braces=True))
            else:
                parts.append(x)
        return InterpStrLit(tuple(parts))

    interpolated = name_string_text = _pieces

    def braces(self, c):
        expr = next(x for x in c if not isinstance(x, Token))
        spec = next((x.value[1:] for x in c if isinstance(x, Token) and x.type == "FORMAT"), None)
        return expr if spec is None else Field(expr, spec)


def load() -> Lark:
    return Lark(GRAMMAR.read_text(encoding="utf-8"), parser="lalr", lexer="contextual", debug=True)


@pytest.fixture(scope="module")
def grammar() -> Lark:
    return load()


def test_no_conflicts(caplog):
    # Lark settles a shift/reduce conflict by shifting and only logs it, so the grammar would no
    # longer mean what it says.
    with caplog.at_level(logging.DEBUG, logger="lark"):
        load()
    assert not [r.message for r in caplog.records if "conflict" in r.message.lower()]


def read_grammar(grammar: Lark, src: str):
    try:
        tree = grammar.parse(src)
    except LarkError:
        return None
    return Reading().transform(tree)


def read_both(grammar: Lark, src: str):
    """The parser's forms and the grammar's, each None when it rejects the source."""
    try:
        parsed = parse(src)
    except ParseError:
        parsed = None
    return parsed, read_grammar(grammar, src)


def check(grammar: Lark, src: str) -> None:
    parsed, ours = read_both(grammar, src)
    if parsed is None:
        assert ours is None, "the grammar accepts what the parser rejects"
    else:
        assert ours is not None, "the grammar rejects what the parser accepts"
        assert ours == parsed


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: str(p.relative_to(ROOT)))
def test_corpus(grammar, path):
    check(grammar, path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("src", [s for _, s in SPEC_EXAMPLES], ids=[k for k, _ in SPEC_EXAMPLES])
def test_spec_example(grammar, src):
    check(grammar, src)
    # A fragment is a sequence of nodes, so it is also read as the items of a form.
    check(grammar, f"(\n{src}\n)")


@pytest.mark.parametrize("src", ACCEPTED)
def test_accepted(grammar, src):
    assert read_both(grammar, src)[0] is not None, "the parser rejects this source"
    check(grammar, src)


@pytest.mark.parametrize("src", REJECTED)
def test_rejected(grammar, src):
    parsed, ours = read_both(grammar, src)
    assert parsed is None, "the parser accepts this source"
    assert ours is None, "the grammar accepts this source"


@pytest.mark.parametrize("src", KNOWN_DIFFERENCES, ids=KNOWN_DIFFERENCES.values())
def test_known_difference(grammar, src):
    parsed, ours = read_both(grammar, src)
    assert parsed != ours, (
        f"the parser now follows the spec on {src!r}: remove the entry, and close"
        f" {KNOWN_DIFFERENCES[src]} once it has no entry left"
    )


def test_pending_steps_have_entries():
    # A step with no entry left models a change that the parser has made already.
    assert {*PENDING_STEPS, *PENDING_PARSERS} <= set(KNOWN_DIFFERENCES.values())


# Pieces of text where the parser's choices lie, which random sources put together.
PIECES = [
    "(", ")", "[", "]", "{", "}", " ", "\n", ";c\n", "'", "$'", "#'", "tex'", "doc@", "free@",
    "a", "b", "x_", "_", ".", "|", ":", "1", "-", "+", "2.5", "1/2", "/", "e", "i", "true",
    "none", "!=", "\\", "\\'", "\\n", "{{", "}}", '"', "@", "#", "$", "^", "*", "<=", "0", "{x:",
    "$'{", "}'", "[0]", "a[", ".b", "(g)", "x:y", "?", "a-", "(c_ ",
]  # fmt: skip


def test_random_sources(grammar):
    rng = random.Random(0)
    for _ in range(20000):
        body = "".join(rng.choice(PIECES) for _ in range(rng.randint(1, 16)))
        src = body if rng.random() < 0.3 else f"(f {body})"
        if src in KNOWN_DIFFERENCES:
            continue
        expected = parser_after_beads(src)
        ours = read_grammar(grammar, src)
        assert expected == ours, f"the parser and the grammar differ on {src!r}"


def test_spec_shows_every_section_once():
    sections = re.findall(r"^//: (\S+)$", GRAMMAR.read_text(encoding="utf-8"), re.M)
    shown = [
        m
        for page in sorted(SPEC.glob("*.md"))
        for m in re.findall(r"^`{3,}\{mtp-grammar\} (\S+)$", page.read_text(encoding="utf-8"), re.M)
    ]
    assert sorted(shown) == sorted(sections)


def test_corpus_is_large():
    # A wrong path would make every corpus test vanish silently.
    assert len(CORPUS) > 100
