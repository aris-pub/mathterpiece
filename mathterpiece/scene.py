from typing import Any

from mathterpiece.views import View


class Scene:
    def __init__(self):
        self.objects: list[Obj] = []
        self.views: list[View] = []

    def __getitem__(self, name: str):
        stack: list = self.objects + self.views
        while stack:
            thing = stack.pop()
            if thing.name == name:
                return thing
            members: list = getattr(thing, "members", [])
            if not members:
                continue
            for mem in members:
                if not isinstance(mem, str):
                    stack.append(mem)

    def add(self, thing: Any):
        if isinstance(thing, Obj):
            self.objects.append(thing)
        elif isinstance(thing, View):
            self.views.append(thing)

    def to_dict(self):
        d: dict[str, Any] = {thing.name: thing for thing in self.objects + self.views}
        stack: list = [mem for thing in d.values() for mem in getattr(thing, "members", [])]
        while stack:
            thing: Any = stack.pop()
            if isinstance(thing, str) or thing.name in d:
                continue
            d[thing.name] = thing
            stack += getattr(thing, "members", [])
        return d

    def resolve_refs(self):
        things: list = self.objects + self.views
        for obj in things:
            members = getattr(obj, "members", [])
            for mem in members:
                if isinstance(mem, str):
                    idx = obj.members.index(mem)
                    obj.members.remove(mem)
                    obj.members.insert(idx, self[mem])


class Obj:
    def __init__(self, name: str = ""):
        self.name: str = name


class Real(Obj):
    def __init__(self, name: str = "", val: float = 0.0):
        super().__init__(name)
        self.val = val

    def __repr__(self) -> str:
        return f"Real({self.val})"


class VisualObj(Obj):
    def __init__(
        self,
        name: str = "",
        x: float = 0.0,
        y: float = 0.0,
        facecolor: str = "black",
        fill: bool = True,
        edgecolor: str = "black",
        linewidth: float = 1.0,
        alpha: float = 1.0,
    ):
        super().__init__(name)
        self.x: float = x
        self.y: float = y
        self.facecolor: str = facecolor
        self.fill: bool = fill
        self.edgecolor: str = edgecolor
        self.linewidth: float = linewidth
        self.alpha: float = alpha

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"


class Text(VisualObj):
    def __init__(self, name: str = "", x: float = 0.0, y: float = 0.0, val: str = ""):
        super().__init__(name, x, y)
        self.val: str = val


class Circle(VisualObj):
    def __init__(self, name: str = "", r: float = 1.0, **kwargs):
        super().__init__(name, **kwargs)
        self.r: float = r


class Group(VisualObj):
    def __init__(self, name: str = "", members: list | None = None):
        super().__init__(name)
        self.members: list[VisualObj | str] = members or []
