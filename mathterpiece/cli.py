import argparse
import logging
import sys
from pathlib import Path

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.log import setup
from mathterpiece.parse import ParseError

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(prog="mtp", description="Compile a mathterpiece file.")
    commands = ap.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="compile a .mtp file")
    build.add_argument("file")
    build.add_argument(
        "-v", "--verbose", action="count", default=0, help="-v info, -vv debug, -vvv trace"
    )
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    setup(args.verbose)
    path = Path(args.file)
    try:
        compile_source(path.read_text())
    except (ParseError, CompileError) as e:
        print(f"{args.file}:{e}", file=sys.stderr)
        sys.exit(1)
    logger.info("compiled %s", args.file)
