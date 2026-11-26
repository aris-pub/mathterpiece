"""Fixtures of the conformance tests of docs/spec/compiler-runtime.md."""

import pytest

from ._shared import FIGURE


@pytest.fixture
def figure(tmp_path):
    src = tmp_path / "dot.mtp"
    src.write_text(FIGURE)
    return src
