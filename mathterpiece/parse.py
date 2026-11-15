import re
import unicodedata
from dataclasses import replace
from fractions import Fraction

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
    Node,
    NoneLit,
    Pos,
    RatioLit,
    RealLit,
    StrLit,
)

OPERATORS = frozenset({"+", "-", "*", "/", "^", "<", "<=", ">", ">=", "=", "!="})
ESCAPES = {"'": "'", "\\": "\\", "n": "\n"}
RESERVED = frozenset("[]{}")
NAME_EXCLUDED = frozenset("[]{}./;\"$^()'|@#")
NAME_BAD_START = frozenset("+-*<>=")

_UREAL = r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?"
INT_RE = re.compile(r"[+-]?\d+")
RATIO_RE = re.compile(r"([+-]?\d+)/(\d+)")
REAL_RE = re.compile(rf"[+-]?{_UREAL}")
IMAG_RE = re.compile(rf"([+-]?{_UREAL})i")
COMPLEX_RE = re.compile(rf"([+-]?{_UREAL})([+-]{_UREAL})i")
LOOKS_NUMERIC_RE = re.compile(r"[+-]?\.?\d")
BOM = "\ufeff"
WHITESPACE = " \t\n"
# Characters that unicodedata gives no name.
CONTROL_NAMES = {
    "\x0b": "vertical tab",
    "\x0c": "form feed",
    "\r": "carriage return",
    "\x85": "next line",
}


class ParseError(Exception):
    def __init__(self, msg: str, pos: Pos):
        super().__init__(f"{pos}: {msg}")
        self.msg = msg
        self.pos = pos


def parse(src: str, file: str | None = None) -> tuple[Form, ...]:
    """The forms of a source; file, for one imported, is kept in every position."""
    return _Parser(src, file).parse()


def parse_name(text: str, pos: Pos) -> Name:
    parser = _Parser(text)
    try:
        node = parser.atom() if text else None
    except ParseError:
        node = None
    if not isinstance(node, Name) or parser.peek() or node.parts[0] in OPERATORS:
        raise ParseError(f"{text!r} is not a name", pos)
    parts = tuple(p if isinstance(p, str) else _at(p, pos) for p in node.parts)
    return Name(parts, pos)


# Positions inside the string would be relative to the string, so every node gets its position.
def _at(node: Node, pos: Pos) -> Node:
    if isinstance(node, Name):
        return Name(tuple(p if isinstance(p, str) else _at(p, pos) for p in node.parts), pos)
    if isinstance(node, Form):
        return Form(tuple(_at(item, pos) for item in node.items), pos)
    if isinstance(node, InterpStrLit):
        return InterpStrLit(node.parts, pos)
    return replace(node, pos=pos)


def _is_delimiter(ch: str) -> bool:
    return ch in WHITESPACE or ch in "();"


def _ends_run(ch: str) -> bool:
    return _is_delimiter(ch) or ch in '[]{}"|'


def _shown(ch: str) -> str:
    """A character that cannot be seen, as an error message names it: U+00A0 (no-break space)."""
    name = CONTROL_NAMES.get(ch) or unicodedata.name(ch, "").lower()
    return f"U+{ord(ch):04X} ({name})" if name else f"U+{ord(ch):04X}"


def _check_char(ch: str, pos: Pos) -> None:
    """Raises for a character that may not be written in a word."""
    if ch == BOM:
        raise ParseError(
            "a byte order mark (U+FEFF) may only be the first character of a source", pos
        )
    # Python counts more characters as space than mtp does, such as U+00A0 and U+2028.
    if ch.isspace() and ch not in WHITESPACE:
        raise ParseError(
            f"{_shown(ch)} is not whitespace: whitespace is only space, tab and newline", pos
        )


