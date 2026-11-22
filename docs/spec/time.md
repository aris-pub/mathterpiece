# Time and animation

:::{note}
Not drafted yet. This page defines moves, movements as functions of time, scores (collections of
movements, each member placed in time by its own lag and repeated with loops), `in-order` and
`at-once` (scores whose members run one after another or together), and animations, which are
templates of movements.
:::

(animation-uses)=
## `(A …)` for an animation `A`

With an animation `C`, `(C A1 … Ak)` creates a `C`, which is a movement. It is a core form, like
`(M …)` for a motif `M`. It may be written where a movement may be written, and k must be at least
the position of the last parameter with no default. In the expand step, the compiler replaces it
with an `(in-order …)` whose members are the items of the body of the animation, with each
parameter replaced by the value of its argument, or by its default when `(C …)` has no argument
for it. So a `(C …)` written as a member of another score is one step of that score
({numref}`animation-step`).

The prover proves that the type of each argument is a {term}`subtype` of the type of its parameter. An argument may
be any expression that may be written in each place in the body where its parameter is written. So
with a variable `k`, `(pulse (* 2 k))` is a compile error when the parameter of `pulse` is written
as a duration, by the rules of {doc}`binding-time`, and is accepted when it is written as a `to`.

A parameter is bound to a value, such as a number or a shape, and not to a variable. A move in the
body may move an attribute of a shape that is the argument of a parameter, such as `who.opacity`,
but may not move the parameter itself. The one exception is a parameter of type `rand-seed`: its
argument must be the name of a seed, and in the body the parameter is replaced by that seed and not
by its value, so a move of the parameter moves the seed. Any other argument for such a parameter is
a compile error, "the argument for P is the name of a seed, as in (C dots)". So with the animation
`roll-dice` of the file rand, `(animation roll-dice ((rand-seed s)) (jump s (next-seed s)))`,
`(roll-dice s)` creates a movement that moves the seed `s`.

:::{admonition} Code differs
:class: note
The compiler writes out each `(C …)` for a choreo `C` where it is written (compiler.py:1669-1729),
and proves the body again for each one. It also compiles once on its own each choreo whose
parameters all have defaults. It binds a parameter that is not a seed, and whose argument is a
name, to that name, so that a move of the parameter moves what the name refers to
(mtp-ydd4.7.56).
:::
