# 3D in plain SVG: tests

Plain SVG and JavaScript, not mathterpiece. These pages test whether SVG alone can draw 3D figures at
a usable speed: each frame, the page projects every point through a camera, lights each face, sorts
the faces far to near, and writes them into a fixed set of paths. See the bead mtp-0myq for the
design and the measurements.

- `sweep.html`: a lit sphere of 1152 faces with the equator, a meridian, a point p and the three
  axes. The camera sweeps once around. Hidden parts of curves and axes are cut away. Hovering a term
  in the sentence marks its shape, and hovering a shape marks its term. `?t=3` freezes the sweep at
  3 seconds.
- `bench.html`: a torus or a wavy surface, `?kind=torus|graph&n=40` for n by n faces,
  `&frames=120` to run that many frames and record their times.
- `bench2.html`: the same, timing the arithmetic, the path text, the attribute writes and the
  browser's drawing separately.

Run from this folder (Playwright comes from web/node_modules):

    node run.cjs headed     # frame rates for several face counts
    node run2.cjs           # where each frame's time goes, and chrome://gpu
    node shots.cjs          # screenshots of sweep.html and a recording of one sweep
