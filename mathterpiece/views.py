from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mathterpiece.scene import VisualObj


class View:
    def __init__(self, name: str, members: list[VisualObj | str] | None = None):
        self.name: str = name
        self.members: list[VisualObj | str] = members or []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"


class Canvas(View):
    def __init__(
        self,
        name: str,
        members: list[VisualObj | str] | None = None,
        xmin: float = -10,
        xmax: float = 10,
        ymin: float = -10,
        ymax: float = 10,
    ):
        super().__init__(name, members)
        self.xmin: float = xmin
        self.xmax: float = xmax
        self.ymin: float = ymin
        self.ymax: float = ymax
