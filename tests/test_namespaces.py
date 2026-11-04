"""Namespaces (mtp-4rc): (namespace theme (color ink '#1f2a44') (real gap 0.4)) declares one
name, theme, a mutable object that is not drawn, whose members are read and written as
attributes are, theme.ink like c.r. The author, 2026-11-04: it holds values of any type, free or
bound, and other namespaces (colors.tab10.blue); its members read each other by bare name inside
it; writers may write its free members by its own name."""

import json

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.mtpc import write


def reads(m, name, attr="r"):
    """The variable a circle's attribute is bound to, by its name."""
    e = m.get(name).attrs[attr].expr
    assert e is not None and e.op == "read"
    return m.objects[e.args[0]].name


THEME = "(namespace theme (color ink '#1f2a44') (color paper '#f6f1e7') (real gap 0.4 (>= 0)))"


class TestDeclaring:
    def test_members_are_read_through_it(self):
        m = model(f"{THEME} (scene s (circle c (r theme.gap) (fill theme.ink)))")
        assert reads(m, "c") == "theme.gap"
        assert reads(m, "c", "fill") == "theme.ink"

    def test_it_adds_one_name(self):
        error(f"{THEME} (real v gap)", "unknown name 'gap'")

    def test_members_read_each_other_by_bare_name(self):
        m = model(
            "(namespace theme (real gap 0.4 (>= 0)) (real double (* 2 gap)))"
            " (scene s (circle c (r theme.double)))"
        )
        double = m.objects[m.names["theme.double"]].value.expr
        assert m.objects[double.args[1].args[0]].name == "theme.gap"
        m = model(
            "(namespace theme (color ink 'navy') (color paper 'white')"
            " (color soft (mix ink paper 0.5))) (scene s (circle c (fill theme.soft)))"
        )
        assert m.get("c").attrs["fill"].bound

    def test_a_member_wins_over_a_name_outside(self):
        m = model(
            "(real gap 9) (namespace theme (real gap 0.4) (real double (* 2 gap)))"
            " (real v theme.double)"
        )
        double = m.objects[m.names["theme.double"]].value.expr
        assert m.objects[double.args[1].args[0]].name == "theme.gap"

    def test_namespaces_nest(self):
        m = model(
            "(namespace colors (namespace tab10 (color blue '#1f77b4') (color orange '#ff7f0e')))"
            " (scene s (circle c (fill colors.tab10.blue)))"
        )
        assert m.get("c").attrs["fill"].bound

    def test_values_of_any_type(self):
        model(
            "(namespace n (real a 1) (int b 2) (point p [1 2]) (list[real] xs [1 2 3])"
            " (bool on true) (string s 'hi') (font label (size 14)))"
            " (scene s (circle c (pos n.p)))"
        )

    def test_only_values(self):
        error("(namespace n (func f ((real x)) x))", "a namespace holds values")
        error("(namespace n (type unit real (>= 0)))", "a namespace holds values")
        error("(namespace n (scene s))", "a namespace holds values")

    def test_a_member_it_does_not_have(self):
        error(f"{THEME} (real v theme.size)", "theme has no member 'size'")

    def test_two_members_of_the_same_name(self):
        error("(namespace n (real a 1) (real a 2))", "'a' is already declared")

    def test_only_at_the_top_level(self):
        error("(scene s (namespace n (real a 1)))", "a namespace is declared at the top level")

    def test_it_is_not_a_number(self):
        error(f"{THEME} (real v theme)", "expected real")


class TestWriting:
    def test_a_free_member(self):
        model(
            f"{THEME} (scene s (circle c (r theme.gap)))"
            " (slider sl (move theme.gap (from 0) (to 1)))"
        )

    def test_a_nested_member(self):
        model(
            "(namespace a (namespace b (real k 1 (>= 0)))) (scene s (circle c (r a.b.k)))"
            " (slider sl (move a.b.k (from 0) (to 2)))"
        )

    def test_not_a_token(self):
        error(f"{THEME} (button b (animation (move theme.ink (to 'red') (duration 1))))", "token")

    def test_not_a_bound_or_const_member(self):
        error(
            "(namespace n (real a 1) (real b (* 2 a))) (slider sl (move n.b (from 0) (to 1)))",
            "bound",
        )
        error("(namespace n (real a 1 (const))) (slider sl (move n.a (from 0) (to 2)))", "const")

    def test_not_the_namespace_itself(self):
        error(f"{THEME} (slider sl (move theme (from 0) (to 1)))", "theme is not a variable")


class TestImported:
    def files(self, tmp_path, fig):
        (tmp_path / "house.mtp").write_text(THEME)
        path = tmp_path / "fig.mtp"
        path.write_text(fig)
        return compile_source(fig, path=path)

    def test_the_file_whole(self, tmp_path):
        m = self.files(tmp_path, "(import house) (scene s (circle c (r house.theme.gap)))")
        assert reads(m, "c") == "house.theme.gap"

    def test_by_name(self, tmp_path):
        m = self.files(tmp_path, "(import house theme) (scene s (circle c (r theme.gap)))")
        assert reads(m, "c") == "house.theme.gap"


class TestWritten:
    def test_the_compiled_file(self):
        src = f"{THEME} (scene s (circle c (r theme.gap) (fill theme.ink)))"
        d = doc(src)
        assert errors(d) == []
        ns = d["objects"][d["names"]["theme"]]
        assert ns["kind"] == "namespace"
        members = {d["objects"][m]["name"]: d["objects"][m] for m in ns["members"]}
        assert set(members) == {"theme.ink", "theme.paper", "theme.gap"}
        # A color member is a token, named by the namespace: --mtp-theme-ink.
        assert members["theme.ink"]["token"] is True

    def test_nested(self):
        d = json.loads(
            write(
                compile_source(
                    "(namespace colors (namespace tab10 (color blue '#1f77b4')))"
                    " (scene s (circle c (fill colors.tab10.blue)))"
                )
            )
        )
        assert errors(d) == []
        assert "colors.tab10.blue" in {o["name"] for o in d["objects"]}

    @pytest.mark.parametrize("src", [THEME, "(namespace n)"])
    def test_with_no_use(self, src):
        assert errors(doc(src)) == []
