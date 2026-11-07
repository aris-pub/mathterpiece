"""Times compiling each example (but house.mtp, which is not a figure) and compares the times
with the baseline in compile-times.json, next to this script. Fails when an example compiles more
than 30% slower than its baseline and by more than 20 ms, or has no baseline. The baseline is one
machine's times, so it is only meaningful on that machine.

Run: uv run python scripts/perf/compile_times.py [--update]
--update records the times measured as the new baseline.
"""

import argparse
import json
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
EXAMPLES = ROOT / "examples"
BASELINE = Path(__file__).parent / "compile-times.json"
SLACK = 0.30
# A slowdown smaller than this is noise, whatever its percentage: most examples compile in a few
# milliseconds, and a busy machine moves them by that much.
FLOOR = 0.020
RUNS = 3
# Seconds one example may spend being compiled again: ulam-spiral takes about 13 s a run.
LIMIT = 15.0


@dataclass
class Row:
    name: str
    seconds: float
    baseline: float | None
    status: str  # "ok", "slow" or "missing"


def compare(times: dict[str, float], baseline: dict[str, float], slack=SLACK) -> list[Row]:
    rows = []
    for name, s in times.items():
        base = baseline.get(name)
        if base is None:
            status = "missing"
        elif s > base * (1 + slack) and s - base > FLOOR:
            status = "slow"
        else:
            status = "ok"
        rows.append(Row(name, s, base, status))
    return rows


def failed(rows: list[Row]) -> bool:
    return any(r.status != "ok" for r in rows)


def table(rows: list[Row]) -> str:
    width = max([len("example")] + [len(r.name) for r in rows])
    lines = [f"{'example':<{width}}  {'seconds':>8}  {'baseline':>8}  {'change':>7}  result"]
    slow = f"SLOWER (more than +{SLACK:.0%} and {FLOOR * 1000:.0f} ms)"
    marks = {"ok": "ok", "slow": slow, "missing": "NOT IN BASELINE"}
    for r in rows:
        base = "-" if r.baseline is None else f"{r.baseline:.4f}"
        change = "-" if not r.baseline else f"{(r.seconds / r.baseline - 1):+.0%}"
        lines.append(
            f"{r.name:<{width}}  {r.seconds:>8.4f}  {base:>8}  {change:>7}  {marks[r.status]}"
        )
    if any(r.status == "missing" for r in rows):
        lines.append("Record the missing examples with: just compile-times --update")
    elif failed(rows):
        lines.append("If the slowdown is expected, record it with: just compile-times --update")
    return "\n".join(lines)


def load(path: Path) -> dict[str, float]:
    return json.loads(path.read_text()) if path.exists() else {}


def save(path: Path, times: dict[str, float]) -> None:
    path.write_text(json.dumps({k: round(times[k], 4) for k in sorted(times)}, indent=2) + "\n")


def median_time(run: Callable[[], float], runs=RUNS, limit=LIMIT) -> float:
    """The median of up to runs times, stopping early once their sum is over limit seconds."""
    times = [run()]
    while len(times) < runs and sum(times) <= limit:
        times.append(run())
    return statistics.median(times)


def compile_once(path: Path) -> float:
    from mathterpiece.compiler import compile_model
    from mathterpiece.parse import parse

    src = path.read_text(encoding="utf-8")
    start = time.perf_counter()
    compile_model(parse(src), path)
    return time.perf_counter() - start


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--update", action="store_true", help="record the times as the baseline")
    args = ap.parse_args(argv)
    times = {}
    for path in sorted(EXAMPLES.glob("*.mtp")):
        if path.name == "house.mtp":
            continue
        times[path.stem] = median_time(lambda p=path: compile_once(p))
        print(f"{path.stem}: {times[path.stem]:.3f} s", file=sys.stderr, flush=True)
    if args.update:
        save(BASELINE, times)
        print(f"recorded {len(times)} times in {BASELINE.relative_to(ROOT)}")
        return 0
    rows = compare(times, load(BASELINE))
    print(table(rows))
    return 1 if failed(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
