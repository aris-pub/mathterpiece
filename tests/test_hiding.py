"""A shape or member declared inside a scene, group or motif may not take a name declared at the
top level of the file, imported names included: it would hide that name, so a read of it inside
gets the wrong thing (mtp-o89r). The error is at the declaration and names both. A let name may
still hide a top-level name."""

import pytest
from helpers import doc, error, model

from mathterpiece.compiler import CompileError, compile_source


def test_a_group_in_a_motif():
    # The case found: (stroke mark) read the group, not the color.
    error(
        "(color mark 'red')\n"
        "(motif m () (group mark (circle c (r 1))) (circle d (r 1) (stroke mark)))\n"
        "(scene s (m x))",
        r"^2:20: group 'mark' would hide the top-level color 'mark' \(1:8\)",
    )


def test_a_shape_in_a_motif_with_no_instance():
    error(
        "(color mark 'red') (motif m () (circle mark (r 1)))",
        r"circle 'mark' would hide the top-level color 'mark' \(1:8\)",
    )


def test_a_shape_in_a_group_in_a_motif():
    error(
        "(color mark 'red') (motif m () (group g (circle mark (r 1)))) (scene s (m x))",
        r"circle 'mark' would hide the top-level color 'mark'",
    )


def test_an_instance_in_a_motif():
    error(
        "(motif dot () (circle c (r 1))) (real k 1) (motif m () (dot k)) (scene s (m x))",
        r"dot 'k' would hide the top-level real 'k'",
    )


def test_a_bound_variable_in_a_motif():
    error(
        "(real k 1) (motif m ((real q 1 (>= 0))) (real k (* 2 q)) (circle c (r k)))",
        r"real 'k' would hide the top-level real 'k'",
    )


@pytest.mark.parametrize(
    "decl, what",
    [
        ("(func f ((real x)) x)", "func"),
        ("(func[real] f ((real x)) x)", "func"),
        ("(motif f () (circle c (r 1)))", "motif"),
        ("(type f real (>= 0))", "type"),
        ("(namespace f (color ink 'red'))", "namespace"),
    ],
)
def test_any_top_level_declaration(decl, what):
    error(
        f"{decl} (motif m () (circle f (r 1)))", f"circle 'f' would hide the top-level {what} 'f'"
    )


def test_a_shape_in_the_scene():
    error(
        "(color mark 'red') (scene s (circle mark (r 1)))",
        r"circle 'mark' would hide the top-level color 'mark' \(1:8\)",
    )


def test_a_shape_in_a_group_in_the_scene():
    error(
        "(color mark 'red') (scene s (group g (circle mark (r 1))))",
        r"circle 'mark' would hide the top-level color 'mark'",
    )


def test_a_variable_in_the_scene():
    error(
        "(real mark 1) (scene s (real mark 2) (circle c (r mark)))",
        r"real 'mark' would hide the top-level real 'mark'",
    )


def test_a_shape_in_a_foreach():
    error(
        "(real mark 1) (scene s (foreach i (range 3) (circle (name 'mark') (r 1))))",
        r"circle 'mark' would hide the top-level real 'mark'",
    )


def test_a_name_imported_by_name(tmp_path):
    (tmp_path / "house.mtp").write_text("(color ink '#1f2a44')\n")
    path = tmp_path / "fig.mtp"
    path.write_text("(import house ink)\n(motif m () (circle ink (r 1)))\n")
    with pytest.raises(
        CompileError, match=r"circle 'ink' would hide 'ink', imported from house.mtp \(1:15\)"
    ):
        compile_source(path.read_text(), path=path)


def test_a_motif_in_an_imported_file(tmp_path):
    (tmp_path / "house.mtp").write_text("(color ink 'red')\n(motif dot () (circle ink (r 1)))\n")
    path = tmp_path / "fig.mtp"
    path.write_text("(import house)\n(scene s (house.dot x))\n")
    with pytest.raises(
        CompileError, match=r"house.mtp:2:23: circle 'ink' would hide the top-level color 'ink'"
    ):
        compile_source(path.read_text(), path=path)


def test_a_file_whole_import_hides_nothing(tmp_path):
    (tmp_path / "house.mtp").write_text("(color ink '#1f2a44')\n")
    path = tmp_path / "fig.mtp"
    path.write_text("(import house)\n(motif m () (circle ink (r 1)))\n(scene s (m x))\n")
    compile_source(path.read_text(), path=path)


def test_the_same_name_in_two_motifs_and_the_scene():
    # Only top-level names count: a scene shape is not one.
    model(
        "(motif m () (circle c (r 1))) (motif n () (circle c (r 1)))"
        " (scene s (circle c (r 1)) (m x) (n y))"
    )


def test_a_let_may_hide_a_top_level_name():
    model("(real mark 1) (scene s (let ((mark 2)) (circle c (r mark))))")


def test_a_function_parameter_hides_a_top_level_name():
    # As in Python: inside the function, x is the parameter (the author, 2026-11-07).
    m = model("(real x 1) (func f ((real x)) (* 10 x)) (real y (f 2))")
    assert m.get("y").value.value == 20


def test_a_motif_parameter_hides_a_top_level_name():
    d = doc(
        "(real size 1) (motif m ((real size 1 (>= 0))) (circle c (r size)))"
        " (scene s (m a (size 2)))"
    )
    names = [o["name"] for o in d["objects"]]
    (c,) = [o for o in d["objects"] if o["name"] == "c"]
    # The radius reads the instance's own size, not the top-level variable.
    assert c["attrs"]["r"]["deps"] == [[names.index("a"), "size"]]
