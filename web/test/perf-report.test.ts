// The budgets and the table of the phone check (perf/phone.mjs), apart from any timing.
import { describe, expect, it } from "vitest";
import { type ExampleResult, BUDGETS, animationCost, failed, judge, table } from "../perf/report.ts";

const ok: ExampleResult = {
  name: "calm",
  loadMs: 900,
  updates: [
    { kind: "slider", label: "a", ms: 4, latencyMs: 20 },
    { kind: "drag", label: "#3", ms: 9, latencyMs: 25 },
  ],
  notes: [],
};

describe("judge", () => {
  it("passes an example within both budgets and names its worst update", () => {
    const j = judge(ok);
    expect(j.failed).toBe(false);
    expect(j.worst).toEqual({ kind: "drag", label: "#3", ms: 9, latencyMs: 25 });
  });

  it("fails a load over 2 s", () => {
    const j = judge({ ...ok, loadMs: 2001 });
    expect(j.loadOver).toBe(true);
    expect(j.failed).toBe(true);
  });

  it("passes a load of exactly 2 s and an update of exactly 16 ms", () => {
    const j = judge({ ...ok, loadMs: BUDGETS.loadMs, updates: [{ kind: "slider", label: "a", ms: BUDGETS.updateMs }] });
    expect(j.failed).toBe(false);
  });

  it("fails an update over 16 ms, judged by its work and not by its latency", () => {
    expect(judge({ ...ok, updates: [{ kind: "play", label: "go", ms: 16.5 }] }).updateOver).toBe(true);
    expect(judge({ ...ok, updates: [{ kind: "play", label: "go", ms: 3, latencyMs: 40 }] }).updateOver).toBe(false);
  });

  it("fails a page that never drew, or that has an error", () => {
    expect(judge({ ...ok, loadMs: null }).failed).toBe(true);
    expect(judge({ ...ok, error: "boom" }).failed).toBe(true);
  });

  it("passes an example with nothing to update", () => {
    const j = judge({ ...ok, updates: [] });
    expect(j.worst).toBeNull();
    expect(j.failed).toBe(false);
  });
});

describe("animationCost", () => {
  it("is the longest frame, the first counting the click's own work", () => {
    expect(animationCost(10, [3, 5, 4])).toBe(13);
    expect(animationCost(1, [3, 8, 4])).toBe(8);
  });

  it("is the click's own work when no frame ran", () => {
    expect(animationCost(2, [])).toBe(2);
  });
});

describe("table", () => {
  const slow: ExampleResult = {
    name: "heavy",
    loadMs: 2500,
    updates: [{ kind: "slider", label: "n", ms: 40.2, latencyMs: 60 }],
    notes: ["cut short"],
  };
  const text = table([ok, slow]);
  const lines = text.split("\n");

  it("has a row for every example with its load and worst update", () => {
    const calm = lines.find((l) => l.startsWith("calm"))!;
    expect(calm).toContain("900");
    expect(calm).toContain("9.0");
    expect(calm).toContain("drag #3");
    expect(calm).toContain("ok");
  });

  it("marks what is over budget", () => {
    const heavy = lines.find((l) => l.startsWith("heavy"))!;
    expect(heavy).toContain("2500 OVER");
    expect(heavy).toContain("40.2 OVER");
    expect(heavy).toContain("slider n");
    expect(heavy).toContain("FAIL");
  });

  it("lists the notes under the table", () => {
    expect(text).toContain("heavy: cut short");
  });

  it("fails when any example fails", () => {
    expect(failed([ok])).toBe(false);
    expect(failed([ok, slow])).toBe(true);
  });
});
