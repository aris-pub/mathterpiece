# Binding time and access

:::{note}
Not drafted yet. This page defines: what is known when compiling and what only while drawing, and what may read the scene or the page.
:::

## What may read what

```{rule} what-reads-what
Every expression may read the scene and the formulas. The views, the controls and the listeners
may read each other. Only an expression in a view, a control or a listener may read a view, a
control or a listener: no expression in the scene, in a formula, or in a variable, a record or a
function outside a component reads one.
```

So `(button b (selected (= mode 'a')))` may read `mode`, and a readout may read the value of a
slider's target, but `(circle c (r push.selected))` in the scene, with `push` a button, is a
{term}`compile error`, and so is `(real r (if push.selected 2 1))` at the top level, since the scene
could read the button through `r`.
