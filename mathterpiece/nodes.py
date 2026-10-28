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
class StrLit:
    value: str
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class InterpStrLit:
    parts: tuple[str | Name, ...]
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class IntLit:
    value: int
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class RatioLit:
    value: Fraction
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class RealLit:
    value: float
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class ComplexLit:
    value: complex
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class BoolLit:
    value: bool
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Form:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


Node = Form | StrLit | InterpStrLit | IntLit | RatioLit | RealLit | ComplexLit | BoolLit | Name
