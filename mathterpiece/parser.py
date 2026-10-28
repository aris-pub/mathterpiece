import logging
from collections.abc import Callable
from random import uniform
from textwrap import dedent
from typing import Any

from mathterpiece.log import TRACE
from mathterpiece.scene import Circle, Group, Real, Scene, Text
from mathterpiece.sexp import next_sexp, toplevel_sexps
from mathterpiece.views import Canvas

logger = logging.getLogger(__name__)


class Parser:
    def __init__(self, src: str):
        self.src: str = src
        self.scn: Scene = Scene()
        self.depth: int = -1
        self.boundvars: dict = {}

    def parse_sexp(self, sexp: str, return_func=False):
        sexp = sexp.strip()
        logger.log(
            TRACE,
            "%sparsing: %s%s",
            " " * (2 * self.depth),
            sexp,
            f" {self.boundvars=}" if self.boundvars else "",
        )

        if sexp[0] != "(":
            # list
            if sexp[0] == "[":
                self.depth += 1
                res = []
                for ex in toplevel_sexps(sexp[1:-1].strip()):
                    res.append(self.parse_sexp(ex))
                self.depth -= 1
                return res

            # atom
            else:

                def func():
                    return eval(sexp, locals=self.scn.to_dict() | self.boundvars)

                return func if return_func else func()

        self.depth += 1
        partial: str = sexp[1:-1]
        head, rest = next_sexp(partial)
        self.depth -= 1
        func = getattr(self, f"parse_{head}")(rest)
        return func if return_func else func()

    def parse_rand(self, partial: str):
        a, b = 0.0, 1.0
        if partial.strip():
            a, b = toplevel_sexps(partial.strip())
            a = self.parse_sexp(a)
            b = self.parse_sexp(b)
        return lambda: uniform(a, b)

    def parse_group(self, partial: str):
        name, rest = partial.split(" ", maxsplit=1)
        name: str = self.parse_sexp(name)
        members: list = self.parse_sexp(rest)
        return lambda: Group(name, members)

    def parse_canvas(self, partial: str):
        name, rest = partial.split(" ", maxsplit=1)
        name: str = self.parse_sexp(name)
        members: list = self.parse_sexp(rest)
        return lambda: Canvas(name, members)

    def parse_circle(self, partial: str):
        split: list[str] = partial.split(" ", maxsplit=1)
        name: str = self.parse_sexp(split[0])
        attrs: dict = {}
        if len(split) == 2:
            attrs = self.parse_attrs(split[1])
            for k, v in attrs.items():
                attrs[k] = self.parse_sexp(v)
        return lambda: Circle(name, **attrs)

    def parse_text(self, partial: str):
        name, partial = next_sexp(partial)
        name: str = self.parse_sexp(name)

        val, rest = next_sexp(partial)
        val: str = self.parse_sexp(val)
        while (nextval := getattr(val, "val", val)) != val:
            val = nextval

        attrs = self.parse_attrs(rest)
        for k, v in attrs.items():
            attrs[k] = self.parse_sexp(v)
        return lambda: Text(name, val=val, **attrs)

    def parse_mult(self, partial):
        func_list: list[Callable] = [
            self.parse_sexp(sexp, return_func=True) for sexp in toplevel_sexps(partial)
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
        for sexp in toplevel_sexps(attrs):
            sexp: str = sexp.strip()[1:-1]
            attr, val = toplevel_sexps(sexp)
            attr_dict[attr.strip()] = val.strip()
        return attr_dict

    def parse_repeat(self, partial: str):
        var, num, sexp = partial.split(" ", maxsplit=2)
        var: str = var.strip()
        num: int = eval(num.strip())
        sexp: str = sexp.strip()

        res: list = []
        for i in range(num):
            self.boundvars[var] = i
            for ex in toplevel_sexps(sexp.strip()):
                res.append(self.parse_sexp(ex))
        self.boundvars.pop(var, None)
        return lambda: res

    def parse_real(self, partial: str):
        split: list[str] = partial.split(" ", maxsplit=1)
        name: str = self.parse_sexp(split[0])
        val: float = 0.0
        if len(split) == 2:
            val: float = self.parse_sexp(split[1])
        return lambda: Real(name, val)

    def parse(self):
        logger.debug("source:\n%s", dedent(self.src).strip())
        src: str = dedent(self.src).strip().replace("\n", " ")
        for sexp in toplevel_sexps(src):
            res = self.parse_sexp(sexp)
            logger.debug("added %r", res)
            self.scn.add(res)
        self.scn.resolve_refs()
        return self.scn
