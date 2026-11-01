# Frame-time baseline (old runtime)

Measured on 2026-11-02, before the runtime rebuild (phase 5 must beat these numbers on the same
machine and the same method). Old runtime at commit c931d82, examples built by the old compiler.

**Method** (`bench/frames.mjs`): headless Chromium (Playwright 1.64.1), Node 26.12.1, Apple M4, viewport
1000 x 900. For each action, the runtime's own work is timed: its event handlers, every
animation-frame callback they queue, and the style and layout that follow, in milliseconds.
Painting and waiting for the screen's refresh are left out. Each control is moved through 60
steps: a slider across its track, a drag in a circle of radius 40 pixels around the shape, and
play for two seconds (work per animation frame). Three runs each.

To run: `cd web && pnpm exec vite --port 5199 &`, then `node bench/frames.mjs golden-tour tour interactive balls unit-circle best-embedding`.

**The three heaviest** (mean per action, range over three runs):

| Example | Objects | Slider | Play |
|---|---|---|---|
| tour | 500 | 3.1 to 3.6 | 3.2 to 3.3 |
| golden-tour | 623 | 3.4 to 3.5 | 2.9 to 3.0 |
| interactive | 419 | 2.9 to 3.3 | none |

**The others with controls:** balls (slider 1.8 to 2.0, play 1.9 to 2.2), unit-circle (slider 1.2
to 1.7, drag 1.0 to 1.6), best-embedding (drag 1.2 to 1.6).

Full output of the three runs:

```
run1 golden-tour {"slider":{"mean":3.39,"p95":4.1,"max":12.8},"play":{"mean":2.9,"p95":3.7,"max":5.8}}
run1 tour {"slider":{"mean":3.49,"p95":4.2,"max":7.1},"play":{"mean":3.26,"p95":4.1,"max":7.8}}
run1 interactive {"slider":{"mean":2.93,"p95":4,"max":9.8}}
run1 balls {"slider":{"mean":1.75,"p95":2.2,"max":3.6},"play":{"mean":2.06,"p95":3.6,"max":4.3}}
run1 unit-circle {"slider":{"mean":1.19,"p95":1.9,"max":2.5},"drag":{"mean":1,"p95":1.5,"max":1.6}}
run1 best-embedding {"drag":{"mean":1.16,"p95":2.5,"max":3.1}}
run2 golden-tour {"slider":{"mean":3.44,"p95":4.4,"max":10.6},"play":{"mean":3.03,"p95":3.8,"max":5.4}}
run2 tour {"slider":{"mean":3.58,"p95":4.2,"max":10.8},"play":{"mean":3.18,"p95":3.8,"max":6.8}}
run2 interactive {"slider":{"mean":3.28,"p95":3.8,"max":9.6}}
run2 balls {"slider":{"mean":2.04,"p95":2.7,"max":4.3},"play":{"mean":2.17,"p95":3.4,"max":4.3}}
run2 unit-circle {"slider":{"mean":1.73,"p95":2.6,"max":3.3},"drag":{"mean":1.6,"p95":2.8,"max":3.2}}
run2 best-embedding {"drag":{"mean":1.57,"p95":2.3,"max":2.9}}
run3 golden-tour {"slider":{"mean":3.49,"p95":5.9,"max":13.4},"play":{"mean":2.98,"p95":3.9,"max":6.5}}
run3 tour {"slider":{"mean":3.1,"p95":3.8,"max":7.3},"play":{"mean":3.17,"p95":3.9,"max":6.2}}
run3 interactive {"slider":{"mean":3.1,"p95":3.8,"max":8}}
run3 balls {"slider":{"mean":2.03,"p95":2.7,"max":3.8},"play":{"mean":1.85,"p95":2.8,"max":3.7}}
run3 unit-circle {"slider":{"mean":1.57,"p95":2.6,"max":4},"drag":{"mean":1.11,"p95":1.7,"max":1.7}}
run3 best-embedding {"drag":{"mean":1.15,"p95":2.1,"max":3}}
```
