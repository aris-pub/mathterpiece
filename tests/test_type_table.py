"""Each structured type written once (mtp-qje3): the compiled file holds the types other than a
plain name, such as a string narrowed to four names, in the top-level list type-table, and every
object, attribute, expression, parameter and result refers to its type by its position there.
The runtime puts them back when it loads the file. Found 2026-11-05 after mtp-jru8: a heatmap
cell's fill wrote the same narrowed string type three times."""

import json

from helpers import doc
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.mtpc import VERSION, write

SRC = (
    "(string scheme 'a' (one-of 'a' 'b' 'c')) (real t 0.5 (>= 0) (<= 1))"
    " (scene s (foreach i 3 (circle_ (x i) (r (if (= scheme 'a') t 1)))))"
)


def raw(src):
    return json.loads(write(compile_source(src)))


def test_a_structured_type_is_written_once():
    d = raw(SRC)
    table = d["type-table"]
    narrowed = {"refine": "string", "constraints": [["one-of", ["a", "b", "c"]]]}
    assert table.count(narrowed) == 1
    text = json.dumps({k: v for k, v in d.items() if k != "type-table"})
    assert '"one-of"' not in text


def test_a_plain_type_stays_its_name():
    d = raw(SRC)
    assert "real" not in d["type-table"] and "string" not in d["type-table"]


def test_put_back_it_reads_as_before():
    whole = doc(SRC)
    scheme = whole["objects"][whole["names"]["scheme"]]
    assert scheme["type"] == {"refine": "string", "constraints": [["one-of", ["a", "b", "c"]]]}
    assert "type-table" not in whole


def test_the_file_passes_the_schema_and_has_the_new_version():
    d = raw(SRC)
    assert d["mtpc"] == VERSION == 4
    assert errors(d) == []
