import argparse
import logging
import sys

import matplotlib.pyplot as plt

from mathterpiece.backends.mpl import EvalError, render
from mathterpiece.compiler import CompileError, compile_scene
from mathterpiece.log import setup
from mathterpiece.parse import ParseError, parse

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(prog="mtp", description="Render a mathterpiece file.")
    ap.add_argument("file")
    ap.add_argument(
        "-v", "--verbose", action="count", default=0, help="-v info, -vv debug, -vvv trace"
    )
    args = ap.parse_args(argv)
    setup(args.verbose)

    with open(args.file) as f:
        src: str = f.read()
    try:
        scene = compile_scene(parse(src))
        logger.info("compiled %s", args.file)
        render(scene)
    except (ParseError, CompileError) as e:
        print(f"{args.file}:{e}", file=sys.stderr)
        sys.exit(1)
    except EvalError as e:
        print(f"{args.file}: {e}", file=sys.stderr)
        sys.exit(1)
    plt.show()
