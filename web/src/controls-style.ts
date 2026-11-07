// How mtp's controls look. They are drawn with BRAIID, the design system of RSM documents, and
// read its tokens, so a figure in an RSM document takes the document's accent, surfaces and dark
// mode. A page that shows controls must load braiid.css. Their font is the interface's, as in
// Studio, not the document's, so they look the same whatever typeface the reader picks.

export const CONTROLS_CSS = `
mtp-slider, mtp-button, mtp-play, mtp-toggle {
  font-family: "Source Sans 3", sans-serif;
  color: var(--text-body);
}

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
    var(--primary-700) calc(8px + var(--u) * (100% - 16px)),
    var(--border-primary) calc(8px + var(--u) * (100% - 16px)));
}
mtp-slider input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 16px; height: 16px; margin-top: -6px; border-radius: 50%;
  background: var(--primary-700); border: 2px solid var(--surface-page);
  box-shadow: 0 0 0 1px var(--border-primary);
}
mtp-slider input[type="range"]::-moz-range-track {
  height: 4px; border-radius: 999px; background: var(--border-primary);
}
mtp-slider input[type="range"]::-moz-range-progress {
  height: 4px; border-radius: 999px; background: var(--primary-700);
}
mtp-slider input[type="range"]::-moz-range-thumb {
  width: 16px; height: 16px; border-radius: 50%; box-sizing: border-box;
  background: var(--primary-700); border: 2px solid var(--surface-page);
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

mtp-button button, mtp-play button {
  position: relative;
  font: 600 0.875rem/1.2 "Source Sans 3", sans-serif;
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border-primary); border-radius: var(--radius-lg);
  background: var(--surface-page); color: var(--primary-700);
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}
/* A larger area the finger can hit than the button draws, for 44px touch targets. */
mtp-button button::after, mtp-play button::after {
  content: ""; position: absolute; inset: -6px;
}
mtp-button button:hover, mtp-play button:hover {
  background: var(--surface-hover); border-color: var(--primary-300);
}
mtp-button button:active, mtp-play button:active { background: var(--gray-100); }
mtp-button button:focus-visible, mtp-play button:focus-visible {
  outline: 2px solid var(--border-action); outline-offset: 2px;
}
mtp-button button:disabled, mtp-play button:disabled { cursor: not-allowed; opacity: 0.5; }

mtp-play { display: inline-flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
mtp-play .mtp-steps {
  display: inline-flex; overflow: hidden;
  border: 1px solid var(--border-primary); border-radius: var(--radius-md);
}
mtp-play .mtp-steps button {
  border: 0; border-left: 1px solid var(--border-primary); border-radius: 0;
  min-width: 2rem; padding: 0.375rem 0.5rem;
  color: var(--text-body); font-variant-numeric: tabular-nums;
}
mtp-play .mtp-steps button:first-child { border-left: 0; }
mtp-play .mtp-steps button.mtp-lit {
  background: var(--primary-50); color: var(--primary-800);
  box-shadow: inset 0 0 0 1px var(--primary-700);
}

mtp-toggle label {
  display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; cursor: pointer;
}
mtp-toggle input { accent-color: var(--primary-600); width: 1rem; height: 1rem; margin: 0; }

@media (prefers-reduced-motion: reduce) {
  mtp-button button, mtp-play button { transition: none; }
}
`;
