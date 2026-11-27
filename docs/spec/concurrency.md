(concurrency)=
# Concurrency model

Several {term}`writers <writer>` may write to one {term}`container` at the same time, as when a play
runs while the reader drags a shape that it moves. This page defines what each writer emits, which
containers each write reaches, and which writes the runtime accepts when two writers write to one
container. The step of a play or a stepper is read from the containers by {term}`matching <match>`
({numref}`matching`), so no rule of this page decides it.

## Writers and their effects

This rule exists to define when a writer emits writes, which every other rule of this page needs.

```{rule} writer-effects
A writer is triggered, and then emits writes to containers until its effect ends, it is released or
it is cancelled ({numref}`cancelled-writers`). A writer that emits writes is running. Its effect
is one of these:

- A movement, known when the writer is triggered: the effect of a mover ({numref}`jumpers-and-movers`)
  and the movement of every listener but `on-drag` and `on-pointermove`. It ends when the movement
  ends ({doc}`time`).
- A gesture that the reader holds: an `on-drag`, and the thumb of a slider or a dial while the reader
  holds it. It emits a write at each motion of the pointer, from the press to the release.
- One write that takes no time: each motion of the pointer for an `on-pointermove`, and every other
  action of the reader on a jumper, such as a click on a toggle. It ends once it has emitted its write.
```

So a button emits writes for as long as its movement runs, and a toggle ends as soon as it has
written to its target, and owns nothing after that ({numref}`owners`).

:::{admonition} Open question
:class: warning
A writer whose effect takes no time owns nothing once it has emitted its write. So when the reader
clicks a toggle while a play runs, a later write of the play to the same bool is accepted, and the
bool changes back. The runtime does this today. The options:

- (a) Keep it so.
- (b) A writer whose effect takes no time keeps its container from every writer that was triggered
  before it, until that writer ends.
:::

This rule exists because the stand-ins of a canvas are written to only by `on-show` and `on-hide`, so these two writers meet no other writer.

```{rule} stand-in-writers
`on-show` and `on-hide` emit writes only to the stand-ins of a canvas
({numref}`runtime-adds-no-objects`), and no other writer emits writes to a stand-in. Between the two,
the write of the one triggered later is accepted on a stand-in, by {numref}`write-decision`.
```

So an `on-show` that is triggered while the `on-hide` of the same shape plays cancels the `on-hide`,
and the reverse.

## Containers

This rule exists to define which containers a write reaches, since writers meet only on containers.

```{rule} target-containers
Two writers meet when both emit writes to one free container. A write to a target that stands for
several containers is a write to each of them:

- The `pos` of a shape stands for its `x` and its `y`.
- An attribute that a group does not have of its own stands for that attribute of
  each member that has it, at any depth, and so does an attribute of a shape declared with a motif
  that {numref}`collection-defaults` lets it set on the shapes of its body.
- The `x` of a line, a triangle, a polyline, a polygon and a bezier stands for the `x` of each of
  the points from which its position is worked out, its `y` for their `y`, and its `pos` for both.

The `x` and the `y` of a point are two containers. The runtime applies every rule of this page to each
container on its own.
```

So a writer of the `x` of a polyline and a writer of its `points` meet on the `x` of each point, and
never meet a writer of its `y`. A writer of `g.r` meets a writer of `c.r`, for a member `c` of `g`, on
`c.r` only. The `shift` of a group is an attribute of its own ({doc}`data-model`), so a writer of
`g.shift` meets no writer of a member.

## Owners and priorities

This rule exists to define the owner of a container, by which the runtime decides each write.

```{rule} owners
Each container has at most one owner: the running writer whose write to it was last accepted
({numref}`write-decision`). A writer owns a container from its first accepted write to it, whether or
not that write changes the value of the container. A writer that ends, is released, is paused or is
cancelled owns nothing after that.
```

So a press on a shape with no motion of the pointer emits no write, and a play that writes to the
shape runs on.

