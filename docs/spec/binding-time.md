# Binding time and access

:::{note}
Not drafted yet. This page defines: what is known when compiling and what only while drawing, and what may read the scene or the page.
:::

## What may read what

```{rule} what-reads-what
Every expression may read the scene and the formulas. The views, the controls and the listeners
may read each other. No expression in the scene or in a formula reads a view, a control or a
listener.
```

So `(button b (selected (= mode 'a')))` may read `mode`, and a readout may read the value of a
slider's target, but `(circle c (r push.selected))` in the scene, with `push` a button, is a
{term}`compile error`.
