```{include} ../page-interface.md
```

## Listeners in views

```{rule} listeners-in-views
A listener acts only on what happens in the view in whose body it is written. A listener on its
own view leaves out the name of the view: `(on-view (animation …))`, `(on-pointermove target)`.
```

Each listener is written in the body of one kind of view: a listener on a
shape, `on-show`, `on-hide`, `on-view`, `on-ready`, `on-live`, `on-quiet` and `on-pointermove` in a
canvas, a listener on a term of a formula, `on-live` and `on-quiet` in a display, and `on-live` and
`on-quiet` in a readout. A listener is never written at the top level and has no `(in …)`, while a
control is written at the top level and names the views that it belongs to with `(in …)`.
