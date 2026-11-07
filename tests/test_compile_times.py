"""The comparison scripts/perf/compile_times.py makes between compile times and its baseline."""

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "perf" / "compile_times.py"
spec = importlib.util.spec_from_file_location("compile_times", SCRIPT)
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)


def test_an_example_within_30_percent_of_its_baseline_passes():
    rows = ct.compare({"a": 1.25, "b": 0.5}, {"a": 1.0, "b": 1.0})
    assert [r.status for r in rows] == ["ok", "ok"]
    assert not ct.failed(rows)


def test_an_example_more_than_30_percent_slower_fails():
    rows = ct.compare({"a": 1.31, "b": 1.0}, {"a": 1.0, "b": 1.0})
    assert [r.status for r in rows] == ["slow", "ok"]
    assert ct.failed(rows)


def test_exactly_30_percent_slower_passes():
    assert ct.compare({"a": 1.3}, {"a": 1.0})[0].status == "ok"


def test_a_slowdown_under_20_ms_passes_whatever_its_percentage():
    # A few milliseconds is noise on a busy machine (the author, 2026-11-07).
    rows = ct.compare({"tiny": 0.015, "small": 0.019}, {"tiny": 0.005, "small": 0.0})
    assert [r.status for r in rows] == ["ok", "ok"]
    assert ct.compare({"a": 0.031}, {"a": 0.010})[0].status == "slow"


def test_an_example_missing_from_the_baseline_fails():
    rows = ct.compare({"a": 1.0, "new": 2.0}, {"a": 1.0})
    assert [r.status for r in rows] == ["ok", "missing"]
    assert ct.failed(rows)


def test_the_table_shows_every_example_and_marks_the_failures():
    rows = ct.compare({"fast": 0.1, "slow": 2.0, "new": 1.0}, {"fast": 0.1, "slow": 1.0})
    text = ct.table(rows)
    lines = text.splitlines()
    assert any("fast" in line and "ok" in line for line in lines)
    assert any("slow" in line and "SLOWER" in line and "+100%" in line for line in lines)
    assert any("new" in line and "NOT IN BASELINE" in line for line in lines)
    assert "--update" in text


def test_update_keeps_the_times_in_seconds_by_name(tmp_path):
    path = tmp_path / "times.json"
    ct.save(path, {"b": 1.23456, "a": 0.5, "c": 0.00041})
    assert json.loads(path.read_text()) == {"a": 0.5, "b": 1.2346, "c": 0.0004}
    assert ct.load(path) == {"a": 0.5, "b": 1.2346, "c": 0.0004}


def test_a_baseline_of_zero_is_shown_without_dividing_by_it():
    rows = ct.compare({"a": 0.05}, {"a": 0.0})
    assert rows[0].status == "slow"
    assert "a" in ct.table(rows)


def test_a_missing_baseline_file_is_an_empty_baseline(tmp_path):
    assert ct.load(tmp_path / "none.json") == {}


def test_slow_examples_get_fewer_runs():
    times = iter([10.0, 11.0, 12.0])
    assert ct.median_time(lambda: next(times), runs=3, limit=15.0) == 10.5
    quick = iter([0.1, 0.3, 0.2])
    assert ct.median_time(lambda: next(quick), runs=3, limit=15.0) == 0.2
