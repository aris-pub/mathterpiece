```{include} ../page-interface.md
```

## Listeners in views

This rule exists so that a listener acts only in the view where the reader can see what it acts on.

```{rule} listeners-in-views
The runtime triggers a listener only for events in the view in whose body the listener is written.
A listener on the view that holds it is written without the name of the view: `(on-view (move …))`,
`(on-pointermove T)`.
```

A listener may be written only in the body of a view, and only in these views:

- in a canvas: a listener on a shape, `on-show`, `on-hide`, `on-view`, `on-ready`, `on-live`,
  `on-quiet` and `on-pointermove`
- in a display: a listener on a term of its formula, `on-live` and `on-quiet`
- in a readout: `on-live` and `on-quiet`.

A listener may not be written at the top level, and has no `(in …)`. A control is written at the
top level, and may hold `(in …)` with the names of the views that it belongs to.
