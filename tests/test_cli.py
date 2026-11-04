import pytest

from mathterpiece.cli import main


def test_compile_writes_the_mtpc(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1)\n(scene s (circle c (r 2)))\n")
    main(["compile", str(src)])
    assert capsys.readouterr().err == ""


def test_compile_reports_the_first_error_with_its_position(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1)\n(real d (* 2 j))\n")
    with pytest.raises(SystemExit) as exc:
        main(["compile", str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"{src}:2:14: unknown name 'j'\n"


def test_a_parse_error_too(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1\n")
    with pytest.raises(SystemExit):
        main(["compile", str(src)])
    assert "unclosed '('" in capsys.readouterr().err


def test_compile_writes_the_mtpc_next_to_the_source(tmp_path):
    from mathterpiece.compiler import compile_source
    from mathterpiece.mtpc import write

    src = tmp_path / "fig.mtp"
    src.write_text("(real k 1)\n")
    main(["compile", str(src)])
    assert (tmp_path / "fig.mtpc").read_text() == write(compile_source("(real k 1)\n"))


def test_compile_writes_where_it_is_told(tmp_path):
    src = tmp_path / "fig.mtp"
    src.write_text("(real k 1)\n")
    out = tmp_path / "out" / "x.mtpc"
    main(["compile", str(src), "-o", str(out)])
    assert out.exists()


def test_a_file_that_cannot_be_read(tmp_path, capsys):
    # mtp-o135: a missing file printed a Python traceback.
    src = tmp_path / "missing.mtp"
    with pytest.raises(SystemExit) as exc:
        main(["compile", str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"{src}: no such file\n"


def test_a_folder_is_not_a_file(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["compile", str(tmp_path)])
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"{tmp_path}: cannot be read: it is a folder\n"


# The author, 2026-11-04: mtp parse prints the forms; mtp check reports the first error and writes
# nothing; mtp compile writes the .mtpc (docs/data-model.md, "The mtp command").
def test_parse_prints_the_forms_with_their_positions(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("; a comment\n(real k 1.5)\n(scene s (circle c (pos [k 2])))\n")
    main(["parse", str(src)])
    out = capsys.readouterr().out
    assert out.splitlines()[:4] == ["2:1 form", "  2:2 name real", "  2:7 name k", "  2:9 real 1.5"]
    assert "      3:25 list" in out
    assert not (tmp_path / "f.mtpc").exists()


def test_parse_reports_a_syntax_error(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1\n")
    with pytest.raises(SystemExit) as exc:
        main(["parse", str(src)])
    assert exc.value.code == 1
    assert "unclosed '('" in capsys.readouterr().err


def test_check_writes_nothing(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1)\n")
    main(["check", str(src)])
    assert capsys.readouterr().out == f"{src}: no errors\n"
    assert not (tmp_path / "f.mtpc").exists()


def test_check_reports_the_first_error(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1)\n(real d (* 2 j))\n(real e (* 2 q))\n")
    with pytest.raises(SystemExit) as exc:
        main(["check", str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"{src}:2:14: unknown name 'j'\n"
    assert not (tmp_path / "f.mtpc").exists()


@pytest.mark.parametrize("command", ["parse", "check", "compile", "build", "serve", "fmt"])
def test_each_command_takes_one_file(tmp_path, command, capsys):
    a, b = tmp_path / "a.mtp", tmp_path / "b.mtp"
    a.write_text("(real k 1)\n")
    b.write_text("(real k 1)\n")
    with pytest.raises(SystemExit) as exc:
        main([command, str(a), str(b)])
    assert exc.value.code == 2


def test_fmt_rewrites_the_file(tmp_path):
    src = tmp_path / "f.mtp"
    src.write_text("(scene s\n(circle c))   \n")
    main(["fmt", str(src)])
    assert src.read_text() == "(scene s\n  (circle c))\n"


def test_fmt_leaves_a_file_with_a_syntax_error_alone(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(scene s\n(circle c)\n")
    with pytest.raises(SystemExit):
        main(["fmt", str(src)])
    assert src.read_text() == "(scene s\n(circle c)\n"
    assert "unclosed '('" in capsys.readouterr().err


def test_compile_finds_imports_next_to_the_file(tmp_path):
    (tmp_path / "house.mtp").write_text("(color ink '#1f2a44')\n")
    src = tmp_path / "f.mtp"
    src.write_text("(import house ink) (scene s (circle c (fill ink)))\n")
    main(["compile", str(src)])
    assert "house.ink" in (tmp_path / "f.mtpc").read_text()


def test_an_error_in_an_imported_file_names_that_file(tmp_path, capsys):
    (tmp_path / "house.mtp").write_text("(color ink (mix 'red' nope 0.5))\n")
    src = tmp_path / "f.mtp"
    src.write_text("(import house)\n")
    with pytest.raises(SystemExit):
        main(["check", str(src)])
    assert capsys.readouterr().err.startswith("house.mtp:1:")


def test_a_syntax_error_in_an_imported_file(tmp_path, capsys):
    (tmp_path / "house.mtp").write_text("(color ink '#1f2a44'\n")
    src = tmp_path / "f.mtp"
    src.write_text("(import house)\n")
    with pytest.raises(SystemExit) as exc:
        main(["compile", str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err.startswith("house.mtp:1:")
