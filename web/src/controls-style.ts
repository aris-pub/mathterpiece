// How mtp's controls look. They are drawn with BRAIID, the design system of RSM documents, and
// read its tokens, so a figure in an RSM document takes the document's accent, surfaces and dark
// mode. A page that shows controls must load braiid.css. Their font is the interface's, as in
// Studio, not the document's, so they look the same whatever typeface the reader picks.

// The jumpers (docs/spec/controls.md) are listed apart, since they share parts that the other controls do not have.
const JUMPERS = "mtp-slider, mtp-range-slider, mtp-dial, mtp-number-field, mtp-text-field, mtp-select, mtp-multi-select";
const ALL = `${JUMPERS}, mtp-button, mtp-play, mtp-stepper, mtp-toggle`;

/** The labels on which the runtime draws a checkbox or a radio button, each followed by tail. */
const marks = (tail: string) => `mtp-toggle label${tail}, :is(mtp-select, mtp-multi-select) .mtp-mark${tail}`;

export const CONTROLS_CSS = `
${ALL} {
  font-family: "Source Sans 3", sans-serif;
  color: var(--text-body);
}

/* A control is drawn in one color at rest and another while the reader uses it: pressing,
   dragging, focused from the keyboard, or a play playing. A page sets them with
   --mtp-control-rest and --mtp-control-active; where it sets neither, both are BRAIID's accent,
   as before there were two. --mtp-c is the one a control draws with now. */
${JUMPERS}, mtp-button, mtp-play, mtp-stepper {
  --mtp-rest: var(--mtp-control-rest, var(--primary-700));
  --mtp-active: var(--mtp-control-active, var(--primary-700));
}
mtp-toggle {
  --mtp-rest: var(--mtp-control-rest, var(--primary-600));
  --mtp-active: var(--mtp-control-active, var(--primary-600));
}
mtp-slider input, mtp-button button { --mtp-c: var(--mtp-rest); }
mtp-slider input:active, mtp-slider input:focus-visible,
mtp-button button:active, mtp-button button:focus-visible { --mtp-c: var(--mtp-active); }

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

mtp-toggle { --mtp-hilite: var(--primary-200, #bae3fd); }
mtp-toggle label {
  display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; cursor: pointer;
}

/* The checkbox of a toggle and of a multi-select of kind 'checkbox', and the radio button of a
   select of kind 'radio', drawn in the design that the author approved on 2026-11-22: off, an
   empty box outlined in the line color, and on, a box in the highlight color outlined in the
   active color, with a check mark, a dot for a radio button, or a bar for a mixed toggle. The
   browser's own box is not used, since accent-color cannot draw this. The native input stays in
   the page, unseen and over the drawn box, so that the keyboard and screen readers still reach it
   and a press on the box reaches it through its label. The states are in :where(), so that a
   page that draws the box itself, as Firsthand Math does for its toggle, wins over every one. */
${marks(" input")} {
  position: absolute; left: 0; top: 50%; width: 16px; height: 16px; margin: 0;
  transform: translateY(-50%); opacity: 0; pointer-events: none;
}
${marks("")} { position: relative; }
${marks("::before")} {
  content: ""; flex: none; box-sizing: border-box; width: 16px; height: 16px; border-radius: 3px;
  border: 1px solid var(--border-primary); background: var(--surface-page);
}
mtp-select .mtp-mark::before { border-radius: 50%; }
${marks(":where(:hover)::before")} { border-color: var(--primary-300); }
${marks(":where(:has(input:checked, input:indeterminate))::before")} {
  background: var(--mtp-hilite); border-color: var(--mtp-active);
}
${marks(":where(:has(input:focus-visible))::before")} {
  outline: 2px solid var(--border-action, Highlight); outline-offset: 2px;
}
/* The check mark is two sides of a small box, turned 45 degrees, so that it does not hang on a
   font. */
mtp-toggle label:where(:has(input:checked))::after, mtp-multi-select .mtp-mark:where(:has(input:checked))::after {
  content: ""; position: absolute; left: 5px; top: 50%; width: 4px; height: 8px; box-sizing: content-box;
  border: solid var(--mtp-active); border-width: 0 2px 2px 0; transform: translateY(-60%) rotate(45deg);
}
mtp-toggle label:where(:has(input:indeterminate))::after {
  content: ""; position: absolute; left: 4px; top: 50%; width: 8px; height: 2px; border-radius: 1px;
  transform: translateY(-50%); background: var(--mtp-active);
}
mtp-select .mtp-mark:where(:has(input:checked))::after {
  content: ""; position: absolute; left: 5px; top: 50%; width: 6px; height: 6px; border-radius: 50%;
  transform: translateY(-50%); background: var(--mtp-active);
}
${marks(":where(:has(input:disabled))")} { cursor: not-allowed; opacity: 0.5; }

/* The jumpers (docs/spec/controls.md), drawn from the parts that the author chose on 2026-11-22
   (the Near BRAIID look, option A for every part): a label in the text color, a track of a 1px
   line with a 2px fill, a raised thumb with a dot in its middle that grows while it is held, short
   ticks with their values, boxes and buttons outlined as a button is, and the chosen option in the
   highlight color. Each draws in its rest color, and in its active color while the reader holds
   it or it has the focus from the keyboard, as the other controls do. */
:is(${JUMPERS}) {
  --mtp-c: var(--mtp-rest);
  --mtp-thumb: light-dark(#ffffff, #38454f);
  --mtp-thumb-shadow: light-dark(rgb(0 0 0 / 0.25), rgb(0 0 0 / 0.6));
  --mtp-hilite: var(--primary-200, #bae3fd);
  --mtp-error: var(--text-error, #d92d20);
}
:is(${JUMPERS}):is([data-mtp-held], :has(:focus-visible)) { --mtp-c: var(--mtp-active); }
:is(${JUMPERS}) .mtp-jumper { display: flex; flex-direction: column; gap: 0.25rem; }
:is(${JUMPERS}) .mtp-label {
  font-size: 0.875rem; font-weight: 600; color: var(--text-body);
}
mtp-slider:has(.mtp-track), mtp-range-slider { display: inline-block; min-width: 12rem; }

/* A straight track. The thumb's center runs from half a thumb in from each end, and --a and --b
   are where the fill starts and ends, from 0 to 1. */
:is(${JUMPERS}) .mtp-track {
  --a: 0; --b: 0;
  position: relative; height: 1.5rem; cursor: pointer; touch-action: none;
}
:is(${JUMPERS}) .mtp-track::before {
  content: ""; position: absolute; left: 8px; right: 8px; top: 50%;
  height: 1px; transform: translateY(-50%); background: var(--border-primary);
}
:is(${JUMPERS}) .mtp-fill {
  position: absolute; top: 50%; height: 2px; transform: translateY(-50%); border-radius: 1px;
  left: calc(8px + var(--a) * (100% - 16px)); width: calc((var(--b) - var(--a)) * (100% - 16px));
  background: var(--mtp-c);
}
:is(${JUMPERS}) .mtp-thumb {
  position: absolute; top: 50%; left: calc(8px + var(--u, 0) * (100% - 16px)); z-index: 1;
  width: 16px; height: 16px; box-sizing: border-box; border-radius: 50%;
  transform: translate(-50%, -50%);
  background: var(--mtp-thumb);
  box-shadow: 0 1px 3px var(--mtp-thumb-shadow), 0 0 0 1px var(--border-primary);
  cursor: grab; touch-action: none;
}
/* A larger area than the thumb draws, for 44px touch targets. */
:is(${JUMPERS}) .mtp-thumb::before { content: ""; position: absolute; inset: -14px; border-radius: 50%; }
:is(${JUMPERS}) .mtp-thumb::after {
  content: ""; position: absolute; left: 50%; top: 50%;
  width: 6px; height: 6px; border-radius: 50%; transform: translate(-50%, -50%);
  background: var(--mtp-c);
  transition: width 0.12s ease, height 0.12s ease;
}
:is(${JUMPERS})[data-mtp-held] .mtp-thumb:focus::after, :is(${JUMPERS}) .mtp-thumb:active::after { width: 10px; height: 10px; }
:is(${JUMPERS})[data-mtp-held] .mtp-thumb:focus { cursor: grabbing; }
:is(${JUMPERS}) .mtp-thumb:focus-visible { outline: 2px solid var(--border-action, Highlight); outline-offset: 2px; }
:is(${JUMPERS}) [data-disabled], :is(${JUMPERS}) :disabled { cursor: not-allowed; opacity: 0.5; }
:is(${JUMPERS}) [data-disabled] .mtp-thumb { cursor: not-allowed; }

/* The ticks under a track, each where the thumb's center stands for its value, with the value
   under it. */
:is(${JUMPERS}) div.mtp-ticks {
  position: relative; height: 1.25rem; margin-top: -0.25rem;
  font-size: 0.75rem; color: var(--text-subtle); font-variant-numeric: tabular-nums;
}
:is(${JUMPERS}) div.mtp-ticks:empty { display: none; }
:is(${JUMPERS}) div.mtp-ticks [data-value] {
  position: absolute; top: 0; left: calc(8px + var(--u) * (100% - 16px));
  width: 1px; height: 5px; background: currentColor;
}
:is(${JUMPERS}) div.mtp-ticks [data-value]::after {
  content: attr(data-value);
  position: absolute; top: 6px; left: 50%; transform: translateX(-50%); white-space: nowrap;
}

/* A dial: the ring, the arc from the start to the thumb, the ticks inside the ring as on a clock,
   and the value in the middle. The ring takes a press over a band wider than it draws. */
mtp-dial { display: inline-block; }
mtp-dial .mtp-dial-face { position: relative; width: 7rem; height: 7rem; touch-action: none; }
mtp-dial svg { display: block; width: 100%; height: 100%; overflow: visible; }
mtp-dial .mtp-ring { fill: none; stroke: var(--border-primary); stroke-width: 1px; vector-effect: non-scaling-stroke; }
mtp-dial .mtp-arc {
  fill: none; stroke: var(--mtp-c); stroke-width: 2px; stroke-linecap: round; vector-effect: non-scaling-stroke;
}
mtp-dial .mtp-tick { stroke: var(--text-subtle); stroke-width: 1px; vector-effect: non-scaling-stroke; }
mtp-dial .mtp-ring-hit { fill: none; stroke: transparent; stroke-width: 18; pointer-events: stroke; cursor: pointer; }
mtp-dial [data-disabled] .mtp-ring-hit { cursor: not-allowed; }
mtp-dial .mtp-dial-value {
  position: absolute; inset: 0; display: grid; place-items: center; pointer-events: none;
  font-size: 0.875rem; font-weight: 600; color: var(--mtp-rest); font-variant-numeric: tabular-nums;
}

/* A number field and a text field: the label above a box outlined as a button is. A number
   field's label, and its value when it has neither buttons nor typing, can be dragged sideways. */
:is(mtp-number-field, mtp-text-field) { display: inline-block; }
:is(mtp-number-field, mtp-text-field) .mtp-box {
  display: inline-flex; align-items: center; align-self: flex-start;
  min-height: 2rem; box-sizing: border-box;
  border: 1px solid var(--border-primary); border-radius: var(--radius-lg, 0.5rem);
  background: var(--surface-page);
  transition: border-color 0.12s ease, box-shadow 0.12s ease;
}
:is(mtp-number-field, mtp-text-field) .mtp-box:has(:focus-visible) {
  outline: 2px solid var(--border-action, Highlight); outline-offset: 2px;
}
:is(mtp-number-field, mtp-text-field) .mtp-box.mtp-refused {
  border-color: var(--mtp-error); box-shadow: 0 0 0 1px var(--mtp-error);
}
:is(mtp-number-field, mtp-text-field) .mtp-box input {
  font: 600 0.875rem/1.2 "Source Sans 3", sans-serif; font-variant-numeric: tabular-nums;
  width: 5rem; padding: 0.375rem 0.5rem; margin: 0; border: 0; outline: none;
  background: transparent; color: var(--mtp-rest); text-align: center;
}
mtp-text-field { min-width: 14rem; }
mtp-text-field .mtp-box { display: flex; align-self: stretch; }
mtp-text-field .mtp-box input { flex: 1; width: auto; min-width: 0; font-weight: 400; color: var(--text-body); text-align: left; }
mtp-number-field .mtp-value {
  padding: 0.375rem 0.5rem; min-width: 2.5rem; text-align: center;
  font: 600 0.875rem/1.2 "Source Sans 3", sans-serif; font-variant-numeric: tabular-nums; color: var(--mtp-rest);
}
mtp-number-field .mtp-value:focus-visible { outline: none; }
mtp-number-field .mtp-box:not(:has(button)):has(.mtp-scrub) { border-color: transparent; background: none; }
mtp-number-field .mtp-scrub { text-decoration: underline dotted; text-underline-offset: 3px; }
mtp-number-field .mtp-scrubber { cursor: ew-resize; touch-action: none; user-select: none; -webkit-user-select: none; }
mtp-number-field .mtp-field-button {
  position: relative; flex: none; display: grid; place-items: center;
  width: 2rem; height: 2rem; padding: 0; margin: -1px; border: 0; border-radius: var(--radius-lg, 0.5rem);
  background: transparent; color: var(--mtp-c);
  font: 600 1rem/1 "Source Sans 3", sans-serif; cursor: pointer;
  transition: background-color 0.12s ease;
}
mtp-number-field .mtp-field-button:hover:not(:disabled) { background: var(--surface-hover); }
mtp-number-field .mtp-field-button:active:not(:disabled) { background: var(--mtp-hilite); }
/* What a screen reader is told of a refused commit, unseen. */
:is(${JUMPERS}) .mtp-live {
  position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap;
}

/* A select and a multi-select: a menu button that opens a list, a row of connected buttons, or one
   radio button or checkbox per line. */
:is(mtp-select, mtp-multi-select) { display: inline-block; }
:is(mtp-select, mtp-multi-select) .mtp-menu { position: relative; align-self: flex-start; }
:is(mtp-select, mtp-multi-select) .mtp-menu-button, :is(mtp-select, mtp-multi-select) .mtp-segment {
  position: relative;
  font: 600 0.875rem/1.2 "Source Sans 3", sans-serif;
  padding: 0.375rem 0.75rem; margin: 0;
  border: 1px solid var(--border-primary); border-radius: var(--radius-lg, 0.5rem);
  background: var(--surface-page); color: var(--mtp-c);
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}
:is(mtp-select, mtp-multi-select) .mtp-menu-button {
  display: inline-flex; align-items: center; justify-content: space-between; gap: 0.5rem;
  min-width: 8rem; min-height: 2rem; text-align: left;
}
:is(mtp-select, mtp-multi-select) .mtp-menu-button svg {
  flex: none; width: 1rem; height: 1rem;
  fill: none; stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round;
}
/* With nothing chosen, the button shows the label in a quieter color, so that the label does not
   look like a chosen option. */
:is(mtp-select, mtp-multi-select) .mtp-placeholder { color: var(--text-subtle); }
:is(mtp-select, mtp-multi-select) :is(.mtp-menu-button, .mtp-segment):hover:not(:disabled) {
  background: var(--surface-hover); border-color: var(--primary-300);
}
:is(mtp-select, mtp-multi-select) :is(.mtp-menu-button, .mtp-segment, .mtp-listbox):focus-visible {
  outline: 2px solid var(--border-action, Highlight); outline-offset: 2px; z-index: 2;
}
:is(mtp-select, mtp-multi-select) .mtp-listbox {
  position: absolute; z-index: 10; top: calc(100% + 4px); left: 0; min-width: 100%; box-sizing: border-box;
  padding: 0.25rem; border: 1px solid var(--border-primary); border-radius: var(--radius-lg, 0.5rem);
  background: var(--surface-page); box-shadow: 0 4px 12px var(--mtp-thumb-shadow);
}
:is(mtp-select, mtp-multi-select) .mtp-listbox[hidden] { display: none; }
:is(mtp-select, mtp-multi-select) .mtp-option {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.375rem 0.625rem; border-radius: calc(var(--radius-lg, 0.5rem) - 2px);
  font-size: 0.875rem; white-space: nowrap; cursor: pointer;
}
:is(mtp-select, mtp-multi-select) .mtp-option:is(:hover, .mtp-active) { background: var(--surface-hover); }
:is(mtp-select, mtp-multi-select) .mtp-option[aria-selected="true"] { color: var(--mtp-rest); font-weight: 600; }
mtp-multi-select .mtp-option::before {
  content: ""; flex: none; width: 1rem; height: 1rem; box-sizing: border-box;
  border: 1px solid var(--border-primary); border-radius: 3px;
}
mtp-multi-select .mtp-option[aria-selected="true"]::before {
  content: "\\2713"; display: grid; place-items: center; font-size: 0.75rem; line-height: 1;
  background: var(--mtp-hilite); border-color: var(--mtp-rest); color: var(--mtp-rest);
}
:is(mtp-select, mtp-multi-select) .mtp-segments { display: inline-flex; align-self: flex-start; }
:is(mtp-select, mtp-multi-select) .mtp-segment { border-radius: 0; margin-left: -1px; }
:is(mtp-select, mtp-multi-select) .mtp-segment:first-child {
  margin-left: 0; border-radius: var(--radius-lg, 0.5rem) 0 0 var(--radius-lg, 0.5rem);
}
:is(mtp-select, mtp-multi-select) .mtp-segment:last-child {
  border-radius: 0 var(--radius-lg, 0.5rem) var(--radius-lg, 0.5rem) 0;
}
:is(mtp-select, mtp-multi-select) .mtp-segment:only-child { border-radius: var(--radius-lg, 0.5rem); }
:is(mtp-select, mtp-multi-select) .mtp-segment:is([aria-checked="true"], [aria-pressed="true"]) {
  z-index: 1; background: var(--mtp-hilite); border-color: var(--mtp-rest);
}
:is(mtp-select, mtp-multi-select) .mtp-marks { display: flex; flex-direction: column; gap: 0.375rem; }
:is(mtp-select, mtp-multi-select) .mtp-mark { display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; cursor: pointer; }

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
:is(${ALL})[data-mtp-folded]:not([data-mtp-folding]) {
  display: none !important;
}
:is(${ALL})[data-mtp-folding] { overflow: hidden; }

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
  mtp-button button, mtp-play .mtp-play-button, mtp-stepper .mtp-step-button, .mtp-switch,
  :is(${JUMPERS}) :is(.mtp-thumb::after, .mtp-box, .mtp-segment, .mtp-menu-button, .mtp-field-button) { transition: none; }
}
`;
