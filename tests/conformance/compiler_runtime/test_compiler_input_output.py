"""Conformance tests of the rule compiler-input-output (docs/spec/compiler-runtime.md)."""

from ._shared import rule, run


@rule("compiler-input-output")
class TestCompilerInputOutput:
    def test_an_accepted_source_gives_one_mtpc(self, figure):
        assert run("compile", str(figure)) == 0
        assert [f.name for f in figure.parent.iterdir() if f.suffix == ".mtpc"] == ["dot.mtpc"]

    def test_a_rejected_source_gives_no_mtpc(self, tmp_path):
        src = tmp_path / "bad.mtp"
        src.write_text("(real a b) (real b 1)")
        assert run("compile", str(src)) != 0
        assert not any(f.suffix == ".mtpc" for f in tmp_path.iterdir())

    def test_the_compiler_reads_the_files_that_the_source_imports(self, tmp_path):
        (tmp_path / "house.mtp").write_text("(color ink #'red')")
        src = tmp_path / "fig.mtp"
        src.write_text("(import house ink)\n(scene s (circle c (fill ink)))\n(canvas v s)\n")
        assert run("compile", str(src)) == 0
