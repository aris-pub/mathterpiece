import logging

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG, TRACE]


def setup(verbosity: int):
    log = logging.getLogger("mathterpiece")
    log.setLevel(LEVELS[min(verbosity, len(LEVELS) - 1)])
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    log.addHandler(handler)
    log.propagate = False
