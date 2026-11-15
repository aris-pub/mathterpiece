"""Conformance tests for docs/spec/compiler-runtime.md.

What only the runtime can show is in web/test/conformance/compiler-runtime.test.ts."""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from mtpc_check import errors as schema_errors

from mathterpiece.cli import main
from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.mtpc import VERSION
from mathterpiece.parse import ParseError, parse

from .support import (
    REJECTION,
    ROOT,
    SPEC,
    accepted,
    compile_error,
    in_folder,
    mtpc,
    obj,
    raw_mtpc,
    syntax_error,
)

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


LABEL = xfail("mtp-ydd4.7.53", "an error carries no label of a rule")
STEPS = xfail("mtp-08wd.1", "each copy of a foreach is proved with the value of its variable")
NOT_WRITTEN = xfail("mtp-vrzc", "a folder that cannot be written prints a Python traceback")
SERVE_IMPORTS = xfail("mtp-q02m", "mtp serve compares only the modification time of the source")
NEEDS_PNPM = pytest.mark.skipif(shutil.which("pnpm") is None, reason="pnpm is not installed")

FIGURE = "(real k 1 (>= 0) (<= 2))\n(scene s (circle c (r k)))\n(canvas v s)\n"


def run(*args: str):
    """Runs the mtp command, and gives its exit status."""
    try:
        main(list(args))
    except SystemExit as e:
        return e.code
    return 0


@pytest.fixture
def figure(tmp_path):
    src = tmp_path / "dot.mtp"
    src.write_text(FIGURE)
    return src


@rule("compile-steps")
class TestCompileSteps:
    def test_the_parse_step_runs_first(self):
        # The compile error comes first in the text, and the syntax error is reported.
        with pytest.raises(ParseError):
            compile_source("(real a b)\n(f 'x)")

    def test_the_parse_step_looks_up_no_name(self):
        parse("(f an-unknown-name (g))")

    def test_each_foreach_is_written_out_as_its_copies(self):
        d = mtpc("(scene s (foreach i 3 (circle #'c-{i}' (r (+ i 1)))))")
        assert [obj(d, f"c-{i}")["attrs"]["r"]["free"] for i in range(3)] == [1, 2, 3]

    def test_each_motif_instance_is_written_out(self):
        d = mtpc("(motif m ((real k 1 (>= 0))) (circle c (r k))) (scene s (m a (k 2)) (m b))")
        kinds = [o["kind"] for o in d["objects"]]
        assert kinds.count("instance") == 2 and kinds.count("circle") == 2

    def test_every_expression_known_when_compiling_is_folded(self):
        assert obj(mtpc("(real v (* 2 (+ 1 2)))"), "v")["value"]["free"] == 6


@rule("prove-bodies-once")
class TestProveBodiesOnce:
    def test_a_motif_body_is_proved_for_every_value_of_its_parameters(self):
        compile_error("(motif dot ((real k)) (circle_ (r (/ 1 k))))")

    def test_a_constraint_leaves_out_the_other_values(self):
        accepted("(motif dot ((real k 1 (>= 1))) (circle_ (r (/ 1 k))))")

    def test_a_function_body_is_proved_with_no_call(self):
        compile_error("(func[real] f ((real x)) (/ 1 x))")

    def test_an_imported_motif_is_proved_in_its_file(self, tmp_path):
        lib = {"lib.mtp": "(motif dot ((real k)) (circle_ (r (/ 1 k))))\n"}
        with pytest.raises(REJECTION):
            in_folder(tmp_path, lib, "(import lib)\n")

    @STEPS
    def test_a_foreach_body_is_proved_once_for_its_range(self):
        accepted("(scene s (foreach i 3 (circle_ (r (or? (/ 1 i) 1)))))")


@rule("step-rejects-or-passes")
class TestStepRejectsOrPasses:
    def test_the_parse_step_rejects_with_a_syntax_error(self):
        syntax_error("(real k")

    def test_a_later_step_rejects_with_a_compile_error(self):
        compile_error("(real k j)")

    @pytest.mark.parametrize(
        "src",
        [
            FIGURE,
            "(rand-seed s 1) (real v (rand))",
            "(real k 0) (button b (animation (move k (to 1) (duration 1))))",
        ],
    )
    def test_an_accepted_source_gives_a_valid_mtpc(self, src):
        assert schema_errors(raw_mtpc(src)) == []


