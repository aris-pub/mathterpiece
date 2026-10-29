import dataclasses

import pytest

from mathterpiece.matrix import IDENTITY
from mathterpiece.model import (
    Bound,
    Canvas,
    Circle,
    DuplicateNameError,
    Free,
    Group,
    Model,
    Real,
    Styled,
    Text,
    TreeError,
    View,
    Visual,
    attributes,
    variadic,
)
from mathterpiece.nodes import Form, Name

TWICE_DISK_R = Form((Name(("*",)), Name(("disk", "r"))))


class TestAttr:
    def test_free_holds_a_value(self):
        assert Free(2.0).value == 2.0

    def test_bound_holds_an_expression(self):
        assert Bound(TWICE_DISK_R).expr == TWICE_DISK_R

    def test_free_and_bound_are_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            Free(1.0).value = 2.0  # ty: ignore[invalid-assignment]
        with pytest.raises(dataclasses.FrozenInstanceError):
            Bound(TWICE_DISK_R).expr = Name(("x",))  # ty: ignore[invalid-assignment]

    def test_equality(self):
        assert Free(1.0) == Free(1.0)
        assert Free(1.0) != Free(2.0)
        assert Bound(Name(("k",))) == Bound(Name(("k",)))


class TestDefaults:
    def test_circle(self):
        c = Circle(name="disk")
        assert c.name == "disk"
        assert (c.x, c.y, c.r) == (Free(0.0), Free(0.0), Free(1.0))
        assert (c.fill, c.stroke, c.stroke_width) == (Free("black"), Free("none"), Free(1.0))
        assert (c.opacity, c.fill_opacity, c.stroke_opacity) == (Free(1.0), Free(1.0), Free(1.0))

    def test_text_has_the_shared_visual_attributes(self):
        t = Text(name="lbl")
        assert t.value == Free("")
        assert (t.x, t.y, t.fill, t.opacity) == (Free(0.0), Free(0.0), Free("black"), Free(1.0))

    def test_real(self):
        assert Real(name="k").value == Free(0.0)

    def test_group(self):
        assert Group(name="g").members == []

    def test_canvas(self):
        cnv = Canvas(name="cnv")
        assert cnv.members == []
        view = (cnv.view_x, cnv.view_y, cnv.view_width, cnv.view_height)
        assert view == (Free(-10.0), Free(-10.0), Free(20.0), Free(20.0))
        assert cnv.transform == Free(IDENTITY)

    def test_defaults_are_not_shared_between_instances(self):
        a, b = Group(name="a"), Group(name="b")
        a.members.append(Circle(name="c"))
        assert b.members == []

    def test_name_is_required(self):
        with pytest.raises(TypeError):
            Circle()  # ty: ignore[missing-argument]

    def test_fields_are_keyword_only(self):
        with pytest.raises(TypeError):
            Circle("disk")  # ty: ignore[missing-argument, too-many-positional-arguments]


class TestGivenValues:
    def test_free_value(self):
        assert Circle(name="c", r=Free(3.5)).r == Free(3.5)

    def test_bound_value(self):
        c = Circle(name="c", r=Bound(TWICE_DISK_R))
        assert c.r == Bound(TWICE_DISK_R)

    def test_attributes_can_be_replaced(self):
        c = Circle(name="c")
        c.r = Free(2.0)
        assert c.r == Free(2.0)


class TestHierarchy:
    def test_circle_and_text_are_styled(self):
        assert issubclass(Circle, Styled)
        assert issubclass(Text, Styled)

    def test_group_is_visual_but_not_styled(self):
        assert issubclass(Group, Visual)
        assert not issubclass(Group, Styled)

    def test_group_has_no_stored_visual_attributes(self):
        assert set(attributes(Group)) == {"members"}

    def test_canvas_is_a_view(self):
        assert issubclass(Canvas, View)
        assert not issubclass(Canvas, Visual)

    def test_real_is_neither_visual_nor_view(self):
        assert not issubclass(Real, Visual)
        assert not issubclass(Real, View)


class TestAttributeTable:
    def test_circle_attributes_in_order(self):
        assert list(attributes(Circle)) == [
            "x",
            "y",
            "fill",
            "stroke",
            "stroke-width",
            "opacity",
            "fill-opacity",
            "stroke-opacity",
            "r",
        ]

    def test_name_is_not_an_attribute(self):
        assert "name" not in attributes(Circle)

    def test_attributes_are_dataclass_fields(self):
        assert attributes(Circle)["r"] is next(
            f for f in dataclasses.fields(Circle) if f.name == "r"
        )

    def test_canvas_attributes(self):
        assert list(attributes(Canvas)) == [
            "view-x",
            "view-y",
            "view-width",
            "view-height",
            "transform",
            "members",
        ]

    def test_text_and_real_attributes(self):
        assert "value" in attributes(Text)
        assert Text(name="t").font_size == Free(1.0)
        assert list(attributes(Real)) == ["value"]

    @pytest.mark.parametrize("cls", [Group, Canvas])
    def test_containers_have_members_as_variadic(self, cls):
        field = variadic(cls)
        assert field is not None
        assert field.name == "members"

    @pytest.mark.parametrize("cls", [Circle, Text, Real])
    def test_non_containers_have_no_variadic(self, cls):
        assert variadic(cls) is None


