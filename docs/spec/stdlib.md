# Built-ins and the standard library

:::{note}
Not drafted yet. This page defines: every built-in function and constant, and the files of the standard library.
:::

(stdlib-primitives)=
## Primitives

The random functions are not built-in functions. The compiler implements them, and a source uses
them only through the names that the file `rand` of the {term}`standard library` gives them.

```{rule} primitive-form
A {term}`primitive` is one of the five functions `rand`, `rand-int`, `pick`, `shuffle` and
`next-seed`, defined in {numref}`random-values`. A primitive has no name until a file of the
standard library declares one with `(primitive N)`: a {term}`declaration` of the function `N`,
which is the primitive `N`. `(primitive N)` takes an optional `(doc …)` and no other item. It is
written only at the top level of a file of the standard library, which is a file that the compiler
reads from the folder of the standard library ({numref}`compiler-reads-files`).
```

A `(primitive N)` in any other place is a {term}`compile error`, "only a file of the standard
library holds (primitive …)". An `N` that is not a primitive is a compile error, "primitive names
one of rand, rand-int, pick, shuffle and next-seed", and so is a `(primitive …)` that holds anything
but a name and a `(doc …)`, "primitive is (primitive name)". A file of the standard library that
declares the same primitive twice is a compile error by {numref}`one-declaration-per-scope`.

```{rule} primitive-calls
A name that refers to a primitive is written only as the head of a call. Written in any other place,
it is a compile error, "N is only called, as (N …)".
```

Each call of `rand`, `rand-int`, `pick` or `shuffle` has a {term}`site` of its own
({numref}`random-site`), so a primitive is never a value. For example, after
`(import rand rand)`, `(map xs rand)` is a compile error.

(stdlib-rand)=
## The file rand

The file `rand` of the standard library holds these declarations, and only these:

| Name | Declaration | What it is |
|---|---|---|
| `rand`, `rand-int`, `pick`, `shuffle`, `next-seed` | `(primitive rand)` and so on | the primitives ({numref}`random-values`) |
| `seed` | `(rand-seed seed 0)` | the {term}`seed` that a file with no seed of its own follows ({numref}`default-seed`) |
| `roll-dice` | `(animation roll-dice ((rand-seed s)) (jump s (next-seed s)))` | an animation that gives the seed `s` its next value at once. `s` is the {term}`default seed` of the file that holds the use when the use gives no argument |

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
