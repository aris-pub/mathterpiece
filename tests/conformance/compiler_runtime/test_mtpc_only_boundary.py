"""Conformance tests of the rule mtpc-only-boundary (docs/spec/compiler-runtime.md)."""

from ._shared import FIGURE, json, mtpc, rule, run


@rule("mtpc-only-boundary")
class TestMtpcOnlyBoundary:
    def test_every_copy_and_every_instance_is_in_the_mtpc(self):
        d = mtpc("(motif m () (circle c (r 1))) (scene s (foreach i 2 (m @'a-{i}')))")
        assert [o["kind"] for o in d["objects"]].count("circle") == 2
        assert {"a-0", "a-1"} <= set(d["names"])

    def test_the_mtpc_holds_nothing_of_the_place_of_the_source(self, tmp_path):
        a = tmp_path / "one" / "fig.mtp"
        b = tmp_path / "two" / "other.mtp"
        for p in (a, b):
            p.parent.mkdir()
            p.write_text("; the opening comment\n" + FIGURE)
            assert run("compile", str(p)) == 0
        text = a.with_suffix(".mtpc").read_text()
        assert text == b.with_suffix(".mtpc").read_text()
        assert "opening comment" not in text and "one" not in json.loads(text)["names"]
