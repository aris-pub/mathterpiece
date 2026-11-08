// How mtp's controls look. They are drawn with BRAIID, the design system of RSM documents, and
// read its tokens, so a figure in an RSM document takes the document's accent, surfaces and dark
// mode. A page that shows controls must load braiid.css. Their font is the interface's, as in
// Studio, not the document's, so they look the same whatever typeface the reader picks.

export const CONTROLS_CSS = `
mtp-slider, mtp-button, mtp-play, mtp-toggle {
  font-family: "Source Sans 3", sans-serif;
  color: var(--text-body);
}

/* A control is drawn in one color at rest and another while the reader uses it: pressing,
   dragging, focused from the keyboard, or a play playing. A page sets them with
   --mtp-control-rest and --mtp-control-active; where it sets neither, both are BRAIID's accent,
   as before there were two. --mtp-c is the one a control draws with now. */
mtp-slider, mtp-button, mtp-play {
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
mtp-button button::after, mtp-play .mtp-play-button::after {
  content: ""; position: absolute; inset: -6px;
}
mtp-button button:hover {
  background: var(--surface-hover); border-color: var(--primary-300);
}
mtp-button button:active { background: var(--gray-100); }
mtp-button button:focus-visible, mtp-play .mtp-play-button:focus-visible,
mtp-play .mtp-bars:focus-visible {
  outline: 2px solid var(--border-action, Highlight); outline-offset: 2px;
}
mtp-button button:disabled, mtp-play .mtp-play-button:disabled { cursor: not-allowed; opacity: 0.5; }

/* A play: the button, then the bars, one per step, with the step playing under them. The bars
   sit on a track of their own color, so at rest they read as a tour not yet played rather than as
   a control turned off. The button is the active color even at rest: it is what the reader
   presses first, and a rest color such as a gray would make it look turned off. */
mtp-play {
  display: flex; align-items: flex-start; gap: 0.75rem; min-width: 16rem;
  --mtp-bar-track: color-mix(in srgb, var(--text-body, currentColor) 20%, transparent);
  --mtp-bar-fill: var(--mtp-rest);
}
mtp-play[data-playing], mtp-play:has(:focus-visible), mtp-play .mtp-bars.mtp-dragging {
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
mtp-play .mtp-play-button:hover {
  background: color-mix(in srgb, var(--mtp-active) 85%, var(--text-body, black));
}
mtp-play .mtp-indicator { flex: 1; min-width: 0; display: grid; gap: 0.125rem; }
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
  flex: 1 1 0; min-width: 0.25rem; height: 0.25rem; border-radius: 999px;
  background: linear-gradient(to right, var(--mtp-bar-fill) calc(var(--u) * 100%),
    var(--mtp-bar-track) calc(var(--u) * 100%));
}
mtp-play .mtp-now {
  font-size: 0.8125rem; line-height: 1.25; color: var(--text-subtle);
  font-variant-numeric: tabular-nums; min-height: 1.25em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

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

@media (prefers-reduced-motion: reduce) {
  mtp-button button, mtp-play .mtp-play-button { transition: none; }
}
`;
