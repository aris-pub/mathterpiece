# Each file in tests/malformed holds one mistake, and its first line says the one error it must
# give: "; error LINE:COL MESSAGE".
import re
from pathlib import Path

import pytest

from mathterpiece.parse import ParseError, parse

FILES = sorted((Path(__file__).parent / "malformed").glob("*.mtp"))


@pytest.mark.parametrize("path", FILES, ids=[f.stem for f in FILES])
def test_one_error_at_its_place(path):
    src = path.read_text()
    m = re.match(r"; error (\d+):(\d+) (.*)\n", src)
    assert m, f"{path.name} does not say its error"
    with pytest.raises(ParseError) as exc:
        parse(src)
    assert (exc.value.pos.line, exc.value.pos.col) == (int(m[1]), int(m[2]))
    assert exc.value.msg == m[3]
