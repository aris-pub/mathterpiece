from dataclasses import dataclass, field
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Pos:
    line: int
    col: int
    # The file imported that the node is from, as (import file) names it; None for the file built.
    file: str | None = None

    def __str__(self) -> str:
        where = f"{self.line}:{self.col}"
        return f"{self.file}.mtp:{where}" if self.file else where


NOPOS = Pos(0, 0)


@dataclass(frozen=True, slots=True)
class Name:
    parts: "tuple[str | Node, ...]"
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class StrLit:
    value: str
    pos: Pos = field(default=NOPOS, compare=False)
    # Written $'…': LaTeX, read with no escapes but \'.
    tex: bool = False


# #'red', #'#f00': the color as #rrggbbaa, however it was written.
@dataclass(frozen=True, slots=True)
class ColorLit:
    value: str
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


# {a b c}: a list.
@dataclass(frozen=True, slots=True)
class ListLit:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


# [x y]: a point. The parser reads any number of items, as the grammar does, and the compiler
# rejects a point that has not two.
@dataclass(frozen=True, slots=True)
class PointLit:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


# a|b: the bar of type notation, such as real|none. The compiler gives it meaning.
@dataclass(frozen=True, slots=True)
class Bar:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


# [a b] right after a name, with more than one item: the inputs and result of func[real real].
@dataclass(frozen=True, slots=True)
class Brackets:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


@dataclass(frozen=True, slots=True)
class Form:
    items: tuple["Node", ...]
    pos: Pos = field(default=NOPOS, compare=False)


Node = (
    Form
    | ListLit
    | PointLit
    | StrLit
    | ColorLit
    | IntLit
    | RatioLit
    | RealLit
    | ComplexLit
    | BoolLit
    | NoneLit
    | Bar
    | Brackets
    | Name
)
