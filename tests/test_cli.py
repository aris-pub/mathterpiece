import json
import logging
from pathlib import Path

import pytest

from mathterpiece.cli import main

EXAMPLES = Path(__file__).parent.parent / "examples"


@pytest.fixture(autouse=True)
def shown(monkeypatch):
    calls = []
    monkeypatch.setattr("matplotlib.pyplot.show", lambda: calls.append(True))
    return calls


@pytest.fixture(autouse=True)
def reset_logger():
    yield
    log = logging.getLogger("mathterpiece")
    log.handlers.clear()
    log.setLevel(logging.NOTSET)
    log.propagate = True


def test_parse_error_exits_with_position(tmp_path, capsys):
    src = tmp_path / "bad.mtp"
    src.write_text("(circle 'a'\n  (r 2x))")
    with pytest.raises(SystemExit) as exc:
        main([str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err.strip() == f"{src}:2:6: invalid number '2x'"


def test_compile_error_exits_with_position(tmp_path, capsys):
    src = tmp_path / "bad.mtp"
    src.write_text("(scene _\n  (circle 'a'\n    (r 'x')))")
    with pytest.raises(SystemExit) as exc:
        main([str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err.startswith(f"{src}:3:")


def test_valid_file_is_compiled_and_shown(tmp_path, capsys, shown):
    src = tmp_path / "ok.mtp"
    src.write_text("(scene 'world' (circle 'a')) (canvas 'cnv' world)")
    main([str(src), "-v"])
    assert f"compiled {src}" in capsys.readouterr().err
    assert shown == [True]


@pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.mtp")), ids=lambda p: p.name)
def test_examples_run(example):
    main([str(example)])


SIMPLE = "(scene 'world' (circle 'a')) (canvas 'cnv' world)"


def test_build_writes_json_next_to_the_source(tmp_path, shown):
    src = tmp_path / "figure.mtp"
    src.write_text(SIMPLE)
    main(["build", str(src)])
    doc = json.loads((tmp_path / "figure.json").read_text())
    assert doc["mtp"] == 1 and "a" in doc["names"]
    assert shown == []


def test_build_to_a_chosen_path(tmp_path):
    src = tmp_path / "figure.mtp"
    src.write_text(SIMPLE)
    out = tmp_path / "out" / "x.json"
    main(["build", str(src), "-o", str(out)])
    assert json.loads(out.read_text())["mtp"] == 1


def test_build_reports_errors(tmp_path, capsys):
    src = tmp_path / "bad.mtp"
    src.write_text("(scene _\n  (circle 'a'\n    (r 'x')))")
    with pytest.raises(SystemExit) as exc:
        main(["build", str(src)])
    assert exc.value.code == 1
    assert capsys.readouterr().err.startswith(f"{src}:3:")
    assert not (tmp_path / "bad.json").exists()


def test_show_is_the_default(tmp_path, shown):
    src = tmp_path / "figure.mtp"
    src.write_text(SIMPLE)
    main(["show", str(src)])
    main([str(src)])
    assert shown == [True, True]


def test_show_a_built_file(tmp_path, shown):
    src = tmp_path / "figure.mtp"
    src.write_text(SIMPLE)
    main(["build", str(src)])
    main(["show", str(tmp_path / "figure.json")])
    assert shown == [True]
