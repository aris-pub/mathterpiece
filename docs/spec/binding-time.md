# Binding time and access

The compiler computes each expression that is known when compiling, in the fold step
({numref}`compile-steps`), and the runtime computes every other expression while drawing
({doc}`evaluation`). This page defines which expressions are known when compiling, and which
expressions may read the scene, the formulas and the page objects.

## Known when compiling

```{rule} known-when-compiling
An expression is known when compiling when it is one of these:

- a literal
- a function declared with `func`, or a built-in function
- a name that refers to an object, such as a shape or a record
- a const container, unless it is a color variable or a font
- a bound container whose expression is known when compiling, unless it is a color variable or a font
- the name of a `let` or a `foreach`, in each copy, when the value bound to it is known when compiling
- a parameter, in a call or a declaration whose argument for it is known when compiling
- a form whose evaluated parts are all known when compiling, unless it is a call of `rand`,
  `rand-int`, `pick` or `shuffle`

Every other expression is known only while drawing.
```

So a free container is known only while drawing, since a writer may write it, and so is every
expression that reads one. A color variable and a font are known only while drawing, since the page
may give them other values through its CSS ({numref}`mtpc-only-boundary`). A random value is known
only while drawing ({numref}`random-never-folded`).

```mtp
(real a 1)              ; free: known only while drawing
(real c 3 (const))      ; const: known when compiling
(real d (* 2 c))        ; bound to an expression known when compiling: known when compiling, and folded to 6
(real e (* 2 a))        ; bound to an expression that reads a free variable: known only while drawing
(color ink #'navy')     ; a color variable: known only while drawing
```

## `foreach` and `free`

```{rule} foreach-copies
A `foreach` over a list whose length is known when compiling ({numref}`known-lengths`) makes one
copy of its items for each item of the list, in the expand step ({numref}`compile-steps`). A
`foreach` over a list whose length is known only while drawing makes its copies by
{numref}`foreach-bounded-length`.
```

```{rule} free-starting-value
`(free X)` is the starting value of a free container: the value of X when the page opens. It is
computed once, in the fold step when X is known when compiling, and otherwise when the page opens,
and it does not update when X changes. The container is free either way.
```

So with `(real c 3 (const))`, `(real r free@(* 2 c))` starts at 6, and a slider may write it.
`(list[int] order free@(shuffle (range 16)))` starts in an order that is drawn when the page opens,
and keeps it until a writer writes `order`.

## What may read what

```{rule} what-reads-what
Every expression may read the scene and the formulas. The views, the controls and the listeners
may read each other. Only an expression in a view, a control or a listener may read a view, a
control or a listener: no expression in the scene, in a formula, or in a variable, a record or a
function outside a {term}`page object` may read one.
```

So `(button b (move k (to 1) (duration 1)) (active (= mode 'a')))` may read `mode`, and a readout may read the variable that
a slider writes, but `(circle c (r size.position))` in the scene, with `size` a slider, is a
{term}`compile error`, and so is `(real r (if (> size.position 2) 2 1))` at the top level, since the
scene could read the slider through `r`.
