# Built-ins and the standard library

:::{note}
Not drafted yet. This page defines: every built-in function and constant, and the files of the standard library.
:::

(stdlib-rand)=
## The file rand

This rule exists because random functions need a seed and a site that the compiler provides, so the file rand cannot be written in mtp.

```{rule} rand-module
The file `rand` of the {term}`standard library` has no .mtp file: the compiler provides its names,
and `(import rand …)` makes them usable in the same way as the names of any other file
({doc}`imports`). The file rand has these names, and only these:

| Name | What it is |
|---|---|
| `rand`, `rand-int`, `pick`, `shuffle`, `next-seed` | the random functions ({numref}`random-values`), which the compiler implements |
| `seed` | the {term}`seed` that a file with no seed of its own uses ({numref}`default-seed`), as if declared `(rand-seed seed 0)` |
| `roll-dice` | an animation, as if declared `(animation roll-dice ((rand-seed s)) (jump s (next-seed s)))`: each `roll-dice` writes the next value of the seed `s` to `s` at once. In a `(roll-dice)` with no argument, `s` is the {term}`default seed` of the file that holds the `(roll-dice)` |
```

This rule exists so that each use of a random function is a call with a site of its own.

```{rule} random-calls
A name that refers to a random function may be written only as the head of a call, and anywhere else
is a compile error, "N is only called, as (N …)".
```

Each call of `rand`, `rand-int`, `pick` or `shuffle` has a {term}`site` of its own
({numref}`random-site`), so a random function is never a value. For example, after
`(import rand rand)`, `(map xs rand)` is a compile error.

:::{admonition} Code differs
:class: note
The compiler reads the file rand from `mathterpiece/stdlib/rand.mtp`, in which each random
function is declared with a form `(primitive N)` that only a file of the standard library may hold.
Bead mtp-o3cc makes the compiler provide the names, and removes that form.
:::

So `(import rand rand-int roll-dice)` makes the names `rand-int` and `roll-dice` usable, and
`(import rand)` makes `rand.rand-int`, `rand.roll-dice` and the others usable ({doc}`imports`).
`(roll-dice s)` creates a `roll-dice`, which is a movement ({ref}`animation-uses`) of one step: a
write of `(next-seed s)` to the seed `s`.

```mtp
(import rand rand-int roll-dice)
(scene table (circle die (r (rand-int 1 6))))
(canvas v (x -6) (y -6) (width 12) (height 12) table)
(button roll (roll-dice) (label 'roll'))
```

Here the source declares no seed, so `(rand-int 1 6)` uses the seed `seed` of the file rand, which
starts at 0, and the button `roll` writes the next value of that seed to it.
