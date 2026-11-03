import pytest

from mathterpiece.cli import main


def test_build_compiles_a_file(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1)\n(scene s (circle c (r 2)))\n")
    main(["build", str(src)])
    assert capsys.readouterr().err == ""


def test_build_reports_the_first_error_with_its_position(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1)\n(real d (* 2 j))\n")
    with pytest.raises(SystemExit) as exc:
        main(["build", str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"{src}:2:14: unknown name 'j'\n"


def test_a_parse_error_too(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1\n")
    with pytest.raises(SystemExit):
        main(["build", str(src)])
    assert "unclosed '('" in capsys.readouterr().err


def test_build_writes_the_mtpc_next_to_the_source(tmp_path):
    from mathterpiece.compiler import compile_source
    from mathterpiece.mtpc import write

    src = tmp_path / "fig.mtp"
    src.write_text("(real k 1)\n")
    main(["build", str(src)])
    assert (tmp_path / "fig.mtpc").read_text() == write(compile_source("(real k 1)\n"))


def test_build_writes_where_it_is_told(tmp_path):
    src = tmp_path / "fig.mtp"
    src.write_text("(real k 1)\n")
    out = tmp_path / "out" / "x.mtpc"
    main(["build", str(src), "-o", str(out)])
    assert out.exists()


def test_a_file_that_cannot_be_read(tmp_path, capsys):
    # mtp-o135: a missing file printed a Python traceback.
    src = tmp_path / "missing.mtp"
    with pytest.raises(SystemExit) as exc:
        main(["build", str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"{src}: no such file\n"


def test_a_folder_is_not_a_file(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["build", str(tmp_path)])
    assert exc.value.code == 1
    assert capsys.readouterr().err == f"{tmp_path}: cannot be read: it is a folder\n"
