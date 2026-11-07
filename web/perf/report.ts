// The budgets of the phone check (perf/phone.mjs) and its table, kept apart from the browser so
// they can be tested without timing anything.

export const BUDGETS = { loadMs: 2000, updateMs: 16 };

/** One update: the runtime's own work for it, in ms, and, not judged, how long from the event
 * until the frame after it had run. */
export interface Update {
  kind: string;
  label: string;
  ms: number;
  latencyMs?: number;
}

export interface ExampleResult {
  name: string;
  /** From the start of navigation until every canvas has drawn its SVG; null when none drew. */
  loadMs: number | null;
  updates: Update[];
  notes: string[];
  error?: string;
}

export interface Judgment {
  loadOver: boolean;
  worst: Update | null;
  updateOver: boolean;
  failed: boolean;
}

export function judge(r: ExampleResult): Judgment {
  const loadOver = r.loadMs === null || r.loadMs > BUDGETS.loadMs;
  const worst = r.updates.reduce<Update | null>((w, u) => (w === null || u.ms > w.ms ? u : w), null);
  const updateOver = worst !== null && worst.ms > BUDGETS.updateMs;
  return { loadOver, worst, updateOver, failed: loadOver || updateOver || r.error !== undefined };
}

export function failed(results: ExampleResult[]): boolean {
  return results.some((r) => judge(r).failed);
}

/** An animation's cost: its longest frame, where the first frame also holds the click's own
 * work, since both happen before the screen next shows anything. */
export function animationCost(clickMs: number, frames: number[]): number {
  if (!frames.length) return clickMs;
  return Math.max(clickMs + frames[0]!, ...frames.slice(1));
}

export function table(results: ExampleResult[]): string {
  const head = ["example", "load ms", "worst update ms", "caused by", "to next frame ms", "updates", "result"];
  const rows = results.map((r) => {
    const j = judge(r);
    const load = r.loadMs === null ? "not drawn" : String(Math.round(r.loadMs));
    const worst = j.worst === null ? "-" : j.worst.ms.toFixed(1);
    return [
      r.name,
      j.loadOver ? `${load} OVER` : load,
      j.updateOver ? `${worst} OVER` : worst,
      j.worst === null ? "-" : `${j.worst.kind} ${j.worst.label}`,
      j.worst?.latencyMs === undefined ? "-" : j.worst.latencyMs.toFixed(1),
      String(r.updates.length),
      j.failed ? "FAIL" : "ok",
    ];
  });
  const widths = head.map((h, i) => Math.max(h.length, ...rows.map((row) => row[i]!.length)));
  const line = (cells: string[]) => cells.map((c, i) => c.padEnd(widths[i]!)).join("  ").trimEnd();
  const notes = results.flatMap((r) => [
    ...(r.error === undefined ? [] : [`${r.name}: error: ${r.error}`]),
    ...r.notes.map((n) => `${r.name}: ${n}`),
  ]);
  return [line(head), ...rows.map(line), ...(notes.length ? ["", ...notes] : [])].join("\n");
}
