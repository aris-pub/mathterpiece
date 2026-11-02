"""Every example compiles and writes an .mtpc the schema accepts."""

import json
from pathlib import Path

import pytest
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.mtpc import write

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.mtp"))


@pytest.mark.parametrize("path", EXAMPLES, ids=[p.stem for p in EXAMPLES])
def test_the_example_compiles_to_a_valid_mtpc(path):
    assert errors(json.loads(write(compile_source(path.read_text())))) == []
