import re
from fractions import Fraction

from mathterpiece.nodes import (
    BoolLit,
    ComplexLit,
    Form,
    InterpStrLit,
    IntLit,
    Name,
    Node,
    Pos,
    RatioLit,
    RealLit,
    StrLit,
)

OPERATORS = frozenset({"+", "-", "*", "/", "^", "<", "<=", ">", ">=", "=", "!="})
ESCAPES = {"'": "'", "\\": "\\", "n": "\n"}
RESERVED = frozenset("[]{}")
NAME_EXCLUDED = frozenset("[]{}./;\"$^()'")
NAME_BAD_START = frozenset("+-*<>=")

_UREAL = r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?"
INT_RE = re.compile(r"[+-]?\d+")
RATIO_RE = re.compile(r"([+-]?\d+)/(\d+)")
REAL_RE = re.compile(rf"[+-]?{_UREAL}")
IMAG_RE = re.compile(rf"([+-]?{_UREAL})i")
COMPLEX_RE = re.compile(rf"([+-]?{_UREAL})([+-]{_UREAL})i")
LOOKS_NUMERIC_RE = re.compile(r"[+-]?\.?\d")


class ParseError(Exception):
    def __init__(self, msg: str, pos: Pos):
        super().__init__(f"{pos}: {msg}")
        self.msg = msg
        self.pos = pos


def parse(src: str) -> tuple[Form, ...]:
    return _Parser(src).parse()


def _is_delimiter(ch: str) -> bool:
    return ch.isspace() or ch in "();"


def _valid_name_part(part: str) -> bool:
    if not part or part[0].isdigit() or part[0] in NAME_BAD_START or part[0] == "'":
        return False
    return not any(ch in NAME_EXCLUDED and ch != "'" for ch in part)


def _name(text: str, pos: Pos) -> Name:
    parts = tuple(text.split("."))
    if not all(_valid_name_part(part) for part in parts):
        raise ParseError(f"invalid name {text!r}", pos)
    return Name(parts, pos)


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
    def __init__(self, src: str):
        self.src = src
        self.i = 0
        self.line = 1
        self.col = 1

    def pos(self) -> Pos:
        return Pos(self.line, self.col)

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
            if ch.isspace():
                self.advance()
            elif ch == ";":
                while self.peek() and self.peek() != "\n":
                    self.advance()
            else:
                break

    def parse(self) -> tuple[Form, ...]:
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
        if ch == '"':
            raise ParseError("double quotes are not allowed; use single quotes", pos)
        if ch in RESERVED:
            raise ParseError(f"{ch!r} is reserved", pos)
        return self.atom()

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
        if not items:
            raise ParseError("empty form", pos)
        return Form(tuple(items), pos)

    def atom(self) -> Node:
        pos = self.pos()
        start = self.i
        while self.peek() and not _is_delimiter(self.peek()):
            self.advance()
        text = self.src[start : self.i]
        if text in OPERATORS:
            return Name((text,), pos)
        if text in ("true", "false"):
            return BoolLit(text == "true", pos)
        if (number := _number(text, pos)) is not None:
            return number
        if LOOKS_NUMERIC_RE.match(text):
            raise ParseError(f"invalid number {text!r}", pos)
        return _name(text, pos)

    def expect_delimiter(self):
        if self.peek() and not _is_delimiter(self.peek()):
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

    def interp_string(self) -> InterpStrLit:
        pos = self.pos()
        self.advance()
        self.advance()
        parts: list[str | Name] = []
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
                parts.append(self.interp_name())
            else:
                text.append(self.advance())
        flush()
        self.expect_delimiter()
        return InterpStrLit(tuple(parts), pos)

    def interp_name(self) -> Name:
        brace = self.pos()
        self.advance()
        while self.peek().isspace():
            self.advance()
        pos = self.pos()
        start = self.i
        while self.peek() and not self.peek().isspace() and self.peek() not in "}'":
            self.advance()
        text = self.src[start : self.i]
        while self.peek().isspace():
            self.advance()
        if self.peek() != "}":
            raise ParseError("expected a single name and '}' inside braces", brace)
        self.advance()
        if not text:
            raise ParseError("empty braces", brace)
        if text in OPERATORS or text in ("true", "false") or LOOKS_NUMERIC_RE.match(text):
            raise ParseError(f"only names are allowed inside braces, got {text!r}", pos)
        return _name(text, pos)
