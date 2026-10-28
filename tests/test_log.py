import logging

import pytest

from mathterpiece.log import TRACE, setup


@pytest.fixture(autouse=True)
def reset_logger():
    log = logging.getLogger("mathterpiece")
    yield
    log.handlers.clear()
    log.setLevel(logging.NOTSET)
    log.propagate = True


@pytest.mark.parametrize(
    "verbosity, level",
    [(0, logging.WARNING), (1, logging.INFO), (2, logging.DEBUG), (3, TRACE), (5, TRACE)],
)
def test_verbosity_levels(verbosity, level):
    setup(verbosity)
    assert logging.getLogger("mathterpiece").level == level


def test_trace_is_below_debug():
    assert TRACE < logging.DEBUG
    assert logging.getLevelName(TRACE) == "TRACE"


def test_does_not_propagate_to_root():
    setup(3)
    assert logging.getLogger("mathterpiece").propagate is False


def test_module_loggers_inherit_level():
    setup(2)
    assert logging.getLogger("mathterpiece.parser").getEffectiveLevel() == logging.DEBUG
