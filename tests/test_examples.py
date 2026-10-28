"""Example programs that used to be hardcoded in main(), checked against their Scene."""

import random

import pytest

from mathterpiece.parser import Parser
from mathterpiece.scene import Circle, Group, Real, Text
from mathterpiece.views import Canvas


def parse(src):
    return Parser(src).parse()


def test_single_circle():
    scn = parse("""
    (circle 'disk')
    (canvas 'cnv' ['disk'])
    """)
    disk = scn["disk"]
    assert isinstance(disk, Circle)
    assert scn.objects == [disk]
    assert isinstance(scn["cnv"], Canvas)
    assert scn["cnv"].members == [disk]


def test_group_referenced_by_canvas():
    scn = parse("""
    (group 'disks' [
      (circle 'disk0' (r 1) (x 0) (y 0))
      (circle 'disk1' (r 1) (x 1) (y 0))
      (circle 'disk2' (r 1) (x 2) (y 0))])
    (canvas 'cnv' ['disks'])
    """)
    disks = scn["disks"]
    assert isinstance(disks, Group)
    assert [d.name for d in disks.members] == ["disk0", "disk1", "disk2"]
    assert [d.x for d in disks.members] == [0, 1, 2]
    assert all(d.r == 1 and d.y == 0 for d in disks.members)
    assert scn["cnv"].members == [disks]


def test_group_defined_inside_canvas():
    scn = parse("""
    (canvas 'cnv' [
      (group 'disks' [
        (circle 'disk0' (r 1) (x 0) (y 0))
        (circle 'disk1' (r 1) (x 1) (y 0))
        (circle 'disk2' (r 1) (x 2) (y 0))])])
    """)
    assert scn.objects == []
    (disks,) = scn["cnv"].members
    assert disks.name == "disks"
    assert [d.name for d in disks.members] == ["disk0", "disk1", "disk2"]
    assert scn.to_dict()["disks"] is disks


def test_circles_defined_inside_canvas():
    scn = parse("""
    (canvas 'cnv' [
      (circle 'disk0' (r 1) (x 0) (y 0))
      (circle 'disk1' (r 1) (x 1) (y 0))
      (circle 'disk2' (r 1) (x 2) (y 0))])
    """)
    assert scn.objects == []
    assert [d.name for d in scn["cnv"].members] == ["disk0", "disk1", "disk2"]
    assert [d.x for d in scn["cnv"].members] == [0, 1, 2]


def test_repeat_in_group():
    scn = parse("""
    (group 'disks'
      (repeat i 3
        (circle f'disk{i}' (r 1) (x i) (y i))
        (text f'text{i}' f'disk{i}' (x i) (y i))))
    (canvas 'cnv' ['disks'])
    """)
    members = scn["disks"].members
    assert [type(m) for m in members] == [Circle, Text] * 3
    assert [m.name for m in members] == ["disk0", "text0", "disk1", "text1", "disk2", "text2"]
    assert [m.val for m in members if isinstance(m, Text)] == ["disk0", "disk1", "disk2"]
    assert [(m.x, m.y) for m in members] == [(0, 0), (0, 0), (1, 1), (1, 1), (2, 2), (2, 2)]


def test_text_reads_other_object_attribute():
    scn = parse("""
    (circle 'disk' (r 1) (x 0) (y 0))
    (text 'lbl' disk.name (x 0) (y 0))
    (canvas 'cnv' ['disk' 'lbl'])
    """)
    assert scn["lbl"].val == "disk"
    assert scn["cnv"].members == [scn["disk"], scn["lbl"]]


def test_text_reads_real():
    scn = parse("""
    (real 'pi' 3.1415926535)
    (text 'lbl' pi (x 0) (y 0))
    (canvas 'cnv' ['lbl'])
    """)
    assert isinstance(scn["pi"], Real)
    assert scn["pi"].val == 3.1415926535
    assert scn["lbl"].val == 3.1415926535


def test_real_computed_from_other_objects():
    scn = parse("""
    (circle 'disk' (r 2) (x 0) (y 0))
    (real 'pi' 3.1415926535)
    (real 'area' (mult pi disk.r disk.r))
    (text 'lbl' area (x 0) (y 0))
    (canvas 'cnv' ['disk' 'lbl'])
    """)
    assert scn["area"].val == pytest.approx(3.1415926535 * 4)
    assert scn["lbl"].val == scn["area"].val
    assert scn["cnv"].members == [scn["disk"], scn["lbl"]]


def test_text_value_from_inline_mult():
    scn = parse("""
    (circle 'disk' (r 2))
    (text 'lbl' (mult 3.1415926535 disk.r disk.r) (x 0) (y 0))
    (canvas 'cnv' ['disk' 'lbl'])
    """)
    assert scn["lbl"].val == pytest.approx(3.1415926535 * 4)


def test_random_dots_read_circle_color():
    random.seed(0)
    scn = parse("""
    (group 'circles' [
        (circle 'teal_c' (r 3.5) (x -5.0) (y  4.0) (edgecolor 'teal') (linewidth 1.5) (fill False))
        (circle 'red_c'  (r 1.2) (x  3.5) (y -2.0) (edgecolor 'red') (linewidth 1.5) (fill False))])
    (group 'dots'
      (repeat i 100
        (circle f'dot{i}'
          (r (rand 0 0.25)) (x (rand -10 10)) (y (rand -10 10)) (alpha 0.25)
          (facecolor teal_c.edgecolor))))
    (canvas 'cnv' ['dots' 'circles'])
    """)
    teal, red = scn["circles"].members
    assert (teal.name, teal.edgecolor, teal.fill) == ("teal_c", "teal", False)
    assert (red.name, red.edgecolor, red.fill) == ("red_c", "red", False)

    dots = scn["dots"].members
    assert len(dots) == 100
    assert [d.name for d in dots] == [f"dot{i}" for i in range(100)]
    assert all(d.facecolor == "teal" and d.alpha == 0.25 for d in dots)
    assert all(0 <= d.r <= 0.25 for d in dots)
    assert all(-10 <= d.x <= 10 and -10 <= d.y <= 10 for d in dots)
    assert scn["cnv"].members == [scn["dots"], scn["circles"]]