def _valid_name_part(part: str) -> bool:
    if not part or part[0].isdigit() or part[0] in NAME_BAD_START or part[0] == "'":
        return False
    # An underscore may only end a form's head, as in (circle_ …), which form() takes apart.
    if "_" in part[:-1]:
        return False
    return not any(ch in NAME_EXCLUDED and ch != "'" for ch in part)


def _unnamed(head: Node) -> Node | None:
    """The head of (head_ …) without its underscore, or None if it has none."""
    if isinstance(head, Bar):
        last = _unnamed(head.items[-1])
        return None if last is None else Bar((*head.items[:-1], last), head.pos)
    if isinstance(head, Name) and isinstance(head.parts[-1], str):
        text = head.parts[-1]
        if len(text) > 1 and text.endswith("_"):
            if head.parts == ("none_",):
                return NoneLit(head.pos)
            # A motif of a file imported whole: (marks.grid_ …) is (marks.grid none …).
            return Name((*head.parts[:-1], text[:-1]), head.pos)
    return None


def _name_parts(text: str, pos: Pos) -> list[str | Node]:
    parts = text.split(".")
    if not all(_valid_name_part(part) for part in parts):
        raise ParseError(f"invalid name {text!r}", pos)
    return list(parts)


def _number(text: str, pos: Pos) -> Node | None:
    if INT_RE.fullmatch(text):
        return IntLit(int(text), pos)
    if m := RATIO_RE.fullmatch(text):
        if int(m[2]) == 0:
            raise ParseError(f"zero denominator in {text!r}", pos)
        return RatioLit(Fraction(int(m[1]), int(m[2])), pos)
    if REAL_RE.fullmatch(text):
        return RealLit(float(text), pos)
    if m := IMAG_RE.fullmatch(text):
        return ComplexLit(complex(0, float(m[1])), pos)
    if m := COMPLEX_RE.fullmatch(text):
        return ComplexLit(complex(float(m[1]), float(m[2])), pos)
    return None


