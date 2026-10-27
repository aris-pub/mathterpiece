# main.py
# A LISP-y DSL for generating interactive mathematical widgets

from textwrap import dedent
from abc import abstractmethod
import matplotlib.pyplot as plt
from typing import Any
import logging

logger = logging.getLogger("mtp")
logging.basicConfig(level=logging.INFO)


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
                stack.append(mem)

    def add(self, thing: Any):
        if isinstance(thing, Obj):
            self.objects.append(thing)
        elif isinstance(thing, View):
            self.views.append(thing)

    def render(self) -> list[tuple[plt.Figure, plt.Axes]]:
        if not self.views:
            return []

        all_figs: list[tuple[plt.Figure, plt.Axes]] = []
        for view in self.views:
            fig, ax = view.render(self)
            all_figs.append((fig, ax))

        return all_figs

    def resolve_refs(self):
        things: list = self.objects + self.views
        for obj in things:
            members = getattr(obj, "members", [])
            if not members:
                continue
            for mem in members:
                if isinstance(mem, str):
                    obj.members.remove(mem)
                    obj.members.append(self[mem])


class Obj:
    def __init__(self, name:str = ""):
        self.name: str = name


class Real(Obj):
    def __init__(self, name:str = "", val: float = 0.0):
        super().__init__(name)
        self.val = val


class VisualObj(Obj):
    def __init__(self, name:str = "", x:float = 0.0, y:float = 0.0):
        super().__init__(name)
        self.x: float = x
        self.y: float = y

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"

    @abstractmethod
    def draw(self, ax: plt.Axes, scn: Scene):
        ...


class Text(VisualObj):
    def __init__(self, name:str = "", x:float = 0.0, y:float = 0.0, val:str = ""):
        super().__init__(name, x, y)
        self.val: str | Ref = val

    def draw(self, ax: plt.Axes, scn: Scene):
        ax.text(self.x, self.y, getval(self.val, scn))


class Circle(VisualObj):
    def __init__(self, name:str = "", x:float = 0.0, y:float = 0.0, r:float = 0.0):
        super().__init__(name, x, y)
        self.r: float = r

    def draw(self, ax: plt.Axes, scn: Scene):
        circle = plt.Circle((self.x, self.y), self.r, alpha=0.5)
        ax.add_artist(circle)


class View:
    def __init__(self, name: str, members:list[VisualObj] | None = None):
        self.name: str = name
        self.members:list[VisualObj] = members or []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"

    @abstractmethod
    def render(self, scn: Scene) -> tuple[plt.Figure, plt.Axes]:
        ...


class Canvas(View):
    def __init__(
            self,
            name: str, members:list[VisualObj] | None = None,
            xmin:float = -10,
            xmax:float = 10,
            ymin:float = -10,
            ymax:float = 10
    ):
        super().__init__(name, members)
        self.xmin:float = xmin
        self.xmax:float = xmax
        self.ymin:float = ymin
        self.ymax:float = ymax
        print(name, members)

    def render(self, scn: Scene) -> tuple[plt.Figure, plt.Axes]:
        fig, ax = plt.subplots()
        ax.set_xlim(self.xmin, self.xmax)
        ax.set_ylim(self.ymin, self.ymax)
        for obj in self.members:
            obj.draw(ax, scn)
        return fig, ax


class Ref:
    def __init__(self, name: str):
        self.name: str = name

    def __repr__(self) -> str:
        return f"Ref('{self.name}')"

    def resolve(self, scn: Scene):
        ids: list[str] = self.name.split(".")
        current = next(obj for obj in scn.objects if obj.name == ids[0])
        for idx in ids[1:]:
            current = getattr(current, idx)
        return current


def getval(thing: Any, scn: Scene):
    if type(thing) is Ref:
        return thing.resolve(scn)
    else:
        return thing


class Group(VisualObj):
    def __init__(self, name:str = "", members: list | None = None):
        super().__init__(name)
        self.members: list[VisualObj] = members or []
        print(name, members)

    def draw(self, ax: plt.Axes, scn: Scene):
        for obj in self.members:
            obj.draw(ax, scn)


class Parser:
    def __init__(self, src: str):
        self.src: str = src

    def parse_sexp(self, sexp, depth=0):
        sexp = sexp.strip()
        # print(" " * (2*depth) + f"parsing: {sexp}")

        if sexp[0] != "(":
            # list
            if sexp[0] == "[":
                return [self.parse_sexp(ex) for ex in self.toplevel_sexps(sexp[1:-1].strip())]

            # atom
            else:
                return eval(sexp)

        partial: str = sexp[1:-1]
        head, rest = partial.split(' ', maxsplit=1)
        head, rest = getattr(self, f"parse_{head}")(rest)
        for k, v in rest.items():
            rest[k] = self.parse_sexp(v, depth+1)
        return head(**rest)

    def parse_group(self, partial: str) -> tuple[Any, dict[str, Any]]:
        name, rest = partial.split(' ', maxsplit=1)
        return Group, {"name": name, "members": rest}

    def parse_canvas(self, partial: str) -> tuple[Any, dict[str, Any]]:
        name, rest = partial.split(' ', maxsplit=1)
        return Canvas, {"name": name, "members": rest}

    def parse_circle(self, partial: str) -> tuple[Any, dict[str, Any]]:
        name, rest = partial.split(' ', maxsplit=1)
        return Circle, {"name": name, **self.parse_attrs(rest)}

    def parse_attrs(self, attrs: str) -> dict[str, Any]:
        attr_dict: dict[str, Any] = {}
        for sexp in self.toplevel_sexps(attrs):
            attr, val = sexp.strip()[1:-1].split(" ")
            attr_dict[attr.strip()] = val.strip()
        return attr_dict

    def toplevel_sexps(self, src: str):
        last: int = 0
        ptr: int = 0
        nestedness: int = 0
        while ptr < len(src):
            sexp = ""
            while src[ptr] in " \n\t":
                ptr += 1

            # atom
            if src[ptr] != "(":
                while ptr < len(src) and src[ptr] != " ":
                    ptr += 1

            # list
            elif src[ptr] == "(":
                nestedness += 1
                ptr += 1
                while nestedness != 0:
                    if src[ptr] == "(":
                        nestedness += 1
                    elif src[ptr] == ")":
                        nestedness -= 1
                    ptr += 1

            sexp: str = src[last : ptr].strip()
            if sexp:
                yield sexp
            last = ptr

    def parse(self):
        scn = Scene()
        for sexp in self.toplevel_sexps(self.src):
            res = self.parse_sexp(sexp)
            scn.add(res)
        scn.resolve_refs()
        return scn


def main():
    src: str = """
    (group 'disks' [
      (circle 'disk-0' (r 1) (x 0) (y 0))
      (circle 'disk-1' (r 1) (x 1) (y 0))
      (circle 'disk-2' (r 1) (x 2) (y 0))])
    (canvas 'cnv' ['disks'])
    """
    # src: str = """
    # (canvas 'cnv' [
    #   (group 'disks' [
    #     (circle 'disk-0' (r 1) (x 0) (y 0))
    #     (circle 'disk-1' (r 1) (x 1) (y 0))
    #     (circle 'disk-2' (r 1) (x 2) (y 0))])])
    # """
    src = dedent(src).strip().replace("\n", " ")
    prs: Parser = Parser(src)
    scn: Scene = prs.parse()
    print(scn.views, scn.views[0].members)
    scn.render()
    plt.show()


if __name__ == "__main__":
    main()
