"""Conformance tests of the rule compiler-same-bytes (docs/spec/compiler-runtime.md)."""

from ._shared import RAND, ROOT, os, rule, subprocess, sys


@rule("compiler-same-bytes")
class TestCompilerSameBytes:
    def test_the_same_source_gives_the_same_bytes_in_two_processes(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_text(
            RAND + "(rand-seed sd 1) (real k 1 (>= 0) (<= 2))\n"
            "(scene s (foreach i 4 (circle @'c-{i}' (r (* k (rand 0 1))) (fill #'red'))))\n"
            "(canvas v s)\n"
        )
        outs = []
        for seed in ("1", "2"):
            out = tmp_path / f"{seed}.mtpc"
            env = {**os.environ, "PYTHONHASHSEED": seed}
            subprocess.run(
                [sys.executable, "-m", "mathterpiece", "compile", str(src), "-o", str(out)],
                check=True,
                env=env,
                cwd=ROOT,
            )
            outs.append(out.read_bytes())
        assert outs[0] == outs[1]
