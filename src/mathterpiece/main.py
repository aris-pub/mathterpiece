# main.py
# A LISP-y DSL for generating interactive mathematical widgets

from random import uniform
from textwrap import dedent
from abc import abstractmethod
import matplotlib.pyplot as plt
from typing import Any, Callable
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
                if not isinstance(mem, str):
                    stack.append(mem)

    def add(self, thing: Any):
        if isinstance(thing, Obj):
            self.objects.append(thing)
        elif isinstance(thing, View):
            self.views.append(thing)

    def to_dict(self):
        d: dict[str, Any] = {thing.name: thing for thing in self.objects + self.views}
        stack: list = [mem for thing in d for mem in getattr(thing, "members", [])]
        while stack:
            thing: Any = stack.pop()
            if thing in d:
                continue
            d[thing.name] = thing
            stack += getattr(thing, "members", [])
        return d

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
            for mem in members:
                if isinstance(mem, str):
                    idx = obj.members.index(mem)
                    obj.members.remove(mem)
                    obj.members.insert(idx, self[mem])


class Obj:
    def __init__(self, name:str = ""):
        self.name: str = name


class Real(Obj):
    def __init__(self, name:str = "", val: float = 0.0):
        super().__init__(name)
        self.val = val

    def __repr__(self) -> str:
        return f"Real({self.val})"


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
        self.val: str = val
        print(self.val)

    def draw(self, ax: plt.Axes, scn: Scene):
        ax.text(self.x, self.y, self.val)


class Circle(VisualObj):
    def __init__(self, name:str = "", x:float = 0.0, y:float = 0.0, r:float = 1.0):
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
            name: str,
            members:list[VisualObj] | None = None,
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

    def render(self, scn: Scene) -> tuple[plt.Figure, plt.Axes]:
        fig, ax = plt.subplots()
        ax.set_xlim(self.xmin, self.xmax)
        ax.set_ylim(self.ymin, self.ymax)
        for obj in self.members:
            obj.draw(ax, scn)
        return fig, ax


class Group(VisualObj):
    def __init__(self, name:str = "", members: list | None = None):
        super().__init__(name)
        self.members: list[VisualObj] = members or []

    def draw(self, ax: plt.Axes, scn: Scene):
        for obj in self.members:
            obj.draw(ax, scn)


class Parser:
    def __init__(self, src: str):
        self.src: str = src
        self.scn: Scene = Scene()
        self.depth: int = -1
        self.boundvars: dict = {}

    def parse_sexp(self, sexp: str, return_func=False):
        sexp = sexp.strip()
        print(" " * (2*self.depth) + f"parsing: {sexp}" + (f" {self.boundvars=}" if self.boundvars else ""))

        if sexp[0] != "(":
            # list
            if sexp[0] == "[":
                self.depth += 1
                res = []
                for ex in self.toplevel_sexps(sexp[1:-1].strip()):
                    res.append(self.parse_sexp(ex))
                self.depth -= 1
                return res

            # atom
            else:
                func = lambda: eval(sexp, locals=self.scn.to_dict() | self.boundvars)
                return func if return_func else func()

        self.depth += 1
        partial: str = sexp[1:-1]
        head, rest = self.next_sexp(partial)
        self.depth -= 1
        func = getattr(self, f"parse_{head}")(rest)
        return func if return_func else func()

    def parse_rand(self, partial:str):
        a, b = 0.0, 1.0
        if partial.strip():
            a, b = self.toplevel_sexps(partial.strip())
            a = self.parse_sexp(a)
            b = self.parse_sexp(b)
            print(a, b)

        return lambda: uniform(a, b)

    def parse_group(self, partial: str):
        name, rest = partial.split(' ', maxsplit=1)
        name: str = self.parse_sexp(name)
        members: list = self.parse_sexp(rest)
        return lambda: Group(name, members)

    def parse_canvas(self, partial: str):
        name, rest = partial.split(' ', maxsplit=1)
        name: str = self.parse_sexp(name)
        members: list = self.parse_sexp(rest)
        return lambda: Canvas(name, members)

    def parse_circle(self, partial: str):
        split: list[str] = partial.split(' ', maxsplit=1)
        name: str = self.parse_sexp(split[0])
        attrs: dict = {}
        if len(split) == 2:
            attrs = self.parse_attrs(split[1])
            for k, v in attrs.items():
                attrs[k] = self.parse_sexp(v)
        return lambda: Circle(name, **attrs)

    def parse_text(self, partial: str):
        name, partial = self.next_sexp(partial)
        name: str = self.parse_sexp(name)

        val, rest = self.next_sexp(partial)
        val: str = self.parse_sexp(val)
        while (nextval :=  getattr(val, "val", val)) != val:
            val = nextval

        attrs = self.parse_attrs(rest)
        for k, v in attrs.items():
            attrs[k] = self.parse_sexp(v)
        return lambda: Text(name, val=val, **attrs)

    def parse_mult(self, partial):
        print("PARTIAL: ", partial)

        func_list: list[Callable] = [
            self.parse_sexp(sexp, return_func=True)
            for sexp in self.toplevel_sexps(partial)
        ]

        def mult_func():
            res: float = 1
            for func in func_list:
                val = func()
                while hasattr(val, "val"):
                    val = val.val
                res *= val
            return res
        return mult_func

    def parse_attrs(self, attrs: str):
        attr_dict: dict[str, Any] = {}
        for sexp in self.toplevel_sexps(attrs):
            sexp: str = sexp.strip()[1:-1]
            attr, val = self.toplevel_sexps(sexp)
            attr_dict[attr.strip()] = val.strip()
        return attr_dict

    def parse_repeat(self, partial: str):
        var, num, sexp = partial.split(' ', maxsplit=2)
        var: str = var.strip()
        num: int = eval(num.strip())
        sexp: str = sexp.strip()

        res: list = []
        for i in range(num):
            self.boundvars[var] = i
            for ex in self.toplevel_sexps(sexp.strip()):
                res.append(self.parse_sexp(ex))
        del self.boundvars[var]
        return lambda: res

    def parse_real(self, partial: str):
        split: list[str] = partial.split(' ', maxsplit=1)
        name: str = self.parse_sexp(split[0])
        val: float = 0.0
        if len(split) == 2:
            val: float = self.parse_sexp(split[1])
        return lambda: Real(name, val)

    def next_sexp(self, src: str):
        sexp_generator = self.toplevel_sexps(src)
        first = next(sexp_generator)
        rest = " ".join(sexp for sexp in sexp_generator)
        return first, rest

    def toplevel_sexps(self, src: str):
        last: int = 0
        ptr: int = 0
        nestedness: int = 0
        while ptr < len(src):
            sexp = ""
            while ptr < len(src) and src[ptr] in " \n\t":
                ptr += 1
            if ptr == len(src):
                break

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
        print(dedent(self.src).strip())
        print()
        src: str = dedent(self.src).strip().replace("\n", " ")
        for sexp in self.toplevel_sexps(src):
            res = self.parse_sexp(sexp)
            self.scn.add(res)
        self.scn.resolve_refs()
        return self.scn