def sample():
    teal = Circle(name="teal_c")
    red = Circle(name="red_c")
    circles = Group(name="circles", members=[teal, red])
    k = Real(name="k")
    cnv = Canvas(name="cnv", members=[circles])
    return teal, red, circles, k, cnv


class TestModelAdd:
    def test_lookup_by_name(self):
        scn = Model()
        disk = Circle(name="disk")
        scn.add(disk)
        assert scn["disk"] is disk
        assert "disk" in scn

    def test_missing_name_raises_key_error(self):
        with pytest.raises(KeyError):
            Model()["nope"]

    def test_missing_name_is_not_contained(self):
        assert "nope" not in Model()

    def test_iterates_in_addition_order(self):
        scn = Model()
        a, b, c = Circle(name="a"), Real(name="b"), Canvas(name="c")
        for obj in (b, c, a):
            scn.add(obj)
        assert list(scn) == [b, c, a]

    def test_len_counts_toplevel_items(self):
        teal, red, circles, k, cnv = sample()
        scn = Model()
        scn.add(circles)
        scn.add(k)
        assert len(scn) == 2

    def test_nested_members_are_indexed(self):
        teal, red, circles, k, cnv = sample()
        scn = Model()
        scn.add(circles)
        assert scn["teal_c"] is teal
        assert scn["red_c"] is red

    def test_deeply_nested_members_are_indexed(self):
        inner = Circle(name="inner")
        g = Group(name="g", members=[Group(name="h", members=[inner])])
        scn = Model()
        scn.add(g)
        assert scn["inner"] is inner
        assert scn["h"] is g.members[0]

    def test_nested_members_are_not_toplevel(self):
        teal, red, circles, k, cnv = sample()
        scn = Model()
        scn.add(circles)
        assert list(scn) == [circles]

    def test_canvas_members_come_from_the_scene(self):
        disk = Circle(name="disk")
        scn = Model()
        scn.add(disk)
        scn.add(Canvas(name="cnv", members=[disk]))
        assert scn["disk"] is disk


class TestModelViewsAndObjects:
    def test_views_and_objects_filter_in_order(self):
        scn = Model()
        a, cnv1, b, cnv2 = Circle(name="a"), Canvas(name="c1"), Real(name="b"), Canvas(name="c2")
        for obj in (a, cnv1, b, cnv2):
            scn.add(obj)
        assert scn.views == [cnv1, cnv2]
        assert scn.objects == [a, b]

    def test_views_are_in_the_index(self):
        scn = Model()
        cnv = Canvas(name="cnv")
        scn.add(cnv)
        assert scn["cnv"] is cnv

    def test_views_and_objects_are_read_only(self):
        scn = Model()
        with pytest.raises(AttributeError):
            scn.views = []  # ty: ignore[invalid-assignment]
        with pytest.raises(AttributeError):
            scn.objects = []  # ty: ignore[invalid-assignment]

    def test_changing_the_returned_list_does_not_change_the_scene(self):
        scn = Model()
        scn.add(Circle(name="a"))
        scn.objects.clear()
        assert len(scn.objects) == 1


class TestModelDuplicates:
    def test_duplicate_toplevel_name(self):
        scn = Model()
        scn.add(Circle(name="a"))
        with pytest.raises(DuplicateNameError):
            scn.add(Real(name="a"))

    def test_duplicate_with_nested_name(self):
        scn = Model()
        scn.add(Group(name="g", members=[Circle(name="a")]))
        with pytest.raises(DuplicateNameError):
            scn.add(Circle(name="a"))

    def test_duplicate_inside_one_tree(self):
        g = Group(name="g", members=[Circle(name="a"), Circle(name="a")])
        with pytest.raises(DuplicateNameError):
            Model().add(g)

    def test_failed_add_changes_nothing(self):
        scn = Model()
        scn.add(Circle(name="a"))
        with pytest.raises(DuplicateNameError):
            scn.add(Group(name="g", members=[Circle(name="b"), Circle(name="a")]))
        assert list(scn) == [scn["a"]]
        assert "g" not in scn
        assert "b" not in scn

    def test_same_object_in_canvas_and_toplevel(self):
        disk = Circle(name="disk")
        scn = Model()
        scn.add(disk)
        scn.add(Canvas(name="cnv", members=[disk]))
        assert scn["disk"] is disk
        assert list(scn) == [disk, scn["cnv"]]

    def test_same_object_in_a_group_and_a_canvas(self):
        disk = Circle(name="disk")
        scn = Model()
        scn.add(Group(name="g", members=[disk]))
        scn.add(Canvas(name="cnv", members=[disk]))
        assert scn["disk"] is disk

    def test_adding_the_same_toplevel_object_twice(self):
        disk = Circle(name="disk")
        scn = Model()
        scn.add(disk)
        with pytest.raises(TreeError):
            scn.add(disk)

    def test_error_names_the_duplicate(self):
        scn = Model()
        scn.add(Circle(name="teal_c"))
        with pytest.raises(DuplicateNameError, match="teal_c"):
            scn.add(Circle(name="teal_c"))