This rule exists so that the illustrator can set which of two writers wins a container, and so that a writer that gives no priority has one all the same.

```{rule} priorities
Every writer has a priority, an {term}`int` from 1 to 1000, which `(priority n)` sets. A writer with
no `(priority …)` has the priority of its kind:

| Kind | The writers | Priority |
|---|---|---|
| view | `on-view` | 1000 |
| gesture | an `on-drag` and the thumb of a slider or a dial, from the first accepted write to the release, and an `on-pointermove` | 700 |
| reader | every other writer that the reader triggers, such as a press of a button, a play or a stepper, a key, a click on a toggle, `on-click`, `on-enter`, `on-leave`, `on-live` and `on-quiet` | 500 |
| page | a writer that the reader does not trigger: `on-ready` | 300 |
```

So with no `(priority …)`, nothing that the reader does cuts an `on-view` short, and an `on-ready`
that loops forever is cut short by any writer that the reader triggers and that writes to one of its containers.
`(button b (move k (to 1) (duration 2)) (priority 800))` wins `k` from a drag.

## The rule for every write

This rule exists to decide each write that two writers emit to one container, the same way in every runtime.

```{rule} write-decision
A write that writer A emits to the container v, clamped first by the guards of A
({numref}`writer-guards`), is decided so:

1. When v has an owner B other than A, and the priority of A is below that of B, or the same and A
   was triggered before B, the write is rejected.
2. Otherwise the write is accepted: it is brought into the conditions of v
   ({numref}`writes-to-conditions`), and A becomes the owner of v. When B owned v, B is cancelled.
```

So when the reader presses a button while a play runs that writes to the same containers, both of
priority 500, the button's writes are accepted and the play is cancelled. At the same priority, the
writer that was triggered later wins, and not the one whose write comes later. A writer never
cancels itself, since it is already the owner of the containers that it writes to.

This rule exists to define what a cancelled writer and a rejected write each do to the rest of a writer's effect.

```{rule} cancelled-writers
A cancelled writer emits no more writes, to any container, and what it wrote stays. A rejected write
cancels nothing. A writer whose write to a container is rejected emits no more writes to that
container for the rest of its effect, so it never becomes its owner, and goes on emitting writes to
its other containers. A writer that is triggered again starts a new effect, which emits writes to
every container again.
```

So a play that is pressed while the reader holds a drag on `k` writes to every container of its
movement but `k`, and goes on without `k` when the drag ends. A press on a button while its movement
runs starts the movement again.

## Movements of one movement group that write to one container

This rule exists because two movements of one movement group that write to the same container at once would give the container no single value.

```{rule} movements-at-once
Two movements of one movement group that write to the same container ({numref}`target-containers`) at
times that overlap are a compile error. A movement writes from its start up to its start plus its
duration ({numref}`movement-value`), and a movement whose duration is `none` writes from its start on.
Two times overlap when the two movements start together ({numref}`ends-read-at-start`), or when each
starts before the other ends.
```

So `(at-once (move k (to 2) (duration 1)) (move k (to 3) (duration 1)))` is a compile error, and
`(at-once (move k (to 0) (duration 0)) (in-order (wait 2) (move k (to 1))))` is not. For a
polyline `pl`, `(at-once (move pl.x (to 3)) (move pl.points (to {[0 0] [2 0]})))` is a compile
error, and `(at-once (move pl.x (to 3)) (move pl.y (to 3)))` is not. The `shift` of a group is a
container of the group and not of its members, so `(at-once (move g.shift (to [1 1])) (move c.x (to 3)))`
is allowed for a member `c` of `g`. `(move k (from 0) (to 1) (duration 1))` is not a compile error,
since the movement after its `jump` starts after it ({numref}`sugar-rewrites`).

:::{admonition} Code differs
:class: note
The compiler checks only the members of an `at-once` (compiler.py:3402-3422), and has no
`with-lag`. Bead mtp-idcs.
:::
