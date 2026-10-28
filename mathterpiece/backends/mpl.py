from functools import singledispatch

import matplotlib.pyplot as plt

from mathterpiece.scene import Circle, Group, Scene, Text, VisualObj
from mathterpiece.views import Canvas, View


def render(scn: Scene) -> list[tuple[plt.Figure, plt.Axes]]:
    return [render_view(view, scn) for view in scn.views]


@singledispatch
def render_view(view: View, scn: Scene) -> tuple[plt.Figure, plt.Axes]:
    raise TypeError(f"no matplotlib renderer for {type(view).__name__}")


@render_view.register
def _(view: Canvas, scn: Scene) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots()
    ax.set_xlim(view.xmin, view.xmax)
    ax.set_ylim(view.ymin, view.ymax)
    for obj in view.members:
        draw(obj, ax, scn)
    return fig, ax


@singledispatch
def draw(obj: VisualObj, ax: plt.Axes, scn: Scene):
    raise TypeError(f"no matplotlib renderer for {type(obj).__name__}")


@draw.register
def _(obj: Circle, ax: plt.Axes, scn: Scene):
    circle = plt.Circle(
        (obj.x, obj.y),
        obj.r,
        facecolor=obj.facecolor,
        fill=obj.fill,
        edgecolor=obj.edgecolor,
        linewidth=obj.linewidth,
        alpha=obj.alpha,
    )
    ax.add_artist(circle)


@draw.register
def _(obj: Text, ax: plt.Axes, scn: Scene):
    ax.text(obj.x, obj.y, obj.val)


@draw.register
def _(obj: Group, ax: plt.Axes, scn: Scene):
    for member in obj.members:
        draw(member, ax, scn)
