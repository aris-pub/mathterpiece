# Binding time and access

The compiler computes each expression that is known when compiling, in the fold step
({numref}`compile-steps`), and the runtime computes every other expression while drawing
({doc}`evaluation`). This page defines which expressions are known when compiling, and which
expressions may read the scene, the formulas and the page objects.

## Known when compiling

This rule exists to decide which expressions the compiler computes and which it leaves to the runtime.

```{rule} known-when-compiling
An expression is known when compiling when it is:

- a literal
- a function declared with `func`, or a built-in function
- a name that refers to an object
- a const container
- a bound container whose expression is known when compiling, unless it is a font
- a `let` or `foreach` name whose value is known when compiling, in each copy
- a parameter whose argument is known when compiling
- a form whose evaluated parts are all known when compiling, except a call of `rand`, `rand-int`,
  `choice` or `shuffled`

Every other expression is known only while drawing.
```

So a free container is known only while drawing, since a writer may write to it, and so is every
expression that reads one. A font is known only while drawing, since the page
may give it other values through its CSS ({numref}`mtpc-only-boundary`). A random value is known
only while drawing ({numref}`random-never-folded`).

```mtp
(real a 1)              ; free: known only while drawing
(real c 3 (const))      ; const: known when compiling
(real d (* 2 c))        ; bound to an expression known when compiling: known when compiling, and folded to 6
(real e (* 2 a))        ; bound to an expression that reads a free variable: known only while drawing
```

## `foreach` and `free`

This rule exists to specify when the copies of a `foreach` are made.

```{rule} foreach-copies
A `foreach` over a list of length known when compiling ({numref}`known-lengths`) makes one copy of its
items per item, in the expand step ({numref}`compile-steps`). Otherwise it makes its copies by
{numref}`foreach-bounded-length`.
```

This rule exists to specify when the starting value of a free container is computed, since it never updates after.

```{rule} free-starting-value
`(free X)` is the starting value of a free container: the value of X when the page opens, computed
once, in the fold step when X is known when compiling and otherwise when the page opens. It does not
update when X changes, and the container is free either way.
```

So with `(real c 3 (const))`, `(real r free@(* 2 c))` starts at 6, and a slider may write to it.
`(list[int] order free@(shuffled (range 16)))` starts in an order that is drawn when the page opens,
and keeps it until a writer writes to `order`.

## What may read what

This rule exists so that a world model means the same whatever page shows it, since the scene and the formulas may read nothing that belongs to a page.

```{rule} what-reads-what
Every expression may read the scene and the formulas. Only an expression in a view, a control or a
listener may read a view, a control or a listener.
```

So `(button b (active (= mode 'a')))` may read `mode`, and a readout may read the variable that
a slider writes to, but `(circle c (r size.position))` in the scene, with `size` a slider, is a
{term}`compile error`, and so is `(real r (if (> size.position 2) 2 1))` at the top level, since the
scene could read the slider through `r`.
