# Lifecycle of a canvas

Status: decided by the author on 2026-11-13. Later the same day, he renamed rest to ready and made
ready a moment. Not built yet. This page defines the lifecycle of a canvas, a display and a
readout, and the listeners `on-view` and `on-ready` of a canvas.

## Timeline

```{mermaid}
:caption: The timeline of a canvas and of its listeners on-view and on-ready.
:name: canvas-timeline

sequenceDiagram
  participant Page
  participant Copy as Canvas copy
  participant Scene
  Page->>Copy: page loads
  Note over Copy,Scene: state -1: the values at page load
  Copy->>Copy: first comes into view
  Copy->>Scene: on-view is triggered (priority 1000)
  Note over Copy,Scene: state 0: the values when on-view ends.<br/>Copy is ready: data-mtp-ready, mtp-state.<br/>Still images are captured now.
  Copy->>Scene: on-ready is triggered (priority 300)
```

A canvas with no `on-view` has no state -1: the values at page load are its state 0, it is
ready from the start, and its `on-ready` is triggered when the page loads.

## Rules

1. **State -1** of a canvas copy consists of the values at page load. It exists only when the
   canvas has an `on-view`.
2. **`on-view`** is triggered when the copy first comes into view, if the scene still has the
   values at page load. Otherwise it is not triggered.
3. **State 0** consists of exactly the values after the movement of the `on-view` has run from the
   values at page load.
4. **Ready:** a canvas is ready, in every copy at once, from the first moment the `on-view` of one
   of its copies has ended, or from page load if it has no `on-view`. It stays ready from then
   on. Ready is a moment, not a comparison of values. A copy whose `on-view` is not triggered,
   because its values had already changed, is ready because its canvas is ready.
5. **`on-view`** has priority 1000. Until a canvas is ready, every input that belongs to it is
   disabled, and each is enabled once the canvas is ready. An input belongs to a canvas when it is
   a listener inside the body of the canvas, or a control that writes to a container on which a shape
   drawn in the canvas depends (the compiler finds these controls).
6. **`on-ready`** is triggered once, when the canvas becomes ready. Its movement may be any
   movement. It has priority 300.
7. **Compile errors:** an `on-view` may not loop, and a movement in an `on-view` may not have a `to`
   expression that depends on the target of the movement.
8. **Still images** are captured at the moment a canvas becomes ready.
9. **The page is ready** once every canvas, display and readout on it is ready. A display or a
   readout has no `on-view`, so it is ready from the start. The page is static: no view or control
   is added to or removed from it after it loads.
10. **On the page** (docs/page-interface.md): each copy has `data-mtp-ready` once it is ready, and
   the runtime fires `mtp-state` on it at that moment. `<mtp-model>` has `data-mtp-ready` once the
   page is ready. The event `mtp-ready` of the model, which meant that the model had loaded, is
   renamed `mtp-loaded`.
11. **`on-show` and `on-hide`** are not part of the lifecycle (the author, 2026-11-14): no listener
   but the `on-view` is triggered before state 0, a canvas becomes ready without waiting for
   them, and they are triggered only when the runtime starts or stops drawing a shape in a copy
   after state 0.
