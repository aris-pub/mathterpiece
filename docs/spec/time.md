# Time and animation

:::{note}
Not drafted yet. This page defines: moves, which are the unit of change over time, movements as functions of time, scores as collections of movements, each member placed in time by its own lag, repeated with loops, as a group is a collection of shapes, with `in-order` and `at-once` as scores whose members run one after another or together, and animations as templates of movements, as a motif is a template of shapes.
:::

(animation-uses)=
## Movements of an animation

With an animation `C`, `(C A1 … Ak)` creates a `C`, which is a movement. It is core, as `(M …)` is for
a motif `M`. It is written where a
movement may be written, and k is at least the position of the last parameter with no default. In
the expand step it becomes an `(in-order …)` whose members are the body of the animation, with each
parameter replaced by the value of its argument, or by its default when it gives no argument
for it. So a `(C …)` written as a member of an `in-order` or an `at-once` is one step
({numref}`animation-step`). The prover proves that each argument {term}`fits <fit>` the type
of its parameter. An argument may be any expression that may be written in the body in the places
where its parameter is written, so `(pulse (* 2 k))` is an error when the parameter is a duration,
by {doc}`binding-time`, and is accepted when it is a `to`. A parameter stands for a value, such as a number or a
shape, never for a variable: a move in the body may move an attribute of a shape given as a
parameter, such as `who.opacity`, and never the parameter itself. The one exception is a parameter
of type `rand-seed`, which stands for a seed: its argument is the name of a seed, and in the body
the parameter is replaced by that seed and not by its value, so a move of the parameter moves the
seed. Any other argument for such a parameter is a compile error, "the argument for P is the name
of a seed, as in (C dots)". So the animation `roll-dice` of the file rand,
`(animation roll-dice ((rand-seed s)) (jump s (next-seed s)))`, moves the seed named in `(roll-dice s)`.

:::{admonition} Code differs
:class: note
The compiler writes each use of a choreo out where it is written (compiler.py:1669-1729), proves
the body again for each use, compiles a choreo whose parameters all have defaults once more without
a use, and binds a parameter that is not a seed and is given a name to that name, so that a move of
the parameter moves what it names (mtp-ydd4.7.56).
:::