class TestModelTree:
    def test_object_in_two_groups(self):
        disk = Circle(name="disk")
        scn = Model()
        scn.add(Group(name="g", members=[disk]))
        with pytest.raises(TreeError, match="disk"):
            scn.add(Group(name="h", members=[disk]))

    def test_toplevel_object_in_a_group(self):
        disk = Circle(name="disk")
        scn = Model()
        scn.add(disk)
        with pytest.raises(TreeError, match="disk"):
            scn.add(Group(name="g", members=[disk]))

    def test_object_twice_in_one_group(self):
        disk = Circle(name="disk")
        with pytest.raises(TreeError):
            Model().add(Group(name="g", members=[disk, disk]))

    def test_anonymous_object_in_two_groups(self):
        dot = Circle(name=None)
        scn = Model()
        scn.add(Group(name="g", members=[dot]))
        with pytest.raises(TreeError):
            scn.add(Group(name="h", members=[dot]))

    def test_two_canvases_show_the_same_object(self):
        disk = Circle(name="disk")
        scn = Model()
        scn.add(disk)
        scn.add(Canvas(name="a", members=[disk]))
        scn.add(Canvas(name="b", members=[disk]))
        assert scn.views == [scn["a"], scn["b"]]

    def test_canvas_shows_an_object_and_its_group(self):
        disk = Circle(name="disk")
        g = Group(name="g", members=[disk])
        scn = Model()
        scn.add(g)
        scn.add(Canvas(name="cnv", members=[disk, g]))
        assert len(scn) == 2

    @pytest.mark.parametrize("name", ["disk", None])
    def test_canvas_cannot_show_an_object_outside_the_scene(self, name):
        with pytest.raises(TreeError):
            Model().add(Canvas(name="cnv", members=[Circle(name=name)]))

    def test_failed_add_changes_nothing(self):
        disk = Circle(name="disk")
        scn = Model()
        scn.add(Group(name="g", members=[disk]))
        with pytest.raises(TreeError):
            scn.add(Group(name="h", members=[Circle(name="other"), disk]))
        assert "h" not in scn
        assert "other" not in scn


class TestModelAlias:
    def test_alias_points_to_the_same_object(self):
        scn = Model()
        pi = Real(name="pi", value=Free(3.141592653589793))
        scn.add(pi)
        scn.alias("π", "pi")
        assert scn["π"] is pi
        assert "π" in scn

    def test_alias_does_not_add_a_toplevel_item(self):
        scn = Model()
        scn.add(Real(name="pi"))
        scn.alias("π", "pi")
        assert len(scn) == 1
        assert scn.objects == [scn["pi"]]

    def test_alias_of_a_nested_object(self):
        scn = Model()
        scn.add(Group(name="g", members=[Circle(name="a")]))
        scn.alias("b", "a")
        assert scn["b"] is scn["a"]

    def test_alias_to_missing_name(self):
        with pytest.raises(KeyError):
            Model().alias("π", "pi")

    def test_alias_name_already_taken(self):
        scn = Model()
        scn.add(Real(name="pi"))
        scn.add(Real(name="tau"))
        with pytest.raises(DuplicateNameError):
            scn.alias("tau", "pi")

    def test_adding_an_object_with_an_alias_name(self):
        scn = Model()
        scn.add(Real(name="pi"))
        scn.alias("π", "pi")
        with pytest.raises(DuplicateNameError):
            scn.add(Real(name="π"))


class TestAnonymous:
    def test_anonymous_object_has_no_name(self):
        assert Circle(name=None).name is None

    def test_anonymous_toplevel_object_is_kept_in_order(self):
        scn = Model()
        anon = Circle(name=None)
        scn.add(Circle(name="a"))
        scn.add(anon)
        assert list(scn)[1] is anon

    def test_anonymous_objects_are_not_indexed(self):
        scn = Model()
        scn.add(Circle(name=None))
        scn.add(Circle(name=None))
        assert len(scn) == 2

    def test_anonymous_member_reachable_by_position(self):
        anon = Circle(name=None)
        g = Group(name="g", members=[anon, Circle(name="b")])
        scn = Model()
        scn.add(g)
        group = scn["g"]
        assert isinstance(group, Group)
        assert group.members[0] is anon
        assert scn["b"] is g.members[1]

    def test_named_members_of_anonymous_group_are_indexed(self):
        a = Circle(name="a")
        scn = Model()
        scn.add(Group(name=None, members=[a]))
        assert scn["a"] is a
