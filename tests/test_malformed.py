# Each file in tests/malformed holds one mistake, and its first line says the one error it must
# give: "; error LINE:COL MESSAGE".
import re
from pathlib import Path

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.parse import ParseError, parse

FILES = sorted((Path(__file__).parent / "malformed").glob("*.mtp"))


@pytest.mark.parametrize("path", FILES, ids=[f.stem for f in FILES])
def test_one_error_where_it_is(path):
    src = path.read_text()
    m = re.match(r"; error (\d+):(\d+) (.*)\n", src)
    assert m, f"{path.name} does not say its error"
    with pytest.raises(ParseError) as exc:
        parse(src)
    assert (exc.value.pos.line, exc.value.pos.col) == (int(m[1]), int(m[2]))
    assert exc.value.msg == m[3]


def test_an_unexpected_item_is_shown_as_mtp():
    # mtp-1njz: the message printed the parser's internal form of the item.
    with pytest.raises(CompileError) as e:
        compile_source("(scene s (group g (foreach i 3 (real w (* 2 i)) (circle_ (r w)))))")
    assert "Form(" not in str(e.value)
    assert "got (real …)" in str(e.value)
