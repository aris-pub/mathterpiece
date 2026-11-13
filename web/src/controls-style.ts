// How mtp's controls look. They are drawn with BRAIID, the design system of RSM documents, and
// read its tokens, so a figure in an RSM document takes the document's accent, surfaces and dark
// mode. A page that shows controls must load braiid.css. Their font is the interface's, as in
// Studio, not the document's, so they look the same whatever typeface the reader picks.

export const CONTROLS_CSS = `
mtp-slider, mtp-button, mtp-play, mtp-stepper, mtp-toggle {
  font-family: "Source Sans 3", sans-serif;
  color: var(--text-body);
}

/* A control is drawn in one color at rest and another while the reader uses it: pressing,
   dragging, focused from the keyboard, or a play playing. A page sets them with
   --mtp-control-rest and --mtp-control-active; where it sets neither, both are BRAIID's accent,
   as before there were two. --mtp-c is the one a control draws with now. */
mtp-slider, mtp-button, mtp-play, mtp-stepper {
  --mtp-rest: var(--mtp-control-rest, var(--primary-700));
  --mtp-active: var(--mtp-control-active, var(--primary-700));
}
mtp-toggle {
  --mtp-rest: var(--mtp-control-rest, var(--primary-600));
  --mtp-active: var(--mtp-control-active, var(--primary-600));
}
mtp-slider input, mtp-button button, mtp-toggle input { --mtp-c: var(--mtp-rest); }
mtp-slider input:active, mtp-slider input:focus-visible,
mtp-button button:active, mtp-button button:focus-visible,
mtp-toggle input:active, mtp-toggle input:focus-visible { --mtp-c: var(--mtp-active); }

mtp-slider { display: inline-block; min-width: 12rem; }
mtp-slider label {
  display: flex; flex-direction: column; gap: 0.25rem;
  font-size: 0.875rem; font-weight: 600; color: var(--text-subtle);
  font-variant-numeric: tabular-nums;
}
mtp-slider input[type="range"] {
  --u: 0;
  -webkit-appearance: none; appearance: none;
  width: 100%; height: 1.5rem; margin: 0;
  background: transparent; cursor: pointer;
}
mtp-slider input[type="range"]::-webkit-slider-runnable-track {
  height: 4px; border-radius: 999px;
  background: linear-gradient(to right,
    var(--mtp-c) calc(8px + var(--u) * (100% - 16px)),
    var(--border-primary) calc(8px + var(--u) * (100% - 16px)));
}
mtp-slider input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 16px; height: 16px; margin-top: -6px; border-radius: 50%;
  background: var(--mtp-c); border: 2px solid var(--surface-page);
  box-shadow: 0 0 0 1px var(--border-primary);
}
mtp-slider input[type="range"]::-moz-range-track {
  height: 4px; border-radius: 999px; background: var(--border-primary);
}
mtp-slider input[type="range"]::-moz-range-progress {
  height: 4px; border-radius: 999px; background: var(--mtp-c);
}
mtp-slider input[type="range"]::-moz-range-thumb {
  width: 16px; height: 16px; border-radius: 50%; box-sizing: border-box;
  background: var(--mtp-c); border: 2px solid var(--surface-page);
  box-shadow: 0 0 0 1px var(--border-primary);
}
mtp-slider input[type="range"]:focus-visible {
  outline: 2px solid var(--border-action); outline-offset: 2px; border-radius: 4px;
}
mtp-slider input[type="range"]:disabled { cursor: not-allowed; opacity: 0.5; }

/* The ticks sit under the track, each where the knob's center stands for its value: the
   knob's center runs from half a knob in from each end. */
mtp-slider .mtp-ticks {
  position: relative; height: 1.25rem; margin-top: -0.25rem;
  font-size: 0.75rem; font-weight: 400; color: var(--text-subtle);
}
mtp-slider .mtp-ticks [data-value] {
  position: absolute; top: 0; left: calc(8px + var(--u) * (100% - 16px));
  width: 1px; height: 5px; background: currentColor;
}
mtp-slider .mtp-ticks [data-value]::after {
  content: attr(data-value);
  position: absolute; top: 6px; left: 50%; transform: translateX(-50%);
  white-space: nowrap; background: none;
}

mtp-button button {
  position: relative;
  font: 600 0.875rem/1.2 "Source Sans 3", sans-serif;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border-primary); border-radius: var(--radius-lg);
  background: var(--surface-page); color: var(--mtp-c);
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}
/* A larger area the finger can hit than the button draws, for 44px touch targets. */
mtp-button button::after, mtp-play .mtp-play-button::after, mtp-stepper .mtp-step-button::after {
  content: ""; position: absolute; inset: -6px;
}
mtp-button button:hover {
  background: var(--surface-hover); border-color: var(--primary-300);
}
mtp-button button:active { background: var(--gray-100); }
/* A button that says it is the current choice, (selected true): filled, as a play's button. */
mtp-button button[aria-pressed="true"],
mtp-button button[aria-pressed="true"]:hover {
  background: var(--mtp-active); border-color: var(--mtp-active); color: var(--surface-page, white);
}
mtp-button button:focus-visible, mtp-play .mtp-play-button:focus-visible,
mtp-play .mtp-bars:focus-visible, mtp-stepper button:focus-visible {
  outline: 2px solid var(--border-action, Highlight); outline-offset: 2px;
}
mtp-button button:disabled, mtp-play .mtp-play-button:disabled,
mtp-stepper .mtp-step-button:disabled, mtp-stepper .mtp-dot:disabled { cursor: not-allowed; opacity: 0.5; }

/* A play: the button, then the bars, one per step with (buttons true), with a knob like the
   slider's, and the step count after them, in one row no taller than the button. The bars sit on a
   track of their own color, so at rest they read as a tour not yet played rather than as a control
   turned off. The button is the active color even at rest: it is what the reader presses first,
   and a rest color such as a gray would make it look turned off. In explore mode the bars are
   dimmed, the knob is an empty ring at the left end, and a pill reading Exploring sits on them. */
mtp-play {
  display: flex; align-items: center; gap: 0.75rem; min-width: 16rem;
  --mtp-bar-track: color-mix(in srgb, var(--text-body, currentColor) 20%, transparent);
  --mtp-bar-fill: var(--mtp-rest);
}
mtp-play[data-mtp-playing], mtp-play:has(:focus-visible), mtp-play .mtp-bars.mtp-dragging {
  --mtp-bar-fill: var(--mtp-active);
}
mtp-play .mtp-play-button {
  position: relative; flex: none;
  display: grid; place-items: center;
  width: 2rem; height: 2rem; padding: 0; border: 0; border-radius: 50%;
  background: var(--mtp-active); color: var(--surface-page, white);
  cursor: pointer;
  transition: background-color 0.12s ease;
}
mtp-play .mtp-play-button svg { width: 1rem; height: 1rem; fill: currentColor; }
mtp-play .mtp-play-button.mtp-replay svg {
  fill: none; stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round;
}
mtp-play .mtp-play-button:hover {
  background: color-mix(in srgb, var(--mtp-active) 85%, var(--text-body, black));
}
mtp-play .mtp-indicator { flex: 1; min-width: 0; }
/* The bars are thin, but the area that takes a press is 2rem tall, and reaches a little above
   and below that for a finger. */
mtp-play .mtp-bars {
  position: relative; display: flex; align-items: center; gap: 0.25rem;
  height: 2rem; cursor: pointer; touch-action: none; border-radius: 4px;
}
mtp-play .mtp-bars::after { content: ""; position: absolute; inset: -6px 0; }
mtp-play .mtp-bars[aria-disabled="true"] { cursor: not-allowed; opacity: 0.5; }
mtp-play .mtp-bar {
  --u: 0;
  position: relative;
  flex: 1 1 0; min-width: 0.25rem; height: 0.25rem; border-radius: 999px;
  background: linear-gradient(to right, var(--mtp-bar-fill) calc(var(--u) * 100%),
    var(--mtp-bar-track) calc(var(--u) * 100%));
}
mtp-play[data-mtp-exploring] .mtp-bar { opacity: 0.45; }
/* The knob sits on the bar it is in, where its fill ends, as the slider's does. */
mtp-play .mtp-knob {
  position: absolute; top: 50%; left: calc(var(--u) * 100%); z-index: 1;
  width: 16px; height: 16px; box-sizing: border-box; border-radius: 50%;
  background: var(--mtp-bar-fill); border: 2px solid var(--surface-page, white);
  box-shadow: 0 0 0 1px var(--border-primary);
  transform: translate(-50%, -50%); pointer-events: none;
}
mtp-play .mtp-knob.mtp-end { transform: translate(-100%, -50%); }
mtp-play .mtp-knob.mtp-empty {
  left: 0; transform: translate(0, -50%);
  background: var(--surface-page, white); border-color: var(--mtp-bar-fill); box-shadow: none;
}
mtp-play .mtp-exploring {
  position: absolute; left: 50%; top: 50%; z-index: 1; transform: translate(-50%, -50%);
  font-size: 0.8125rem; font-weight: 700; line-height: 1.2; white-space: nowrap;
  padding: 0.2rem 0.65rem; border-radius: 999px;
  background: var(--mtp-active); color: var(--surface-page, white);
  pointer-events: none;
}
mtp-play .mtp-exploring[hidden] { display: none; }
/* The count and the step's label after the bars. Every state's text is laid in one grid cell,
   the others hidden, so the room is as wide as the longest. */
mtp-play .mtp-after {
  flex: none; display: grid; align-items: center; min-width: 2.5rem;
  font-size: 0.875rem; font-variant-numeric: tabular-nums; color: var(--text-subtle); white-space: nowrap;
}
mtp-play .mtp-after > * { grid-area: 1 / 1; }
mtp-play .mtp-count-room { visibility: hidden; }

/* A stepper: "‹", a dot per step, then "›", the buttons drawn as a play's. A passed step's dot is
   solid, the current one solid with a ring, and one still to come pale. The dots are drawn as the
   play's bars are: in the rest color, and the active one while a step plays or a part has focus. */
mtp-stepper {
  display: inline-flex; align-items: center; gap: 0.75rem;
  --mtp-dot: var(--mtp-rest);
}
mtp-stepper[data-mtp-playing], mtp-stepper:has(:focus-visible) { --mtp-dot: var(--mtp-active); }
mtp-stepper .mtp-step-button {
  position: relative; flex: none;
  display: grid; place-items: center;
  width: 2rem; height: 2rem; padding: 0; border: 0; border-radius: 50%;
  background: var(--mtp-active); color: var(--surface-page, white);
  cursor: pointer;
  transition: background-color 0.12s ease;
}
mtp-stepper .mtp-step-button svg {
  width: 1rem; height: 1rem;
  fill: none; stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round;
}
mtp-stepper .mtp-count {
  flex: none; min-width: 2.5rem; text-align: right;
  font-size: 0.8125rem; color: var(--text-subtle); font-variant-numeric: tabular-nums; white-space: nowrap;
}
mtp-stepper .mtp-step-button:hover:not(:disabled) {
  background: color-mix(in srgb, var(--mtp-active) 85%, var(--text-body, black));
}
/* The dots and the pill reading Exploring share one grid cell, so the dots are never narrower
   than the pill: few dots spread to its width. The pill keeps its room while hidden, so the
   stepper has one width in every state. */
mtp-stepper .mtp-dot-area { display: grid; align-items: center; }
mtp-stepper .mtp-dots {
  grid-area: 1 / 1; display: flex; align-items: center; justify-content: space-between; gap: 10px;
}
mtp-stepper .mtp-exploring {
  grid-area: 1 / 1; justify-self: center; z-index: 1;
  font-size: 0.8125rem; font-weight: 700; line-height: 1.2; white-space: nowrap;
  padding: 0.2rem 0.65rem; border-radius: 999px;
  background: var(--mtp-active); color: var(--surface-page, white);
  pointer-events: none;
}
mtp-stepper .mtp-exploring[hidden] { display: block; visibility: hidden; }
mtp-stepper .mtp-dot {
  position: relative; flex: none;
  width: 10px; height: 10px; padding: 0; border: 0; border-radius: 50%;
  background: color-mix(in srgb, var(--mtp-dot) 22%, var(--surface-page, white));
  cursor: pointer;
}
/* The dot takes a press 24px across, which reaches a little past the gap to the next. */
mtp-stepper .mtp-dot::after { content: ""; position: absolute; inset: -7px; }
mtp-stepper .mtp-dot.mtp-passed, mtp-stepper .mtp-dot[aria-current="step"] { background: var(--mtp-dot); }
mtp-stepper .mtp-dot[aria-current="step"] {
  box-shadow: 0 0 0 2px var(--surface-page, white), 0 0 0 3.5px var(--mtp-dot);
}
/* In explore mode the dots are dimmed, as a play's bars are, and the count reads – / N. */
mtp-stepper[data-mtp-exploring] .mtp-dot { opacity: 0.45; }

mtp-toggle label {
  display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; cursor: pointer;
}
mtp-toggle input { accent-color: var(--mtp-c); width: 1rem; height: 1rem; margin: 0; }

/* A shape a tap selected, which the next tap moves (the tap alternative to a drag). Chromium
   draws no outline on the shapes inside an SVG, so the ring is a shadow, sized in the view box's
   units (--mtp-unit is one pixel's worth). */
mtp-canvas .mtp-selected {
  --ring: calc(2px * var(--mtp-unit, 1));
  --ring-color: var(--border-action, Highlight);
  filter: drop-shadow(0 0 var(--ring) var(--ring-color)) drop-shadow(0 0 var(--ring) var(--ring-color))
    drop-shadow(0 0 var(--ring) var(--ring-color));
}

/* Quiet mode (mtp-16z). A control tied only to quiet views is folded away; while it folds or
   unfolds it is still drawn, clipped to the height it is passing through. */
:is(mtp-slider, mtp-button, mtp-play, mtp-stepper, mtp-toggle)[data-mtp-folded]:not([data-mtp-folding]) {
  display: none !important;
}
:is(mtp-slider, mtp-button, mtp-play, mtp-stepper, mtp-toggle)[data-mtp-folding] { overflow: hidden; }

/* The switch of a view with a quiet mode: a hand to make it live, a cross to put it back. It sits
   in the view's top right corner, or in the line for a readout or an inline formula, and is drawn
   as the controls are, in their rest color, and their in-use color under the pointer or focus.
   It looks 2rem across and takes a press 44px across. */
:is(mtp-canvas, mtp-display)[data-mtp-mode] { position: relative; }
.mtp-switch {
  position: absolute; top: 0.375rem; right: 0.375rem; z-index: 1;
  display: grid; place-items: center;
  width: 2rem; height: 2rem; padding: 0; margin: 0;
  border: 1px solid var(--border-primary, currentColor); border-radius: 50%;
  background: var(--surface-page, white);
  color: var(--mtp-control-rest, var(--primary-700));
  cursor: pointer;
  transition: color 0.12s ease, border-color 0.12s ease;
}
.mtp-switch::after {
  content: ""; position: absolute; left: 50%; top: 50%;
  width: 44px; height: 44px; transform: translate(-50%, -50%);
}
.mtp-switch:hover, .mtp-switch:active, .mtp-switch:focus-visible {
  color: var(--mtp-control-active, var(--primary-700));
  border-color: currentColor;
}
.mtp-switch:focus-visible { outline: 2px solid var(--border-action, Highlight); outline-offset: 2px; }
.mtp-switch svg {
  width: 1.125rem; height: 1.125rem;
  fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round;
}
.mtp-switch.mtp-switch-inline {
  position: relative; top: auto; right: auto;
  display: inline-grid; vertical-align: middle; margin-inline-start: 0.375em;
  width: 1.5rem; height: 1.5rem;
}
.mtp-switch.mtp-switch-inline svg { width: 0.875rem; height: 0.875rem; }

@media (prefers-reduced-motion: reduce) {
  mtp-button button, mtp-play .mtp-play-button, mtp-stepper .mtp-step-button, .mtp-switch { transition: none; }
}
`;
