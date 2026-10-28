import argparse
import logging

import matplotlib.pyplot as plt

from mathterpiece.backends import mpl
from mathterpiece.log import setup
from mathterpiece.parser import Parser

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(prog="mtp", description="Render a mathterpiece file.")
    ap.add_argument("file")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="-v info, -vv debug, -vvv trace")
    args = ap.parse_args(argv)
    setup(args.verbose)

    with open(args.file) as f:
        src: str = f.read()
    scn = Parser(src).parse()
    logger.info("parsed %s: %d objects, %d views", args.file, len(scn.objects), len(scn.views))
    mpl.render(scn)
    plt.show()