class _Parser:
    def __init__(self, src: str, file: str | None = None):
        self.src = src
        self.file = file
        self.i = 0
        self.line = 1
        self.col = 1
        self.in_braces = False

    def pos(self) -> Pos:
        return Pos(self.line, self.col, self.file)

    def peek(self, offset: int = 0) -> str:
        j = self.i + offset
        return self.src[j] if j < len(self.src) else ""

    def advance(self) -> str:
        ch = self.src[self.i]
        self.i += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def skip_blank(self):
        while ch := self.peek():
            if ch in WHITESPACE:
                self.advance()
            elif ch == ";":
                while self.peek() and self.peek() != "\n":
                    self.advance()
            else:
                break

    def parse(self) -> tuple[Form, ...]:
        # The mark is skipped without moving the column, so positions count from the next character.
        if self.src.startswith(BOM):
            self.i = 1
        forms: list[Form] = []
        while True:
            self.skip_blank()
            if not self.peek():
                return tuple(forms)
            if self.peek() != "(":
                pos = self.pos()
                self.node()
                raise ParseError("expected a form at the top level", pos)
            forms.append(self.form())

    def node(self) -> Node:
        ch = self.peek()
        pos = self.pos()
        if ch == "(":
            return self.form()
        if ch == ")":
            raise ParseError("unexpected ')'", pos)
        if ch == "'":
            return self.string()
        if ch == "$":
            if self.peek(1) != "'":
                raise ParseError("'$' must be followed by a quote", pos)
            return self.interp_string()
        if ch == "#":
            if self.peek(1) != "'":
                raise ParseError("'#' starts a name string: #'dot-{k}'", pos)
            return self.name_string()
        if ch == '"':
            raise ParseError("double quotes are not allowed; use single quotes", pos)
        if ch == "[":
            return self.list_literal()
        if ch == "]":
            raise ParseError("unexpected ']'", pos)
        if ch in RESERVED:
            raise ParseError(f"{ch!r} is reserved", pos)
        if self.src.startswith("tex'", self.i):
            return self.tex_string()
        if self.prefix_end() is not None:
            return self.prefixed()
        return self.atom()

    def prefix_end(self) -> int | None:
        """Where the @ of H@X is, when the word that starts here holds one."""
        j = self.i
        while j < len(self.src) and not _ends_run(self.src[j]):
            if self.in_braces and self.src[j] == ":":
                return None
            if self.src[j] == "@":
                return j
            j += 1
        return None

    def prefixed(self) -> Form:
        """H@X, which is (H X): H a name, X any expression but another H@X."""
        pos = self.pos()
        end = self.prefix_end()
        assert end is not None
        head = self.src[self.i : end]
        while self.i < end:
            _check_char(self.peek(), self.pos())
            self.advance()
        if not head:
            raise ParseError("'@' follows the name of a head, as in r@1", pos)
        if head in OPERATORS or head in (".", "true", "false", "none") or head.endswith("_"):
            raise ParseError(f"'@' cannot follow {head!r}, only the name of a head", pos)
        name = Name(tuple(_name_parts(head, pos)), pos)
        self.advance()
        return Form((name, self.prefixed_item(head)), pos)

    def prefixed_item(self, head: str) -> Node:
        ch = self.peek()
        if not ch or ch in WHITESPACE or ch in ");]":
            raise ParseError(
                f"{head}@ is followed directly by its item, as in {head}@1", self.pos()
            )
        starts_word = ch not in "'$#[(" and not self.src.startswith("tex'", self.i)
        if starts_word and self.prefix_end() is not None:
            raise ParseError(f"a prefixed form cannot follow {head}@: write ({head} …)", self.pos())
        return self.node()

    def name_string(self) -> Node:
        """#'dot-{k}', which is (name $'dot-{k}'): the string with values filled in, read as a
        name. Parts may follow it, as they follow a name: #'dot-{k}'.pos, #'row-{i}'[0]."""
        pos = self.pos()
        # The string's own check for what follows it would refuse a part, so it is read here.
        text = self.interp_string(parts_may_follow=True)
        if all(isinstance(part, str) for part in text.parts):
            raise ParseError(
                "a name string fills values into a name: with none, write the name itself, or"
                " (name 'text')",
                pos,
            )
        whole: Node = Form((Name(("name",), pos), replace(text, pos=pos)), pos)
        while self.peek() in (".", "["):
            at = self.pos()
            if self.peek() == ".":
                self.advance()
                part_pos = self.pos()
                part = self.run()
                if not part:
                    raise ParseError("expected a name after '.'", part_pos)
                for name in _name_parts(part, part_pos):
                    whole = Form((Name((".",), at), whole, Name((name,), part_pos)), at)
            else:
                index = self.list_items()
                if len(index.items) != 1:
                    raise ParseError("brackets after a name hold one position", at)
                whole = Form((Name((".",), at), whole, index.items[0]), at)
        self.expect_delimiter()
        return whole

    def form(self) -> Form:
        pos = self.pos()
        self.advance()
        items: list[Node] = []
        while True:
            self.skip_blank()
            if not self.peek():
                raise ParseError("unclosed '('", pos)
            if self.peek() == ")":
                self.advance()
                break
            items.append(self.node())
        if self.peek() in (".", "["):
            raise ParseError("a part cannot follow a form; use (. X Y)", self.pos())
        # (head_ …) is (head none …): the form has no name.
        if items and (head := _unnamed(items[0])) is not None:
            items = [head, NoneLit(items[0].pos), *items[1:]]
        return Form(tuple(items), pos)

    # A [ that starts a value opens a list; one right after a name indexes it (see access), and
    # one right after a list too: [a b c][h] is (. [a b c] h).
    def list_literal(self) -> Node:
        whole: Node = self.list_items()
        while self.peek() == "[":
            bracket = self.pos()
            index = self.list_items()
            if len(index.items) != 1:
                raise ParseError("brackets after a list hold one position", bracket)
            whole = Form((Name((".",), bracket), whole, index.items[0]), whole.pos)
        if self.peek() and not (
            _is_delimiter(self.peek()) or self.peek() == "]" or self.ends_braces()
        ):
            _check_char(self.peek(), self.pos())
            raise ParseError(f"unexpected {self.peek()!r} after a list", self.pos())
        return whole

    def list_items(self) -> ListLit:
        pos = self.pos()
        self.advance()
        items: list[Node] = []
        while True:
            self.skip_blank()
            if not self.peek():
                raise ParseError("unclosed '['", pos)
            if self.peek() == "]":
                self.advance()
                break
            if self.peek() == ")":
                raise ParseError("expected ']' to close the list", self.pos())
            items.append(self.node())
        return ListLit(tuple(items), pos)

    def run(self) -> str:
        start = self.i
        # Inside braces, ':' starts a format spec, so it ends the name.
        while self.peek() and not _ends_run(self.peek()):
            if self.in_braces and self.peek() == ":":
                break
            _check_char(self.peek(), self.pos())
            self.advance()
        return self.src[start : self.i]

    def atom(self) -> Node:
        pos = self.pos()
        node = self.operand()
        if self.peek() != "|":
            return node
        items = [node]
        while self.peek() == "|":
            self.advance()
            if not self.peek() or _is_delimiter(self.peek()) or self.peek() in "|]":
                raise ParseError("expected a type after '|'", self.pos())
            items.append(self.operand())
        return Bar(tuple(items), pos)

    def operand(self) -> Node:
        pos = self.pos()
        text = self.run()
        if not text:
            raise ParseError(f"unexpected {self.peek()!r}", pos)
        if self.peek() == "[":
            return self.access(text, pos)
        if text in OPERATORS or text == ".":
            return Name((text,), pos)
        if text in ("true", "false"):
            return BoolLit(text == "true", pos)
        if text == "none":
            return NoneLit(pos)
        if "@" in text:
            raise ParseError("'@' follows only the name of a head, as in r@1", pos)
        if text == "_":
            raise ParseError("_ is not a name: write none, or head_ for a form with no name", pos)
        if (number := _number(text, pos)) is not None:
            return number
        if LOOKS_NUMERIC_RE.match(text):
            raise ParseError(f"invalid number {text!r}", pos)
        return Name(tuple(_name_parts(text, pos)), pos)

    def access(self, text: str, pos: Pos) -> Name:
        if text in OPERATORS or text in ("true", "false") or LOOKS_NUMERIC_RE.match(text):
            raise ParseError(f"only names can be indexed, got {text!r}", pos)
        parts = _name_parts(text, pos)
        while self.peek() == "[":
            bracket = self.pos()
            self.advance()
            self.skip_blank()
            if self.peek() == "]":
                raise ParseError("empty index", bracket)
            if not self.peek():
                raise ParseError("unclosed '['", bracket)
            items = [self.node()]
            self.skip_blank()
            while (
                self.peek()
                and self.peek() not in "])"
                and not (self.in_braces and self.peek() == "}")
            ):
                items.append(self.node())
                self.skip_blank()
            if self.peek() != "]":
                raise ParseError("expected ']' after '['", bracket)
            self.advance()
            parts.append(items[0] if len(items) == 1 else Brackets(tuple(items), bracket))
            if self.peek() == ".":
                self.advance()
                part_pos = self.pos()
                part = self.run()
                if not part:
                    raise ParseError("expected a name after '.'", part_pos)
                parts.extend(_name_parts(part, part_pos))
        ends = _ends_run(self.peek()) or (self.in_braces and self.peek() == ":")
        if self.peek() and not ends:
            _check_char(self.peek(), self.pos())
            raise ParseError(f"unexpected {self.peek()!r} after index", self.pos())
        return Name(tuple(parts), pos)

    # Inside an interpolated string's braces, a value may end at the closing brace or a format spec.
    def ends_braces(self) -> bool:
        return self.in_braces and self.peek() in "}:"

    def expect_delimiter(self):
        if self.peek() and not (
            _is_delimiter(self.peek()) or self.peek() == "]" or self.ends_braces()
        ):
            _check_char(self.peek(), self.pos())
            raise ParseError("expected whitespace, '(', ')' or ';' after a string", self.pos())

    def escape(self, start: Pos) -> str:
        pos = self.pos()
        self.advance()
        ch = self.peek()
        if not ch:
            raise ParseError("unterminated string", start)
        if ch not in ESCAPES:
            raise ParseError(f"invalid escape '\\{ch}'", pos)
        self.advance()
        return ESCAPES[ch]

    def string(self) -> StrLit:
        pos = self.pos()
        self.advance()
        chars: list[str] = []
        while True:
            ch = self.peek()
            if not ch:
                raise ParseError("unterminated string", pos)
            if ch == "'":
                self.advance()
                break
            chars.append(self.escape(pos) if ch == "\\" else self.advance())
        self.expect_delimiter()
        return StrLit("".join(chars), pos)

    def tex_string(self) -> StrLit:
        """tex'…': LaTeX, which uses backslashes everywhere, so only \\' is an escape. \\\\ is
        kept whole, so that it never escapes the quote after it."""
        pos = self.pos()
        for _ in "tex":
            self.advance()
        self.advance()
        chars: list[str] = []
        while True:
            ch = self.peek()
            if not ch:
                raise ParseError("unterminated string", pos)
            if ch == "'":
                self.advance()
                break
            if ch == "\\" and self.peek(1) == "'":
                self.advance()
            elif ch == "\\" and self.peek(1) == "\\":
                chars.append(self.advance())
            chars.append(self.advance())
        self.expect_delimiter()
        return StrLit("".join(chars), pos, tex=True)

    def interp_string(self, parts_may_follow: bool = False) -> InterpStrLit:
        """$'…', or the string of #'…': two characters open it."""
        pos = self.pos()
        self.advance()
        self.advance()
        parts: list[str | Node | Field] = []
        text: list[str] = []

        def flush():
            if text:
                parts.append("".join(text))
                text.clear()

        while True:
            ch = self.peek()
            if not ch:
                raise ParseError("unterminated string", pos)
            if ch == "'":
                self.advance()
                break
            if ch == "\\":
                text.append(self.escape(pos))
            elif ch == "{" and self.peek(1) == "{":
                self.advance()
                self.advance()
                text.append("{")
            elif ch == "}" and self.peek(1) == "}":
                self.advance()
                self.advance()
                text.append("}")
            elif ch == "}":
                raise ParseError("unmatched '}'; write '}}' for a literal brace", self.pos())
            elif ch == "{":
                flush()
                parts.append(self.interp_part())
            else:
                text.append(self.advance())
        flush()
        if not parts_may_follow:
            self.expect_delimiter()
        return InterpStrLit(tuple(parts), pos)

    def interp_part(self) -> Node | Field:
        brace = self.pos()
        self.advance()
        self.skip_blank()
        if self.peek() in ("}", ":", ""):
            raise ParseError("expected an expression inside braces", brace)
        # Inside braces, ':' ends a name, so a format spec can follow it.
        self.in_braces = True
        try:
            expr = self.node()
        finally:
            self.in_braces = False
        self.skip_blank()
        spec = None
        if self.peek() == ":":
            self.advance()
            start = self.i
            while self.peek() and self.peek() not in "{}'":
                self.advance()
            spec = self.src[start : self.i]
            if self.peek() == "{":
                raise ParseError("a format spec cannot hold braces", self.pos())
        if self.peek() != "}":
            raise ParseError("expected a single expression and '}' inside braces", brace)
        self.advance()
        return expr if spec is None else Field(expr, spec)
