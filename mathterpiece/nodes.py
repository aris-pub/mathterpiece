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
    parts: "tuple[str | Node, ...]"
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class StrLit:
    value: str
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class InterpStrLit:
    parts: tuple["str | Node | Field", ...]
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
class NoneLit:
    pos: Pos = field(default=NOPOS, compare=False)


# {expr:spec} in an interpolated string: the expression shown with a Python format spec.
@dataclass(frozen=True, slots=True)
class Field:
    expr: "Node"
    spec: str
    pos: Pos = field(default=NOPOS, compare=False)


# [a b c]: a list of values, such as a point.
@dataclass(frozen=True, slots=True)
class ListLit:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Form:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


Node = (
    Form
    | ListLit
    | StrLit
    | InterpStrLit
    | IntLit
    | RatioLit
    | RealLit
    | ComplexLit
    | BoolLit
    | NoneLit
    | Name
)
