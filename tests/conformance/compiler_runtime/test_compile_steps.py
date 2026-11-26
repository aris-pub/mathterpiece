"""Conformance tests of the rule compile-steps (docs/spec/compiler-runtime.md)."""

from ._shared import ParseError, compile_source, mtpc, obj, parse, pytest, rule


@rule("compile-steps")
class TestCompileSteps:
    def test_the_parse_step_runs_first(self):
        # The compile error comes first in the text, and the syntax error is reported.
        with pytest.raises(ParseError):
            compile_source("(real a b)\n(f 'x)")

    def test_the_parse_step_looks_up_no_name(self):
        parse("(f an-unknown-name (g))")

    def test_each_foreach_is_written_out_as_its_copies(self):
        d = mtpc("(scene s (foreach i 3 (circle @'c-{i}' (r (+ i 1)))))")
        assert [obj(d, f"c-{i}")["attrs"]["r"]["free"] for i in range(3)] == [1, 2, 3]

    def test_each_motif_instance_is_written_out(self):
        d = mtpc("(motif m ((real k 1 (>= 0))) (circle c (r k))) (scene s (m a (k 2)) (m b))")
        kinds = [o["kind"] for o in d["objects"]]
        assert kinds.count("instance") == 2 and kinds.count("circle") == 2

    def test_every_expression_known_when_compiling_is_folded(self):
        assert obj(mtpc("(real v (* 2 (+ 1 2)))"), "v")["value"]["free"] == 6
