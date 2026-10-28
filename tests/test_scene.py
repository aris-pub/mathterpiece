from mathterpiece.scene import Circle, Group, Real, Scene
from mathterpiece.views import Canvas


def make_scene():
    scn = Scene()
    a, b, c = Circle("a"), Circle("b"), Circle("c")
    inner = Group("inner", [c])
    outer = Group("outer", [b, inner])
    scn.add(a)
    scn.add(outer)
    scn.add(Real("pi", 3.14))
    scn.add(Canvas("cnv", ["a", "outer"]))
    return scn


class TestAdd:
    def test_objects_and_views(self):
        scn = make_scene()
        assert [o.name for o in scn.objects] == ["a", "outer", "pi"]
        assert [v.name for v in scn.views] == ["cnv"]

    def test_ignores_other_values(self):
        scn = Scene()
        scn.add(3)
        scn.add("a")
        assert scn.objects == [] and scn.views == []


class TestGetItem:
    def test_toplevel(self):
        scn = make_scene()
        assert scn["a"].name == "a"
        assert scn["cnv"].name == "cnv"

    def test_nested(self):
        scn = make_scene()
        assert scn["b"].name == "b"
        assert scn["c"].name == "c"


class TestToDict:
    def test_toplevel_names(self):
        d = make_scene().to_dict()
        assert {"a", "outer", "pi", "cnv"} <= d.keys()

    def test_values_are_the_objects(self):
        scn = make_scene()
        d = scn.to_dict()
        assert d["a"] is scn.objects[0]

    def test_nested_names(self):
        d = make_scene().to_dict()
        assert {"b", "inner", "c"} <= d.keys()
        assert d["c"].name == "c"


class TestResolveRefs:
    def test_replaces_names_with_objects(self):
        scn = make_scene()
        scn.resolve_refs()
        cnv = scn.views[0]
        assert cnv.members[0] is scn.objects[0]
        assert cnv.members[1] is scn.objects[1]

    def test_keeps_order(self):
        scn = Scene()
        for name in ["x", "y", "z"]:
            scn.add(Circle(name))
        scn.add(Canvas("cnv", ["z", "x", "y"]))
        scn.resolve_refs()
        assert [m.name for m in scn.views[0].members] == ["z", "x", "y"]

    def test_mixed_refs_and_objects(self):
        scn = Scene()
        scn.add(Circle("x"))
        y = Circle("y")
        scn.add(Canvas("cnv", ["x", y]))
        scn.resolve_refs()
        assert [m.name for m in scn.views[0].members] == ["x", "y"]
        assert scn.views[0].members[1] is y
