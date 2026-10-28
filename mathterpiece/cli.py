import argparse
import logging
import sys

from mathterpiece.log import setup
from mathterpiece.parse import ParseError, parse

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(prog="mtp", description="Parse a mathterpiece file.")
    ap.add_argument("file")
    ap.add_argument(
        "-v", "--verbose", action="count", default=0, help="-v info, -vv debug, -vvv trace"
    )
    args = ap.parse_args(argv)
    setup(args.verbose)

    with open(args.file) as f:
        src: str = f.read()
    try:
        forms = parse(src)
    except ParseError as e:
        print(f"{args.file}:{e}", file=sys.stderr)
        sys.exit(1)
    logger.info("parsed %s: %d forms", args.file, len(forms))
