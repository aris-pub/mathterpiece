# Figure guidelines

How every figure in this repository is written: the examples, the test cases, the replicas, and
any figure made later. These are rules for the author of a figure; how the runtime behaves is in
`reference.md`.

## Phones and touch

Readers will open figures on phones, so every figure must work by finger. The rules follow UI/UX
guidance for touch and for interactive charts (sources below), and the runtime implements the
behaviour they describe (bead mtp-4hin.1).

- **Nothing only by hover.** A phone has no hover. Anything a reader can see or do by hovering must
  also come from a tap. In mtp a tap acts as a hover: it enters the shape, and the shape stays
  entered until the reader taps elsewhere. So write `on-enter` and `on-leave` so that a shape left
  entered after a tap still makes sense.
- **What a tap shows stays.** Details shown on hover or tap stay until the reader taps elsewhere.
  Do not hide essential information behind hover, and do not make a detail vanish when the finger
  lifts.
- **A moving finger inspects.** While a finger is down and moving, the figure follows it, as a
  pointer would. Figures that inspect values by moving the pointer, such as a map read by hovering,
  work the same way under a finger.
- **Every drag also works by taps.** Tap a draggable shape to select it, then tap where it goes. The
  runtime gives every drag this; do not build a figure whose only way to change something is a
  long or precise drag.
- **Targets of at least 44 px.** A shape a finger must hit should be at least 44 CSS pixels across
  on a phone, or far enough from other targets that the nearest one wins. Avoid crowding small
  draggable points together.
- **Let the page scroll.** A finger on a figure's empty parts scrolls the page. Put pointer
  listeners on the shapes that need them; a canvas-level `on-pointermove` takes the finger over
  the whole canvas, so use it only when the whole canvas is the control.
- **Fit the screen.** A figure must read at a phone's width (about 390 CSS px): no text or control
  that only works on a wide screen.
- **Check it.** Before a figure is done, run `just phone-speed <name>`, which drives it by touch on
  an imitated phone and checks that each update fits in a frame (16 ms of work) and the page draws
  within 2 s.

Sources:
[WARP design system, interaction with data visualization](https://warp-ds.github.io/docs/foundations/data-visualization/interaction);
[Snyder, Rossi, Koh, Heer and Hoffswell, Interaction Techniques for Exploratory Data Visualization on Mobile Devices, EuroVis 2024](https://idl.uw.edu/papers/mobile-vis-interaction-techniques);
[WCAG 2.2, 2.5.7 Dragging Movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html)
and [1.4.13 Content on Hover or Focus](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html);
[Microsoft, hover and touch](https://msdn.microsoft.com/library/dn265029.aspx).