@rule("prover-finds-ranges")
class TestProverFindsRanges:
    @pytest.mark.parametrize("src", ["(scene s (circle c (r (- 1 2))))", "(real v (/ 1 0))"])
    def test_a_range_outside_the_constraint(self, src):
        compile_error(src)

    def test_a_range_inside_the_constraint(self):
        accepted("(real k 1 (>= 0) (<= 2)) (scene s (circle c (r (* 2 k))))")

    def test_a_bound_value_whose_range_may_break_its_constraint_gets_a_check(self):
        d = mtpc("(real k 1 (>= 0) (<= 2)) (real|none v (* 2 k) (<= 3))")
        assert obj(d, "v")["value"]["bound"][0] == "check"

    def test_a_bound_value_whose_range_lies_inside_gets_no_check(self):
        d = mtpc("(real k 1 (>= 0) (<= 1)) (real|none v (* 2 k) (<= 3))")
        assert obj(d, "v")["value"]["bound"][0] != "check"


@rule("subcommands")
class TestSubcommands:
    def test_parse_prints_and_writes_no_file(self, figure, capsys):
        assert run("parse", str(figure)) == 0
        assert capsys.readouterr().out
        assert sorted(p.name for p in figure.parent.iterdir()) == ["dot.mtp"]

    def test_check_prints_no_errors_and_writes_no_file(self, figure, capsys):
        assert run("check", str(figure)) == 0
        assert capsys.readouterr().out == f"{figure}: no errors\n"
        assert sorted(p.name for p in figure.parent.iterdir()) == ["dot.mtp"]

    def test_compile_writes_the_mtpc(self, figure):
        assert run("compile", str(figure)) == 0
        assert (figure.parent / "dot.mtpc").exists()

    @NEEDS_PNPM
    def test_build_writes_the_folder(self, figure):
        assert run("build", str(figure)) == 0
        assert (figure.parent / "build_dot").is_dir()

    def test_fmt_writes_the_file_itself(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_text("(real k  1)\n")
        assert run("fmt", str(src)) == 0
        assert sorted(p.name for p in tmp_path.iterdir()) == ["f.mtp"]

    @pytest.mark.parametrize("flag", ["-v", "-vv", "-vvv"])
    @pytest.mark.parametrize("command", ["parse", "check", "compile", "fmt"])
    def test_every_subcommand_takes_v(self, figure, command, flag):
        assert run(command, str(figure), flag) == 0

    @pytest.mark.parametrize("command", ["parse", "check", "compile", "build", "serve", "fmt"])
    def test_each_subcommand_takes_one_file(self, figure, command):
        assert run(command, str(figure), str(figure)) != 0
        assert run(command) != 0


@rule("command-errors")
class TestCommandErrors:
    @pytest.mark.parametrize("command", ["check", "compile", "build"])
    def test_a_rejected_source(self, tmp_path, command, capsys):
        src = tmp_path / "bad.mtp"
        src.write_text("(real k (* 2 j))\n")
        assert run(command, str(src)) == 1
        assert capsys.readouterr().err
        assert sorted(p.name for p in tmp_path.iterdir()) == ["bad.mtp"]

    @pytest.mark.parametrize("command", ["parse", "check", "compile", "build", "fmt"])
    def test_a_file_that_cannot_be_read(self, tmp_path, command, capsys):
        assert run(command, str(tmp_path / "missing.mtp")) == 1
        assert len(capsys.readouterr().err.strip().splitlines()) == 1
        assert list(tmp_path.iterdir()) == []

    def test_a_folder_given_as_the_file(self, tmp_path, capsys):
        assert run("compile", str(tmp_path)) == 1
        assert len(capsys.readouterr().err.strip().splitlines()) == 1

    def test_a_file_that_is_not_utf8(self, tmp_path, capsys):
        src = tmp_path / "f.mtp"
        src.write_bytes(b"(real k 1) ; \xff\n")
        assert run("compile", str(src)) == 1
        assert len(capsys.readouterr().err.strip().splitlines()) == 1

    @NOT_WRITTEN
    def test_a_file_that_cannot_be_written(self, figure, capsys):
        blocker = figure.parent / "blocker"
        blocker.write_text("a file, so no folder can be made here")
        status = run("compile", str(figure), "-o", str(blocker / "out.mtpc"))
        assert status == 1
        assert len(capsys.readouterr().err.strip().splitlines()) == 1

    @NOT_WRITTEN
    def test_a_port_that_is_taken(self, figure, capsys):
        taken = socket.socket()
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        try:
            status = run("serve", str(figure), "-p", str(taken.getsockname()[1]))
        finally:
            taken.close()
        assert status == 1
        assert len(capsys.readouterr().err.strip().splitlines()) == 1


@rule("mtp-compile")
class TestMtpCompile:
    def test_next_to_the_source(self, figure, capsys):
        assert run("compile", str(figure)) == 0
        assert (figure.parent / "dot.mtpc").read_text() == json.dumps(
            raw_mtpc(FIGURE), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ) + "\n"
        assert capsys.readouterr().out == ""

    @pytest.mark.parametrize("flag", ["-o", "--output"])
    def test_the_path_given_with_o_making_its_folder(self, figure, flag):
        out = figure.parent / "new" / "deeper" / "x.mtpc"
        assert run("compile", str(figure), flag, str(out)) == 0
        assert json.loads(out.read_text())["mtpc"] == VERSION


@NEEDS_PNPM
@rule("mtp-build")
class TestMtpBuild:
    def test_the_folder_and_its_three_files(self, figure, capsys):
        (figure.parent / "build_dot").mkdir()
        (figure.parent / "build_dot" / "notes.txt").write_text("mine")
        assert run("build", str(figure)) == 0
        out = figure.parent / "build_dot"
        assert sorted(p.name for p in out.iterdir()) == [
            "dot.mtpc", "index.html", "mathterpiece.js", "notes.txt",
        ]  # fmt: skip
        assert (out / "notes.txt").read_text() == "mine"
        assert capsys.readouterr().out == f"wrote {out / 'index.html'}\n"
        assert json.loads((out / "dot.mtpc").read_text()) == raw_mtpc(FIGURE)

    def test_the_runtime_script_is_the_same_for_every_world_model(self, tmp_path):
        a, b = tmp_path / "a.mtp", tmp_path / "b.mtp"
        a.write_text(FIGURE)
        b.write_text("(real j 2)\n")
        assert run("build", str(a)) == 0 and run("build", str(b)) == 0
        script = lambda n: (tmp_path / f"build_{n}" / "mathterpiece.js").read_bytes()  # noqa: E731
        assert script("a") == script("b")


def _get(url: str) -> str:
    return urllib.request.urlopen(url, timeout=5).read().decode()


@NEEDS_PNPM
@rule("mtp-serve")
class TestMtpServe:
    def test_serves_the_page_and_counts_the_builds(self, figure):
        from mathterpiece.serve import Server

        server = Server(figure, port=0)
        server.start()
        try:
            url = f"http://127.0.0.1:{server.port}"
            assert '"name":"v"' in _get(url) and '"name":"v"' in _get(f"{url}/any/other/path")
            before = int(_get(f"{url}/version"))
            time.sleep(0.05)
            figure.write_text(FIGURE.replace("(canvas v s)", "(canvas w s)"))
            server.check()
            assert int(_get(f"{url}/version")) > before
            assert '"name":"w"' in _get(url)
        finally:
            server.stop()

    def test_a_build_that_fails_serves_the_error_and_goes_on(self, figure):
        from mathterpiece.serve import Server

        server = Server(figure, port=0)
        server.start()
        try:
            url = f"http://127.0.0.1:{server.port}"
            time.sleep(0.05)
            figure.write_text("(real k (* 2 j))\n")
            server.check()
            assert '"name":"v"' not in _get(url)
            time.sleep(0.05)
            figure.write_text(FIGURE)
            server.check()
            assert '"name":"v"' in _get(url)
        finally:
            server.stop()

    @SERVE_IMPORTS
    def test_saving_an_imported_file_builds_again(self, tmp_path):
        from mathterpiece.serve import Server

        (tmp_path / "lib.mtp").write_text("(color ink 'navy')\n")
        src = tmp_path / "fig.mtp"
        src.write_text("(import lib)\n(scene s (circle c (r 1) (fill lib.ink)))\n(canvas v s)\n")
        server = Server(src, port=0)
        server.start()
        try:
            url = f"http://127.0.0.1:{server.port}"
            before = int(_get(f"{url}/version"))
            time.sleep(0.05)
            (tmp_path / "lib.mtp").write_text("(color ink 'teal')\n")
            server.check()
            assert int(_get(f"{url}/version")) > before
        finally:
            server.stop()


@rule("mtp-fmt")
class TestMtpFmt:
    SRC = "; a comment\n(real k   1 ; the radius\n  (>= 0))\n\n\n\n(scene s (circle c (r k)))\n"

    def test_a_syntax_error_is_rejected_and_the_file_is_left_alone(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_text("(real k\n")
        assert run("fmt", str(src)) == 1
        assert src.read_text() == "(real k\n"

    def test_the_file_keeps_its_comments_and_its_meaning(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_text(self.SRC)
        assert run("fmt", str(src)) == 0
        out = src.read_text()
        assert "; a comment" in out and "; the radius" in out
        assert mtpc(out) == mtpc(self.SRC)

    def test_a_file_in_the_layout_is_not_written(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_text(self.SRC)
        run("fmt", str(src))
        before = src.stat().st_mtime_ns
        os.utime(src, ns=(before - 10**9, before - 10**9))
        assert run("fmt", str(src)) == 0
        assert src.stat().st_mtime_ns == before - 10**9

    def test_fmt_runs_no_step_after_parse(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_text("(real k   unknown-name)\n")
        assert run("fmt", str(src)) == 0


@rule("compiler-decides-early")
class TestCompilerDecidesEarly:
    @pytest.mark.parametrize(
        "src, v",
        [
            ("(real v (* 2 (+ 1 2)))", 6),
            ("(func f ((real x)) (* 2 x)) (real v (f 3))", 6),
            ("(string v $'{(* 2 3)}')", "6"),
            ("(real v (if (> 2 1) 1 2))", 1),
        ],
    )
    def test_what_is_known_when_compiling_is_computed_then(self, src, v):
        assert obj(mtpc(src), "v")["value"]["free"] == v


@rule("compiler-same-bytes")
class TestCompilerSameBytes:
    def test_the_same_source_gives_the_same_bytes_in_two_processes(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_text(
            "(rand-seed sd 1) (real k 1 (>= 0) (<= 2))\n"
            "(scene s (foreach i 4 (circle #'c-{i}' (r (* k (rand 0 1))) (fill 'red'))))\n"
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


@rule("compiler-reads-files")
class TestCompilerReadsFiles:
    def test_an_import_is_looked_for_next_to_the_file_first(self, tmp_path):
        files = {"colors.mtp": "(color mine 'teal')\n"}
        m = in_folder(tmp_path, files, "(import colors)\n(color v colors.mine)\n")
        assert "colors.mine" in m.names

    def test_then_in_the_standard_library(self, tmp_path):
        m = in_folder(tmp_path, {}, "(import colors)\n(color v colors.tab10-named.red)\n")
        assert "v" in m.names

    def test_through_other_imports(self, tmp_path):
        files = {"a.mtp": "(import b)\n(color ink b.pen)\n", "b.mtp": "(color pen 'teal')\n"}
        m = in_folder(tmp_path, files, "(import a)\n(color v a.ink)\n")
        assert "v" in m.names

    def test_an_import_that_is_found_nowhere(self, tmp_path):
        with pytest.raises(REJECTION):
            in_folder(tmp_path, {}, "(import no-such-file)\n")


@rule("compiler-never-acts-while-drawing")
class TestCompilerNeverActsWhileDrawing:
    def test_no_animation_is_played(self):
        d = mtpc("(real k 0) (animation a (move k (to 5) (duration 1))) (button b (animation a))")
        assert obj(d, "k")["value"]["free"] == 0

    def test_a_token_is_written_with_its_declared_value_and_never_folded(self):
        d = mtpc("(color ink 'navy') (scene s (circle c (r 1) (fill ink)))")
        assert obj(d, "ink")["value"]["free"] == "#000080ff"
        fill = obj(d, "c")["attrs"]["fill"]
        assert fill["bound"][0] == "read" and fill["bound"][2] == d["names"]["ink"]

    def test_no_random_value_is_drawn(self):
        d = mtpc("(rand-seed sd 1) (real v (rand))")
        assert "bound" in obj(d, "v")["value"]


@rule("mtpc-only-boundary")
class TestMtpcOnlyBoundary:
    def test_every_copy_and_every_instance_is_in_the_mtpc(self):
        d = mtpc("(motif m () (circle c (r 1))) (scene s (foreach i 2 (m #'a-{i}')))")
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


def _walk(x, found):
    if isinstance(x, list):
        if len(x) >= 3 and x[0] == "read" and isinstance(x[2], int):
            found["reads"].append((x[2], x[3]))
        if len(x) >= 3 and x[0] == "call" and isinstance(x[2], int):
            found["calls"].append(x[2])
        for y in x:
            _walk(y, found)
    elif isinstance(x, dict):
        for y in x.values():
            _walk(y, found)


def _bound_slots(d):
    for o in d["objects"]:
        slots = [o["value"]] if "value" in o else []
        slots += list(o.get("attrs", {}).values())
        for slot in slots:
            if isinstance(slot, dict) and "bound" in slot:
                yield o, slot


# house.mtp is not a figure, and ulam-spiral.mtp takes about 15 seconds to compile.
EXAMPLES = sorted(
    p for p in (ROOT / "examples").glob("*.mtp") if p.name not in ("house.mtp", "ulam-spiral.mtp")
)


@rule("corrupt-mtpc")
class TestCorruptMtpc:
    @pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
    def test_the_compiler_writes_no_corrupt_mtpc(self, path):
        d = mtpc(path.read_text(), path=path)
        found = {"reads": [], "calls": []}
        _walk(d["objects"], found)
        _walk(d["functions"], found)
        assert all(0 <= i < len(d["objects"]) for i, _ in found["reads"])
        assert all(0 <= i < len(d["functions"]) for i in found["calls"])
        for o, slot in _bound_slots(d):
            # An expression that reads nothing is known when compiling, so it is folded.
            assert slot["deps"], f"{o.get('name')} is bound but reads nothing"
            found = {"reads": [], "calls": []}
            _walk(slot["bound"], found)
            # The position of a group is read through its translate, so a read of an object
            # needs some attribute of that object in deps, and not always the one read.
            read_objects = {i for i, _ in slot["deps"]}
            for i, a in found["reads"]:
                assert i in read_objects, f"{o.get('name')} reads {(i, a)} without it in deps"


@rule("schema-strength")
class TestSchemaStrength:
    def test_a_valid_mtpc_matches(self):
        assert schema_errors(raw_mtpc(FIGURE)) == []

    def test_another_version_does_not_match(self):
        d = raw_mtpc(FIGURE)
        d["mtpc"] = VERSION + 1
        assert schema_errors(d)

    def test_an_unknown_kind_of_object_does_not_match(self):
        d = raw_mtpc(FIGURE)
        d["objects"][0]["kind"] = "no-such-kind"
        assert schema_errors(d)

    def test_a_reference_to_no_object_is_not_an_int(self):
        d = raw_mtpc(FIGURE)
        d["names"]["k"] = "zero"
        assert schema_errors(d)


@rule("format-version")
class TestFormatVersion:
    def test_every_mtpc_holds_the_version(self):
        assert raw_mtpc("")["mtpc"] == VERSION

    def test_the_compiler_and_the_runtime_implement_the_same_version(self):
        doc_ts = (ROOT / "web" / "src" / "doc.ts").read_text()
        (runtime,) = re.findall(r"export const FORMAT_VERSION = (\d+);", doc_ts)
        assert int(runtime) == VERSION


# pytest.raises with a match argument checks the wording of an error.
WORDING = re.compile(r"raises\([^)]*match *=")


@rule("what-is-normative")
class TestWhatIsNormative:
    def test_no_conformance_test_checks_the_wording_of_an_error(self):
        here = Path(__file__).parent
        for path in here.glob("test_*.py"):
            text = path.read_text()
            assert not WORDING.search(text), f"{path.name} checks the wording of an error"

    def test_the_bytes_may_differ_while_the_meaning_is_the_same(self):
        # Two spellings with one meaning compile to one .mtpc, read as JSON.
        assert mtpc("(scene s (circle c (r 1) (fill 'red')))") == mtpc(
            "(scene s (circle c (fill 'red') (r 1)))"
        )


def _labels() -> set[str]:
    labels = set()
    for page in SPEC.glob("*.md"):
        labels |= set(re.findall(r"^```\{rule\} ([a-z0-9-]+)", page.read_text(), re.M))
    return labels


@rule("conformance")
class TestConformance:
    @LABEL
    def test_a_rejected_source_gets_an_error_that_carries_a_label(self):
        with pytest.raises(CompileError) as e:
            compile_source("(real a b) (real b 1)")
        carried = set(getattr(e.value, "rules", ()))
        # The source breaks both rules, so the error may carry either label or both.
        assert carried and carried <= {"declare-before-use", "name-lookup"}
        assert carried <= _labels()

    def test_an_accepted_source_gives_a_valid_mtpc(self):
        assert schema_errors(raw_mtpc(FIGURE)) == []
