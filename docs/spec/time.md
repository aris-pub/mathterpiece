# Time and animation

A {term}`movement` is an object that the runtime executes by writing to its target over time
({numref}`objects`). This page defines the forms that create movements, the value that a movement
writes to its target at each instant, how a {term}`movement group` places its members in time and
repeats them, and animations, which are templates of movements. What happens when two writers
write to one container is defined in {doc}`concurrency`.

## Movements

This rule exists to fix the arguments of the forms that create one movement, so that the compiler can check each of them.

````{rule} move-signature
```mtp-sig
(move TARGET
  (to:T TARGET)
  (duration:(real (>= 0)) D)
  (ease:ease E)
  (path:func[T T real T] P)
  (lag:(real (>= 0)) L)
  (doc:string ''))

(movement NAME TARGET
  (like move))
```

`TARGET` is the container that the movement writes to ({numref}`writable-targets`), or `none`, and
`T` is the type of the container. `(move …)` results in a new movement with no name, and
`(movement N …)`, written at the top level, declares the movement `N`. A duration is a number of
seconds. A movement whose target is `none` writes to nothing, and takes only `duration` and `lag`.
The defaults `D`, `E` and `L` are set by {numref}`movement-defaults`, `P` is the straight line of
{numref}`straight-line`, and a movement with no `to` ends at the value that its target holds when it
starts.
````

So `(move k (to 1) (duration 2))` writes to `k` for 2 seconds and ends at 1, and
`(movement grow c.r (to 2) (duration 1))` declares a movement named `grow`. `(move V (from F) …)`,
`(jump V X)` and `(wait T)` are syntactic sugar ({numref}`sugar-rewrites`): `(jump k 3)` is a
movement of duration 0, and `(wait 1)` is a movement that writes to nothing for 1 second.

:::{admonition} Code differs
:class: note
The compiler calls a movement a transition, declared with `(transition t TARGET …)`, and reads `from`
as an argument of the movement and not as syntactic sugar (compiler.py:3117-3180). It has no `lag`.
Beads mtp-kir3 and mtp-idcs.
:::

This rule exists to define the value that a movement writes to its target at each instant, which makes a movement a function of time.

```{rule} movement-value
A movement that starts at the instant s and lasts d seconds runs from s to s + d. Its progress at an
instant t is p = (t - s)/d, and is 1 when d is 0. At each instant t at which the runtime draws while
the movement runs, the movement writes to its target the value P(X0, X1, E(p)): X0 is the value of the
target and X1 the value of the `to` when the movement starts ({numref}`ends-read-at-start`), E is its
ease, and P its path. Its last write is the value at p = 1, even when the runtime next draws after
s + d. It writes nothing before s and nothing after its last write.
```

So with `k` at 0, `(move k (to 1) (duration 2))` with no ease writes 0.5 to `k` at 1 second, and 1 at
2 seconds. `(jump k 3)` writes 3 at its start. Each write is decided by {numref}`write-decision`, and
an accepted write is brought into the conditions of the target ({numref}`writes-to-conditions`).

This rule exists to define the straight line, the path of every movement that gives no `path`, for each type of target.

```{rule} straight-line
P(X0, X1, u), the straight line from X0 to X1, is the following for each type of target:

| The type of the target | P(X0, X1, u) |
|---|---|
| `int`, `ratio`, `real` | X0 + (X1 - X0) × u, for every u, so a u above 1 or below 0 takes the value past X1 or X0 |
| `point` | the same, for `x` and for `y` |
| `color` | X0 when u is at most 0, X1 when u is at least 1, and `(mix X0 X1 u)` between them, with `none` mixed as the transparent color |
| any other type | X0 while u is below 1, and X1 from u = 1 |

When X0 or X1 is `none` and the target is not a color, P(X0, X1, u) is X0 while u is below 1 and X1 from
u = 1, the path is not used, and u is 1 from the start unless the ease is `(steps 1 (at Q))`.
```

So a movement of a bool, a string or a list changes its value at one instant. A movement with a
`to` of `none` may be written only when the type of the target includes `none`, by
{numref}`written-values`, as in `(move m (to none))` with `(real|none m 2)`, and then `m` is `none`
from the start of the movement.

