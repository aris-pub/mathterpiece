import logging
from pathlib import Path

import pytest

from mathterpiece.cli import main

EXAMPLES = Path(__file__).parent.parent / "examples"


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


def test_valid_file_reports_forms(tmp_path, capsys):
    src = tmp_path / "ok.mtp"
    src.write_text("(circle 'a') (canvas 'cnv' a)")
    main([str(src), "-v"])
    assert f"parsed {src}: 2 forms" in capsys.readouterr().err


@pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.mtp")), ids=lambda p: p.name)
def test_examples_parse(example):
    main([str(example)])
