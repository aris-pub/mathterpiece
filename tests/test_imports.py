"""(import name …) (mtp-1lq). The author, 2026-11-04: (import house) reads house.mtp, from the
importing file's folder first, then the standard library, and gives house.ink; (import house ink
accent) gives ink and accent as names of their own, as Python's from house import ink, accent;
there is no way to import every name at once. An imported file holds only top-level declarations
of colors, fonts, functions, motifs, variants, types, and const variables. A color's CSS variable
is named by its file: --mtp-house-ink."""

import pytest

from mathterpiece import compiler
from mathterpiece.compiler import CompileError, compile_source

HOUSE = """; The house style.
(color ink '#1f2a44')
(color accent '#e76f51')
(font label (size 14))
(real gap 0.4 (const))
(type unit real (>= 0) (<= 1))
(func darker ((color c)) (mix c ink 0.5))
(motif dot () (circle c (r 0.2) (fill ink)))
"""


@pytest.fixture
def files(tmp_path):
    def write(**sources):
        for name, src in sources.items():
            (tmp_path / f"{name}.mtp").write_text(src)
        return tmp_path / "fig.mtp"

    return write


def build(path):
    return compile_source(path.read_text(), path=path)


def fails(path, match):
    with pytest.raises(CompileError, match=match):
        build(path)


def test_the_file_by_its_name(files):
    m = build(files(house=HOUSE, fig="(import house) (scene s (circle c (fill house.ink)))"))
    assert "house.ink" in m.names
    assert m.get("c").attrs["fill"].bound


def test_names_one_by_one(files):
    m = build(
        files(house=HOUSE, fig="(import house ink accent) (scene s (circle c (fill accent)))")
    )
    assert m.get("c").attrs["fill"].bound
    # As Python's from-import: the file's own name is not given.
    fails(files(house=HOUSE, fig="(import house ink) (real v house.gap)"), "unknown name 'house'")


def test_only_what_is_named(files):
    fails(files(house=HOUSE, fig="(import house ink) (real v gap)"), "unknown name 'gap'")


def test_a_name_the_file_does_not_declare(files):
    fails(files(house=HOUSE, fig="(import house shade)"), "house.mtp declares no 'shade'")
    fails(
        files(house=HOUSE, fig="(import house) (real v house.shade)"),
        "house.mtp declares no 'shade'",
    )


def test_the_file_reads_its_own_names(files):
    m = build(files(house=HOUSE, fig="(import house darker) (color v (darker 'red'))"))
    assert m.get("v").value.bound


def test_a_local_name_inside_the_file_wins_over_its_declarations(files):
    house = "(real gap 0.4 (const)) (func f ((real x)) (let ((gap 2)) (+ x gap)))"
    m = build(files(house=house, fig="(import house f) (real v (f 1))"))
    assert m.get("v").value.value == 3


def test_motifs_and_types(files):
    build(files(house=HOUSE, fig="(import house) (scene s (house.dot d)) (house.unit u 0.5)"))
    build(files(house=HOUSE, fig="(import house dot unit) (scene s (dot d) (dot_)) (unit u 0.5)"))
    fails(files(house=HOUSE, fig="(import house unit) (unit u 2)"), "breaks")


def test_const_variables(files):
    m = build(files(house=HOUSE, fig="(import house gap) (real v (* 2 gap))"))
    assert m.get("v").value.value == 0.8


@pytest.mark.parametrize(
    "decl, what",
    [
        ("(scene s (circle c))", "a scene"),
        ("(real k 1)", "a variable that is not const"),
        ("(real k 1) (canvas v)", "a variable that is not const"),
        ("(slider sl (move k (from 0) (to 1)))", "a slider"),
        ("(animation a (wait 1))", "an animation"),
    ],
)
def test_an_imported_file_holds_only_declarations(files, decl, what):
    fails(files(house=decl, fig="(import house)"), f"house.mtp holds {what}")


def test_a_name_imported_and_declared(files):
    fails(
        files(house=HOUSE, fig="(import house ink) (color ink 'red')"), "'ink' is already declared"
    )


def test_an_error_inside_the_imported_file_names_it(files):
    fails(files(house="(color ink (mix 'red' nope 0.5))", fig="(import house)"), "house.mtp:1:")


def test_a_missing_file(files):
    fails(files(fig="(import house)"), "no house.mtp next to fig.mtp or in the standard library")


def test_a_cycle(files):
    fails(files(a="(import b)", b="(import a)", fig="(import a)"), "imports itself")


def test_a_file_imported_twice_is_read_once(files):
    base = "(color ink '#000000')"
    house = "(import base ink) (func darker ((color c)) (mix c ink 0.5))"
    m = build(files(base=base, house=house, fig="(import base) (import house darker)"))
    assert list(m.names).count("base.ink") == 1


def test_names_an_imported_file_imported(files):
    # As Python: a name the file imported can be imported from it.
    base = "(color ink '#000000')"
    build(files(base=base, house="(import base ink)", fig="(import house ink) (color v ink)"))


def test_the_standard_library_after_the_folder(files, tmp_path, monkeypatch):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "css.mtp").write_text("(color gold '#ffd700')")
    monkeypatch.setattr(compiler, "STDLIB", lib)
    build(files(fig="(import css gold) (color v gold)"))
    # The folder's own css.mtp wins.
    fails(
        files(css="(color silver '#c0c0c0')", fig="(import css gold)"), "css.mtp declares no 'gold'"
    )


def test_an_import_needs_the_files_folder():
    with pytest.raises(CompileError, match="compile it from a file"):
        compile_source("(import house)")


def test_the_compiled_file_names_the_token_by_its_file(files):
    import json

    from mathterpiece.mtpc import write

    d = json.loads(
        write(build(files(house=HOUSE, fig="(import house ink) (scene s (circle c (fill ink)))")))
    )
    assert "house.ink" in d["names"]