This rule exists so that a movement of a value that cannot change smoothly changes at one instant, and never stops at a value between its ends.

```{rule} discrete-eases
The ease of a movement whose target is a bool, a string or of a {term}`choice type` must be
`(steps 1 (at Q))`, which is 0 before the progress Q and 1 from Q on. Any other ease is a compile error,
"an ease for a bool takes only the values 0 and 1".
```

So `(move shown (to true) (duration 1) (ease (steps 1 (at 0.5))))` changes `shown` at 0.5 seconds,
and with no ease, `shown` changes at the start ({numref}`movement-defaults`).

:::{admonition} Code differs
:class: note
The compiler has `(step-ease Q)` in place of `(steps 1 (at Q))`, and gives a bool, a string or a
choice type the ease `(step 1)`, which changes at the start (compiler.py:3482-3500). Beads
mtp-ydd4.7.40 and mtp-6a4r.
:::

This rule exists to fix the instant at which a movement reads the values that it moves between, so that what the movements that start at one instant write does not depend on the order in which the runtime computes them.

```{rule} ends-read-at-start
A movement reads X0, the value of its target, and X1, the value of its `to`, at the instant that it starts,
and they stay fixed while it runs. A member of a movement group whose lag is at least 1 starts after
the member before it, even when the two start at one instant, and so does every movement inside it.
Two movements that start at one instant, with neither starting after the other, start together. The
movements that start together read before any of them writes, and a movement reads what every
movement that starts before it has written. For a target that stands for several containers
({numref}`target-containers`), X0 is the value of the first member that has the attribute.
```

So `(at-once (move a (to b)) (move b (to a)))` swaps `a` and `b`, and
`(in-order (defaults (duration 0)) (move a (to 5)) (move b (to a)))` writes 5 to `b`, since the
second movement starts after the first one, at the same instant. A movement in the second round of
a loop reads what the reader changed during the first round ({numref}`group-loop`).

This rule exists so that a movement inside a movement group need not give its duration, its ease and its lag, and so that every movement has each of them.

```{rule} movement-defaults
A member of a movement group that gives no `duration`, `ease` or `lag` of its own takes the one
that the `(defaults …)` of the group gives. The `(defaults …)` of a movement group may hold only
`duration`, `ease` and `lag`, and applies only to its members ({numref}`animation-step`). When
neither the movement nor the group gives one:

- A movement with no duration is a compile error, "this move needs a duration".
- The ease of a movement whose target is a bool, a string or of a choice type is
  `(steps 1 (at 0))`, and of every other movement the ease E(p) = p, so that it moves at one
  speed.
- A member with no lag, other than the first member, is a compile error, "this movement needs a
  lag".
```

So `(button b (move k (to 1)))` is a compile error, and
`(in-order (defaults (duration 0.5)) (move a (to 1)) (move b (to 1) (duration 2)))` lasts 2.5
seconds. Since `(in-order …)` and `(at-once …)` add a lag to their `(defaults …)`
({numref}`sugar-rewrites`), every member of them has one.

:::{admonition} Code differs
:class: note
The compiler gives the defaults of an animation, an `in-order` and an `at-once` to every movement
inside them, at any depth, and not only to their members (compiler.py:3308-3330). Bead mtp-ydd4.7.26.
:::

This rule exists so that the compiler can fix the start of every movement, which the runtime then never computes again.

```{rule} known-durations
The duration and the lag of a movement, and the count of a `(loop …)`, must be known when compiling
({doc}`binding-time`). A duration that is not known when compiling is a compile error, "a duration
is a number of seconds known when compiling", and so is such a lag or count.
```

So `(move k (to 1) (duration (* 2 a)))` is a compile error when `a` is free, and the `to` of a
movement may read any container.

## Movement groups

This rule exists to fix the arguments of `with-lag`, the form that creates a movement group, so that the compiler can check each one.

````{rule} with-lag-signature
```mtp-sig
(with-lag
  (lag:(real (>= 0)) L)
  (loop COUNT:(int (>= 1))?)
  (defaults ITEMS:(duration|ease|lag)*)
  (doc:string '')
  MEMBERS:movement*)
```

