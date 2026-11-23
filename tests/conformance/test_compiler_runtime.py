"""Conformance tests for docs/spec/compiler-runtime.md.

What only the runtime can show is in web/test/conformance/compiler-runtime.test.ts."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from mtpc_check import errors as schema_errors

from mathterpiece.build import compiled
from mathterpiece.cli import main
from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.mtpc import SPEC_VERSION
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

RAND = "(import rand rand rand-int pick shuffle next-seed roll-dice) "

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


LABEL = xfail("mtp-ydd4.7.53", "an error carries no label of a rule")
STEPS = xfail("mtp-08wd.1", "each copy of a foreach is proved with the value of its variable")

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
        d = mtpc("(scene s (foreach i 3 (circle @'c-{i}' (r (+ i 1)))))")
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
            RAND + "(rand-seed s 1) (real v (rand))",
            "(real k 0) (button b (move k (to 1) (duration 1)))",
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


@rule("compiler-decides-early")
class TestCompilerDecidesEarly:
    @pytest.mark.parametrize(
        "src, v",
        [
            ("(real v (* 2 (+ 1 2)))", 6),
            ("(func f ((real x)) (* 2 x)) (real v (f 3))", 6),
            ("(string v f'{(* 2 3)}')", "6"),
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


@rule("compiler-reads-files")
class TestCompilerReadsFiles:
    def test_an_import_is_looked_for_next_to_the_file_first(self, tmp_path):
        files = {"colors.mtp": "(color mine #'teal')\n"}
        m = in_folder(tmp_path, files, "(import colors)\n(color v colors.mine)\n")
        assert "colors.mine" in m.names

    def test_then_in_the_standard_library(self, tmp_path):
        m = in_folder(tmp_path, {}, "(import colors)\n(color v colors.tab10-named.red)\n")
        assert "v" in m.names

    def test_through_other_imports(self, tmp_path):
        files = {"a.mtp": "(import b)\n(color ink b.pen)\n", "b.mtp": "(color pen #'teal')\n"}
        m = in_folder(tmp_path, files, "(import a)\n(color v a.ink)\n")
        assert "v" in m.names

    def test_an_import_that_is_found_nowhere(self, tmp_path):
        with pytest.raises(REJECTION):
            in_folder(tmp_path, {}, "(import no-such-file)\n")


@rule("compiler-never-acts-while-drawing")
class TestCompilerNeverActsWhileDrawing:
    def test_no_animation_is_played(self):
        d = mtpc("(real k 0) (animation a (move k (to 5) (duration 1))) (button b a)")
        assert obj(d, "k")["value"]["free"] == 0

    def test_a_token_is_written_with_its_declared_value_and_never_folded(self):
        d = mtpc("(color ink #'navy') (scene s (circle c (r 1) (fill ink)))")
        assert obj(d, "ink")["value"]["free"] == "#000080ff"
        fill = obj(d, "c")["attrs"]["fill"]
        assert fill["bound"][0] == "read" and fill["bound"][2] == d["names"]["ink"]

    def test_no_random_value_is_drawn(self):
        d = mtpc(RAND + "(rand-seed sd 1) (real v (rand))")
        assert "bound" in obj(d, "v")["value"]


@rule("any-compiler-any-runtime")
class TestAnyCompilerAnyRuntime:
    """Another compiler or runtime can only rely on what the format defines, so every .mtpc that
    this compiler writes must match the schema of its version, which the runtime implements."""

    @pytest.mark.parametrize(
        "src", sorted((ROOT / "docs" / "spec" / "pages").glob("*/*.mtp")), ids=lambda p: p.name
    )
    def test_the_mtpc_of_each_example_page_matches_the_schema(self, src):
        doc = json.loads(compiled(src.read_text(encoding="utf-8"), src))
        assert schema_errors(doc) == []
        assert doc["mtpc"] == SPEC_VERSION


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
        d["mtpc"] = SPEC_VERSION + 1
        assert schema_errors(d)

    def test_an_unknown_kind_of_object_does_not_match(self):
        d = raw_mtpc(FIGURE)
        d["objects"][0]["kind"] = "no-such-kind"
        assert schema_errors(d)

    def test_a_reference_to_no_object_is_not_an_int(self):
        d = raw_mtpc(FIGURE)
        d["names"]["k"] = "zero"
        assert schema_errors(d)

    def test_a_listener_on_a_shape_names_one_view_in_in(self):
        d = raw_mtpc(LISTENERS)
        assert schema_errors(d) == []
        v, w = d["names"]["v"], d["names"]["w"]
        for kind in ("on-click", "on-enter", "on-drag", "on-show"):
            listener = _listener(d, kind)
            listener["in"] = [v, w]
            assert schema_errors(d), kind
            del listener["in"]
            assert schema_errors(d), kind
            listener["in"] = [v]

    def test_an_on_pointermove_names_one_view_in_in_only_on_a_shape(self):
        d = raw_mtpc(LISTENERS)
        moves = [o for o in d["objects"] if o["kind"] == "on-pointermove"]
        (on_shape,) = [o for o in moves if o["shape"] is not None]
        (on_canvas,) = [o for o in moves if o["shape"] is None]
        v = d["names"]["v"]
        del on_shape["in"]
        assert schema_errors(d)
        on_shape["in"] = [v]
        on_canvas["in"] = [v]
        assert schema_errors(d)

    def test_a_listener_on_its_own_view_has_no_in(self):
        d = raw_mtpc(LISTENERS)
        _listener(d, "on-view")["in"] = [d["names"]["v"]]
        assert schema_errors(d)


LISTENERS = """(real k 0 (>= 0) (<= 1))
(point p [0 0])
(scene s (circle c (r 1)))
(canvas v s
  (on-click c (animation (move k (to 1) (duration 1))))
  (on-enter c (animation (move k (to 1) (duration 1))))
  (on-drag c c.pos)
  (on-show c (animation (at-once (move c.opacity (to 1) (duration 0))
                                 (move c.drawn (to 1) (duration 1)))))
  (on-pointermove c p)
  (on-pointermove p)
  (on-view (animation (move k (to 1) (duration 1)))))
(canvas w s)
"""


def _listener(d: dict, kind: str) -> dict:
    return next(o for o in d["objects"] if o["kind"] == kind)


@rule("spec-version")
class TestSpecVersion:
    def test_every_mtpc_holds_the_version_of_this_draft(self):
        index = (SPEC / "index.md").read_text()
        (draft,) = re.findall(r"This is the draft of version (\d+) of the specification", index)
        assert raw_mtpc("")["mtpc"] == int(draft)

    def test_the_version_is_a_whole_number(self):
        version = raw_mtpc("")["mtpc"]
        assert type(version) is int and version >= 1

    def test_the_compiler_and_the_runtime_implement_the_same_version(self):
        doc_ts = (ROOT / "web" / "src" / "doc.ts").read_text()
        (runtime,) = re.findall(r"export const SPEC_VERSION = (\d+);", doc_ts)
        assert int(runtime) == SPEC_VERSION


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
        assert mtpc("(scene s (circle c (r 1) (fill #'red')))") == mtpc(
            "(scene s (circle c (fill #'red') (r 1)))"
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
