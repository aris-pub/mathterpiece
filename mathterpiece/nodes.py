from dataclasses import dataclass, field
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Pos:
    line: int
    col: int

    def __str__(self) -> str:
        return f"{self.line}:{self.col}"


NOPOS = Pos(0, 0)


@dataclass(frozen=True, slots=True)
class Name:
    parts: tuple[str, ...]
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Str:
    value: str
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class InterpStr:
    parts: tuple[str | Name, ...]
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Int:
    value: int
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Ratio:
    value: Fraction
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Real:
    value: float
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Complex:
    value: complex
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Bool:
    value: bool
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Form:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


Node = Form | Str | InterpStr | Int | Ratio | Real | Complex | Bool | Name