`(with-lag …)` results in a new movement group, of type `movement-group`, whose members are
`MEMBERS`, in order. Its own `lag` places it in a movement group that holds it, as the `lag` of a
`(move …)` does. `(in-order …)` and `(at-once …)` are syntactic sugar for it
({numref}`sugar-rewrites`).
````

This rule exists to place each member of a movement group in time, as each member of a group is placed in space by its position.

```{rule} lag-starts
The first member of a movement group starts when the group starts. Each later member starts when
the member before it has run for its lag times its duration: when the member before it starts at s
and lasts d seconds, a member with the lag L starts at s + L × d. A lag above 1 leaves a pause between
the two. After a member whose duration is `none` ({numref}`movement-duration`), a member with a
lag above 0 never starts. The lag of the first member, and the lag of a movement that is not a member
of a movement group, place nothing.
```

So in `(in-order a b)`, which is `(with-lag (defaults (lag 1)) a b)`, `b` starts when `a` ends, and
in `(at-once a b)` both start together. In
`(with-lag (defaults (lag 0.25) (duration 1)) (move a (to 1)) (move b (to 1)) (move c (to 1)))`,
`b` starts at 0.25 seconds and `c` at 0.5 seconds. Each copy that a `foreach` in the body makes is
a member, in the order of the copies ({numref}`foreach-copies`), so
`(at-once (foreach d dots (move d.r (to 0) (duration 1))))` shrinks every dot at once.

:::{admonition} Code differs
:class: note
The compiler has no `with-lag` and no `lag`: `in-order` and `at-once` are the only movement groups,
and each places its members as the lags 1 and 0 do. Beads mtp-idcs and mtp-08wd.10.
:::

This rule exists to define how a movement group repeats its members.

```{rule} group-loop
A movement group with `(loop n)` plays its members n times in a row, and one with `(loop)` plays them
again forever. Each time is a round: a round starts when the one before it ends, and its members
start again, so they read their ends again ({numref}`ends-read-at-start`). A movement group with no
`(loop …)` plays its members once. A movement group that loops and whose round lasts 0 seconds is a
compile error, "this movement group loops, but a round of it takes no time".
```

So `(in-order (loop) (move a (to 1) (duration 1)) (move a (to 0) (duration 1)))` takes `a` to 1 and
back forever. A movement with no `from` carries on in each round from where the round before left
its target, and a movement with a `from` jumps back to it, since its `from` is a `jump`
({numref}`sugar-rewrites`).

:::{admonition} Code differs
:class: note
Only an `(animation …)` takes `(loop …)` (compiler.py:3268-3285), and in the compiler an animation
is a movement group and not a template. Bead mtp-cg47.
:::

This rule exists so that a source can read how long a movement lasts, including a movement that never ends.

```{rule} movement-duration
Every movement has the const attribute `duration`, its duration in seconds, a real, or `none` for a
movement that never ends. The duration of a `(move …)` is set by {numref}`move-signature` and
{numref}`movement-defaults`. One round of a movement group lasts from its start to the latest end
of its members ({numref}`lag-starts`), and a movement group with `(loop n)` lasts n rounds. The
duration of a movement group that loops forever, or that holds a member that starts and never ends,
is `none`.
```

So `(in-order a b)` lasts as long as `a` and `b` together, and `(at-once a b)` as long as the longer
of the two. With `m` a movement that loops forever, `(real d m.duration)` is a compile error, since
`m.duration` is `none`, and `(real|none d m.duration)` is `none`.

This rule exists because a movement group places its members in time once, when it starts, and a write that another writer rejects must not move the rest in time.

```{rule} start-times-fixed
When a movement starts, the start of every movement inside it is fixed, by {numref}`lag-starts`
and {numref}`group-loop`. A rejected write and a cancelled writer ({doc}`concurrency`) make no
movement start at another instant.
```

So when the reader drags `k` while a play runs `(in-order (move k (to 1) (duration 1)) (move j (to 1) (duration 1)))`,
the movement of `j` still starts at 1 second, whatever happens to the writes to `k`.

