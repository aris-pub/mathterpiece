import pytest

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import Canvas, Circle, Group, Real, Root
from mathterpiece.nodes import Pos
from mathterpiece.parse import parse


def compiled(src):
    return compile_model(parse(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match) as exc:
        compiled(src)
    return exc.value


class TestSceneForm:
    def test_empty_anonymous_scene(self):
        scn = compiled("(scene _)")
        assert isinstance(scn.root, Root)
        assert scn.root.name is None
        assert scn.root.members == []

    def test_named_scene(self):
        scn = compiled("(scene 'world' (circle 'disk'))")
        assert scn["world"] is scn.root
        assert scn.root.members == [scn["disk"]]

    def test_members_are_drawn_in_order(self):
        scn = compiled("(scene _ (circle 'a') (group 'g' (circle 'b')) (text 't' 'hi'))")
        assert [m.name for m in scn.root.members] == ["a", "g", "t"]

    def test_names_inside_are_bare_everywhere(self):
        scn = compiled("(scene 'world' (circle 'disk')) (real 'k' disk.r) (canvas 'cnv' disk)")
        cnv = scn["cnv"]
        assert isinstance(cnv, Canvas)
        assert cnv.members == [scn["disk"]]
        assert isinstance(scn["k"], Real)

    def test_canvas_shows_the_whole_scene(self):
        scn = compiled("(scene 'world' (circle 'a')) (canvas 'cnv' world)")
        cnv = scn["cnv"]
        assert isinstance(cnv, Canvas)
        assert cnv.members == [scn.root]

    def test_reals_before_and_after(self):
        scn = compiled(
            "(real 'k' 2) (scene _ (circle 'a' (r k)) (circle 'b')) (real 'd' (dist a b))"
        )
        assert isinstance(scn["d"], Real)
        assert isinstance(scn["a"], Circle)

    def test_referencing_a_scene_member_in_a_group_moves_it(self):
        scn = compiled("(scene _ (circle 'a') (group 'g' a))")
        g = scn["g"]
        assert isinstance(g, Group)
        assert scn.root.members == [g]
        assert g.members == [scn["a"]]

    def test_repeat_inside(self):
        scn = compiled("(scene _ (repeat 3 i (circle $'c{i}')))")
        assert len(scn.root.members) == 3

    def test_motif_instances_inside(self):
        scn = compiled("(motif 'dot' (circle 'c')) (scene _ (dot 'd'))")
        assert scn.root.members == [scn["d"]]

    def test_top_level_order_puts_the_root_with_the_objects(self):
        scn = compiled("(real 'k') (scene 'world') (canvas 'cnv')")
        assert [o.name for o in scn if o.name in ("k", "world", "cnv")] == ["k", "world", "cnv"]


class TestSceneFormErrors:
    def test_a_file_needs_a_scene(self):
        error("(real 'k')", match="scene")

    def test_an_empty_file_needs_a_scene(self):
        error("", match="scene")

    def test_only_one_scene(self):
        err = error("(scene _)\n(scene _)", match="one scene")
        assert err.pos == Pos(2, 1)

    @pytest.mark.parametrize(
        "src",
        [
            "(circle 'a') (scene _)",
            "(scene _) (text 't' 'hi')",
            "(scene _) (group 'g')",
            "(motif 'dot' (circle 'c')) (dot 'd') (scene _)",
            "(scene _) (repeat 2 i (circle _))",
        ],
    )
    def test_visual_objects_go_inside_the_scene(self, src):
        error(src, match="inside the scene")

    @pytest.mark.parametrize(
        "member, match",
        [
            ("(real 'k')", "outside the scene"),
            ("(canvas 'cnv')", "outside the scene"),
            ("(motif 'dot' (circle 'c'))", "top level"),
            ("(scene _)", "one scene"),
            ("(r 2)", None),
            ("2", None),
        ],
    )
    def test_not_allowed_inside(self, member, match):
        error(f"(scene _ {member})", match=match)

    def test_scene_takes_no_attributes(self):
        error("(scene _ (x 2))")

    def test_name_is_a_string_or_underscore(self):
        error("(scene world)")
        error("(scene)")

    def test_no_forward_references_to_the_scene(self):
        error("(canvas 'cnv' world) (scene 'world')", match="world")

    def test_canvas_cannot_define_visual_objects(self):
        error("(scene _) (canvas 'cnv' (circle 'a'))", match="scene")

    def test_names_inside_must_be_unique(self):
        error("(scene _ (circle 'a') (group 'g' (circle 'a')))", match="'a'")

    def test_scene_name_is_checked_against_names_inside(self):
        error("(scene 'world' (circle 'world'))", match="world")
