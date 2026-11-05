"""mtp build and mtp serve (docs/data-model.md, "The mtp command"): building is parsing,
compiling, writing the .mtpc, and writing a minimal page that shows the figure. The author,
2026-11-04: mtp build figure.mtp writes the folder build_figure/; the runtime is built with Node
and pnpm."""

import json
import shutil
import time
import urllib.request

import pytest

from mathterpiece.cli import main

pytestmark = pytest.mark.skipif(shutil.which("pnpm") is None, reason="pnpm is not installed")

FIGURE = """; A dot and a slider.
(real k 1 (>= 0) (<= 2))
(scene s (circle c (r k)))
(canvas v s)
(slider size (move k (from 0) (to 2)) (label 'size'))
(button back (animation (move k (to 1) (duration 0.5))))
(readout says $'k = {k:.1f}')
"""


@pytest.fixture
def figure(tmp_path):
    src = tmp_path / "dot.mtp"
    src.write_text(FIGURE)
    return src


def test_build_writes_a_folder_named_after_the_figure(figure):
    main(["build", str(figure)])
    out = figure.parent / "build_dot"
    assert sorted(p.name for p in out.iterdir()) == ["dot.mtpc", "index.html", "mathterpiece.js"]
    assert json.loads((out / "dot.mtpc").read_text())["objects"]


def test_the_page_shows_every_view_control_and_readout_in_order(figure):
    main(["build", str(figure)])
    page = (figure.parent / "build_dot" / "index.html").read_text()
    shown = [page.index(f'name="{n}"') for n in ("v", "size", "back", "says")]
    assert shown == sorted(shown)
    assert '<mtp-canvas model="figure" name="v">' in page
    assert '<mtp-slider model="figure" name="size">' in page
    assert "A dot and a slider." in page


def test_the_page_holds_the_figure_and_the_runtime_so_it_opens_as_a_file(figure):
    # A browser loads no module and fetches no file for a page opened as a file.
    main(["build", str(figure)])
    out = figure.parent / "build_dot"
    page = (out / "index.html").read_text()
    assert (out / "dot.mtpc").read_text().strip() in page.replace("<\\/", "</")
    assert "customElements" in page
    assert 'src="' not in page


def test_build_of_a_figure_with_an_error_writes_nothing(tmp_path, capsys):
    src = tmp_path / "bad.mtp"
    src.write_text("(real k (* 2 j))\n")
    with pytest.raises(SystemExit) as exc:
        main(["build", str(src)])
    assert exc.value.code == 1
    assert "unknown name 'j'" in capsys.readouterr().err
    assert not (tmp_path / "build_bad").exists()


class TestServe:
    def test_serves_the_page_and_builds_again_on_each_save(self, figure):
        from mathterpiece.serve import Server

        server = Server(figure, port=0)
        server.start()
        try:
            url = f"http://127.0.0.1:{server.port}"
            page = urllib.request.urlopen(url).read().decode()
            assert '<mtp-canvas model="figure" name="v">' in page
            before = urllib.request.urlopen(f"{url}/version").read().decode()
            time.sleep(0.05)
            figure.write_text(FIGURE.replace("(canvas v s)", "(canvas w s)"))
            server.check()
            after = urllib.request.urlopen(f"{url}/version").read().decode()
            assert after != before
            assert 'name="w"' in urllib.request.urlopen(url).read().decode()
        finally:
            server.stop()

    def test_shows_a_compile_error_on_the_page_and_keeps_watching(self, figure):
        from mathterpiece.serve import Server

        server = Server(figure, port=0)
        server.start()
        try:
            url = f"http://127.0.0.1:{server.port}"
            time.sleep(0.05)
            figure.write_text("(real k (* 2 j))\n")
            server.check()
            page = urllib.request.urlopen(url).read().decode()
            assert "unknown name 'j'" in page
            time.sleep(0.05)
            figure.write_text(FIGURE)
            server.check()
            assert "unknown name" not in urllib.request.urlopen(url).read().decode()
        finally:
            server.stop()


def test_the_opening_comment_becomes_paragraphs():
    # The comment's line breaks are the source's: its lines run together, and an empty comment
    # line starts a new paragraph (the author, 2026-11-05).
    from mathterpiece.build import about

    src = "; One line\n; and the next.\n;\n; A second paragraph.\n(real k 1)\n; Not this one.\n"
    assert about(src) == ["One line and the next.", "A second paragraph."]
    assert about("(real k 1)") == []