This rule exists so that a movement group can hold a movement or an animation by its name.

```{rule} movement-names
In a movement group, the name of a movement declared with `movement` is that movement, and the
name of an animation `A` with no parameters is `(A)`.
```

So after `(movement grow c.r (to 2) (duration 1))`, `(in-order grow (wait 1))` plays `grow` and then
waits for 1 second.

## Steps of a play and a stepper

This rule exists to define the steps through which a play and a stepper go.

```{rule} movement-steps
The steps of the effect of a play or a stepper ({numref}`mover-signatures`) are these. When the
effect is a movement group whose members after the first all have the lag 1, as those of an
`in-order` do, its steps are its members, in order, and for a movement group that loops, the members
of one round. Every other effect is one step.
```

So `(play p (in-order grow (wait 1) shrink))` has three steps, `(play p (at-once grow shrink))` has one,
and a member that is a movement group is one step ({numref}`animation-step`). The effect
`(fade-in c)` of an animation `fade-in` has the steps of the body of `fade-in`, since the expand
step replaces it with that body ({numref}`animation-movements`).

(animation-uses)=
## `(A …)` for an animation `A`

This rule exists to fix the form that declares an animation, which is a template of movements as a motif is a template of shapes.

````{rule} animation-signature
```mtp-sig
(animation NAME PARAMS
  (doc:string '')
  BODY:movement)
```

`PARAMS` are the parameters of the animation ({numref}`parameters`), and `BODY` is one movement.
`(animation A PARAMS M)` declares the movement type `A` ({numref}`motif-and-variant-types`). Several
movements in place of `M` are an `(in-order …)` of them ({numref}`sugar-rewrites`).
````

This rule exists to define what `(A …)` creates, so that every compiler writes the same movements for it.

```{rule} animation-movements
With an animation `A`, `(A X1 … Xk)` creates an `A`, which is a movement. It is a core form, like
`(M …)` for a motif `M`, and it may be written where a movement may be written. k must be at least
the position of the last parameter with no default, except for `dice-roll` ({doc}`stdlib`). In the
expand step, the compiler replaces it with the body of `A`, with each parameter replaced by the value
of its argument, or by its default when `(A …)` gives no argument for it. The prover checks that the
type of each argument is a {term}`subtype` of the type of its parameter, and an argument may be any
expression that may be written in each place in the body where its parameter is written.
```

So a `(A …)` written as a member of a movement group is one member of that group
({numref}`animation-step`). With a variable `k`, `(pulse (* 2 k))` is a compile error when the
parameter of `pulse` is written as a duration, by {numref}`known-durations`, and is accepted when it
is written as a `to`. By {numref}`declare-before-use`, the body of `A` may not hold an `(A …)`,
directly or through the bodies of other animations.

This rule exists because a movement in the body of an animation writes to containers, and a parameter is not one, except a seed.

```{rule} animation-parameters
A parameter is bound to a value, such as a number or a shape, and not to a variable. A movement in
the body may write to an attribute of a shape that is the argument of a parameter, such as
`who.opacity`, but may not write to the parameter itself. A parameter of type `rand-seed` is the one
exception: its argument must be the name of a seed, and in the body the parameter is replaced by
that seed and not by its value, so a movement whose target is the parameter writes to the seed. Any
other argument for such a parameter is a compile error, "the argument for P is the name of a seed,
as in (A dots)".
```

So with the animation `dice-roll` of the file rand,
`(animation dice-roll ((rand-seed s)) (jump s (next-seed s)))`, `(dice-roll s)` creates a movement
that writes to the seed `s`.

:::{admonition} Code differs
:class: note
The compiler calls an animation a choreo, declared with `(choreo …)`, and writes out each
`(C …)` for a choreo `C` where it is written (compiler.py:1907-1980), and checks the body again
for each one. It also compiles once on its own each choreo whose parameters all have defaults. It
takes only arguments known when compiling, and binds a parameter that is not a seed, and whose
argument is a name, to that name, so that a movement whose target is the parameter writes to what
the name refers to (mtp-ydd4.7.56).
:::