def main():
    src: str = """
    (circle 'disk')
    (canvas 'cnv' ['disk'])
    """
    src: str = """
    (group 'disks' [
      (circle 'disk0' (r 1) (x 0) (y 0))
      (circle 'disk1' (r 1) (x 1) (y 0))
      (circle 'disk2' (r 1) (x 2) (y 0))])
    (canvas 'cnv' ['disks'])
    """
    src: str = """
    (canvas 'cnv' [
      (group 'disks' [
        (circle 'disk0' (r 1) (x 0) (y 0))
        (circle 'disk1' (r 1) (x 1) (y 0))
        (circle 'disk2' (r 1) (x 2) (y 0))])])
    """
    src: str = """
    (canvas 'cnv' [
      (circle 'disk0' (r 1) (x 0) (y 0))
      (circle 'disk1' (r 1) (x 1) (y 0))
      (circle 'disk2' (r 1) (x 2) (y 0))])
    """
    src: str = """
    (group 'disks'
      (repeat i 3
        (circle f'disk{i}' (r 1) (x i) (y i))
        (text f'text{i}' f'disk{i}' (x i) (y i))))
    (canvas 'cnv' ['disks'])
    """
    src: str = """
    (circle 'disk' (r 1) (x 0) (y 0))
    (text 'lbl' disk.name (x 0) (y 0))
    (canvas 'cnv' ['disk' 'lbl'])
    """
    src: str = """
    (real 'pi' 3.1415926535)
    (text 'lbl' pi (x 0) (y 0))
    (canvas 'cnv' ['lbl'])
    """
    src: str = """
    (circle 'disk' (r 2) (x 0) (y 0))
    (real 'pi' 3.1415926535)
    (real 'area' (mult pi disk.r disk.r))
    (text 'lbl' area (x 0) (y 0))
    (canvas 'cnv' ['disk' 'lbl'])
    """
    src: str = """
    (circle 'disk' (r 2))
    (text 'lbl' (mult 3.1415926535 disk.r disk.r) (x 0) (y 0))
    (canvas 'cnv' ['disk' 'lbl'])
    """
    src: str = """
    (group 'dots'
      (repeat i 50
        (circle f'dot{i}' (r (rand 0 0.5)) (x (rand -10 10)) (y (rand -10 10)))))
    (canvas 'cnv' ['dots'])
    """
    prs: Parser = Parser(src)
    scn: Scene = prs.parse()
    scn.render()
    plt.show()


if __name__ == "__main__":
    main()
