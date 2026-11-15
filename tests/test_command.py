"""The mtp command and its subcommands. The spec leaves how the compiler is run to the
implementation (docs/spec/compiler-runtime.md, Rule compiler-input-output), so these are not
conformance tests."""

import json
import os
import shutil
import socket
import time
import urllib.request

import pytest
from conformance.support import (
    mtpc,
    raw_mtpc,
)

from mathterpiece.cli import main
from mathterpiece.mtpc import SPEC_VERSION


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


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
        assert json.loads(out.read_text())["mtpc"] == SPEC_VERSION


@NEEDS_PNPM
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
