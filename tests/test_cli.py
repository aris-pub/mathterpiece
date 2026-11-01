import pytest

from mathterpiece.cli import main


def test_build_compiles_a_file(tmp_path, capsys):
    src = tmp_path / "f.mtp"
    src.write_text("(real k 1)\n(scene s (circle c (r 2)))\n")
    main(["build", str(src)])
    assert capsys.readouterr().err == ""


def test_build_reports_the_first_error_with_its_place(tmp_path, capsys):
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
