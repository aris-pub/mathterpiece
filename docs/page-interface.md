# Page interface of views and controls

Status: approved by the author, 2026-11-13. Not built yet.

## Rules

1. **Reading.** Each element (`mtp-model`, every view and every control) shows its own page
   state on itself as `data-mtp-…` attributes: present or absent for a yes/no state, a value
   otherwise. Every change of its page state fires one `mtp-state` event on that element.
2. **Scene values** are not page state. They are never shown as attributes. A script reads them
   from `<mtp-model>` and never writes them.
3. **Driving.** A script acts on an element only through its inputs, as a reader does. Each piece
   of an element the reader presses, clicks or drags is an input and carries
   `data-mtp-input="name"`, the name unique within its element. No element has methods that
   change it. To start again, a script reloads the page.
4. **Names.** Every attribute carries the `data-mtp-` prefix.

## What follows for each kind

| Element | Attributes (each `data-mtp-…`) | Inputs (`data-mtp-input=…`) |
|---|---|---|
| `mtp-model` (the page) | `ready` | none |
| canvas, display, readout | `ready`, `seen`, `mode` (`quiet` or `live`) | `switch` (the hand) |
| button | `inactive` | `button` |
| toggle | `inactive` | `box` |
| slider | `inactive`, `held` | `track` |
| play | `inactive`, `step`, `playing`, `exploring` | `button`, `bar-1` to `bar-N` |
| stepper | `inactive`, `step`, `playing`, `exploring` | `back`, `next`, `dot-1` to `dot-N` |

`inactive` is present while a control's `(active bool)` does not hold. `step` is 0 in explore
mode, and `exploring` is present then.

## Events

`mtp-state` on each element replaces `mtp-mode` and `mtp-rest`. On `<mtp-model>`, `mtp-change`
stays, and the old `mtp-ready` (the model has loaded) is renamed `mtp-loaded`: both are about
the model and the scene, not page state.

During `mtp-state` on a play or a stepper, its `step` and `playing` values read from
`<mtp-model>` already match its attributes, or for copies, the attributes of the copy that moved
the scene last.
