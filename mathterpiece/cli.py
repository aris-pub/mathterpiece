import argparse
import json
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from mathterpiece.backends.mpl import EvalError, render_json
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.log import setup
from mathterpiece.parse import ParseError, parse

logger = logging.getLogger(__name__)
COMMANDS = ("show", "build")


def main(argv: list[str] | None = None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # `mtp file.mtp` means `mtp show file.mtp`.
    if not argv or argv[0] not in COMMANDS and not argv[0].startswith("-"):
        argv.insert(0, "show")
    ap = argparse.ArgumentParser(prog="mtp", description="Show or build a mathterpiece file.")
    commands = ap.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="draw a .mtp or built .json file with matplotlib")
    show.add_argument("file")
    build = commands.add_parser("build", help="compile a .mtp file to JSON for the backends")
    build.add_argument("file")
    build.add_argument("-o", "--output", help="where to write (default: next to the file)")
    for command in (show, build):
        command.add_argument(
            "-v", "--verbose", action="count", default=0, help="-v info, -vv debug, -vvv trace"
        )
    args = ap.parse_args(argv)
    setup(args.verbose)

    path = Path(args.file)
    try:
        if args.command == "show" and path.suffix == ".json":
            doc = json.loads(path.read_text())
        else:
            doc = to_json(compile_model(parse(path.read_text())))
            logger.info("compiled %s", args.file)
        if args.command == "build":
            out = Path(args.output) if args.output else path.with_suffix(".json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(doc, allow_nan=False))
            logger.info("wrote %s", out)
            return
        render_json(doc)
    except (ParseError, CompileError) as e:
        print(f"{args.file}:{e}", file=sys.stderr)
        sys.exit(1)
    except EvalError as e:
        print(f"{args.file}: {e}", file=sys.stderr)
        sys.exit(1)
    plt.show()
