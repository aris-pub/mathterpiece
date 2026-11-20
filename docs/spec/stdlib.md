# Built-ins and the standard library

:::{note}
Not drafted yet. This page defines: every built-in function and constant, and the files of the standard library.
:::

(stdlib-rand)=
## The file rand

```{rule} rand-module
The file `rand` of the {term}`standard library` has no .mtp: the compiler gives its names, and
`(import rand …)` reads them as it reads the names of any file ({doc}`imports`). It gives these
names, and only these:

| Name | What it is |
|---|---|
| `rand`, `rand-int`, `pick`, `shuffle`, `next-seed` | the random functions ({numref}`random-values`), which the compiler implements |
| `seed` | the {term}`seed` that a file with no seed of its own follows ({numref}`default-seed`), as if declared `(rand-seed seed 0)` |
| `roll-dice` | an animation that gives the seed `s` its next value at once, as if declared `(animation roll-dice ((rand-seed s)) (jump s (next-seed s)))`. `s` is the {term}`default seed` of the file that holds the use when the use gives no argument |
```

```{rule} random-calls
A name that refers to a random function is written only as the head of a call. Written in any
other place, it is a compile error, "N is only called, as (N …)".
```

Each call of `rand`, `rand-int`, `pick` or `shuffle` has a {term}`site` of its own
({numref}`random-site`), so a random function is never a value. For example, after
`(import rand rand)`, `(map xs rand)` is a compile error.

:::{admonition} Code differs
:class: note
The compiler reads the file rand from `mathterpiece/stdlib/rand.mtp`, which names each random
function with a form `(primitive N)` that only a file of the standard library may hold. Bead mtp-o3cc
gives the names from the compiler and removes that form.
:::

So `(import rand rand-int roll-dice)` gives the names `rand-int` and `roll-dice`, and
`(import rand)` gives `rand.rand-int`, `rand.roll-dice` and the others ({doc}`imports`).
`(roll-dice s)` is a use of an animation ({ref}`animation-uses`): one step, which writes
`(next-seed s)` into the seed `s`. `(roll-dice)` with no argument rolls the {term}`default seed`
of the file that holds it ({numref}`default-seed`).

```mtp
(import rand rand-int roll-dice)
(scene table (circle die (r (rand-int 1 6))))
(canvas v (x -6) (y -6) (width 12) (height 12) table)
(button roll (animation (roll-dice)) (label 'roll'))
```

Here the source declares no seed, so `(rand-int 1 6)` follows `seed` of the file rand, which
starts at 0, and the button `roll` gives that seed its next value.
