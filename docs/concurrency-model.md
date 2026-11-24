# Concurrency model

Status: approved by the author on 2026-11-13, with his decisions of that day on the open questions.
It replaces the rules in reference.md, section "Concurrency", which were written case by case.

## The parts of the model

1. **Writers.** The controls and the listeners. A writer has a trigger and an effect. The
   effect is either a movement, which is known when the writer is triggered, or a gesture: an
   `on-drag`, a slider's knob while the reader holds it, and an `on-pointermove`, which emit writes each
   time the pointer moves. A writer is triggered, then emits writes to its containers until its
   effect ends, it is released, or it is cancelled. A writer that emits writes is running.
   `on-show` and `on-hide` emit writes only to the stand-ins of a canvas, and no other writer emits writes to them, so
   they meet only each other, and the one triggered later wins (reference, "Showing and hiding").
2. **Containers.** The free variables and the free attributes, which writes change. A write to an
   attribute of a group is a write to the same attribute of each member. The `pos` of a shape is
   its `x` and its `y`. An attribute that stands for several containers, such as the `x` of a
   polyline, the `x` of a line or the `r` of a group, is neither free nor bound: a write to it is a
   write to each container that it stands for (the `x` of each point). The `x` and the `y` of a
   point are two containers. Writers meet only on containers, so a writer of the `x` of a polyline
   and a writer of its `y` never meet. The runtime applies every rule below to each container on
   its own.
3. **Owner.** Each container has at most one owner: the running writer whose write to it was last
   accepted. A writer owns a container from its first accepted write (emitted, passed by the guards
   of the writer and by the constraints of the container), whether or not that write changes the
   value of the container.
4. **Priority.** Every writer has a priority, an int from 1 to 1000, set with `(priority n)`.
   A writer without it has the priority of its kind:
   - **View, 1000:** `on-view` (the author, 2026-11-13). Nothing that the reader does cuts it
     short.
   - **Page, 300:** a writer that the reader did not trigger: `on-ready`.
   - **Reader, 500:** a writer that the reader triggered: a press, a click, a key, a flip,
     `on-enter`, `on-leave`, `on-live`, `on-quiet`, and a play or a stepper that the reader
     pressed.
   - **Gesture, 700:** a gesture that the reader is making: an `on-drag` and a slider's knob, from
     the first accepted write to the release, and an `on-pointermove`.
5. **Constraints.** Each side clamps a write.
   - **Writer side:** the guards of the writer clamp a write before it is emitted.
   - **Container side:** the conditions of the container's type are enforced on a write when it is accepted ({numref}`writes-to-conditions`).

`(exclusive)` is removed from the language.

## The rule for every write

A write from writer A reaches container v.

1. If v has an owner B other than A, and A's priority is lower than B's, or the same and A was
   triggered before B, the write is rejected.
2. Otherwise the write is accepted: it is clamped by v's constraints, and A becomes v's owner.
   If B owned v, B is cancelled on all its containers.

A rejected write cancels nothing. A writer whose write to a container is rejected emits no more writes
to that container for the rest of its effect, and goes on emitting writes to its other containers. A writer
that is triggered again starts a new effect. A writer that ends or is released owns nothing after
that.

At the same priority, the newer writer is the one that was triggered later, not the one whose write
arrives later: a toggle flipped after a play was pressed keeps its bool (open: see below).

Steps and explore mode are not part of this model: the runtime reads the step of a play or a
stepper from the containers of the scene (mtp-wjtd notes).

## Questions decided by the author

- **Q1 (author, 2026-11-13).** A writer that loses a container is cancelled: it stops emitting
  writes to every container.
- **Q2 (author, 2026-11-13).** Each container is decided on its own, for every writer: a writer
  whose writes are rejected on some containers still has its other writes accepted. A play pressed
  while the reader holds a drag on k moves only its other containers.
- **Q3 (author, 2026-11-13).** A rejected writer stops emitting writes to that container for the rest of its
  effect, so it does not become the owner of the container when the owner ends.
- **Open.** A toggle's flip takes no time, so its writer ends as soon as it has emitted its write and owns
  nothing after. A play that had not yet emitted a write to the bool then emits it later, and the write
  is accepted. The runtime does this now, until the author decides.

## The earlier cases under the model

| Case | Before | Under the model |
|---|---|---|
| Reader writer running, reader newcomer | newcomer wins | unchanged (same priority, triggered later) |
| Reader writer running, `on-view` newcomer | newcomer refused | **changes**: the `on-view` wins, at priority 1000 (the author, 2026-11-13) |
| Page writer running, any newcomer | newcomer wins | unchanged |
| `(exclusive)` writer running, any newcomer | newcomer refused | removed: a higher `(priority n)` instead |
| Held drag, `on-enter` onto another shape writing to the dragged container | `on-enter` cancels the drag | **changes**: rejected (lower priority), its other writes accepted |
| Held drag, `on-view` writing to the dragged container | refused | **changes**: the `on-view` wins, at priority 1000 |
| Grab with no move, play running on the container | play runs on | unchanged (no write, no ownership) |
| Held slider knob, reader newcomer writing to its container | newcomer cancels the slider | **changes**: rejected (lower priority), as for a drag |
| Slider step from the keyboard | a newcomer of its own | unchanged (reader, not a gesture) |
| Paused play or stepper | not running | unchanged (owns nothing) |
| Another writer writes to a container of a play | explore mode | not concurrency: the step is read from the scene |
| A writer never cancels itself | stated as a rule | unchanged (A is already the owner) |
| Attribute of a group, `pos`, the `x` of a polyline | stated case by case | unchanged (a write to each container) |
| The `x` and the `y` of a polyline | did not meet | unchanged (the `x` and the `y` of each point are containers) |
| Copies of a control | two writers | unchanged (two writers of the same priority) |
| Refused newcomer: none of its moves happen | stated as a rule | **changes**: see Q2 |
| Newcomer meeting several running writers | refused if any refuses | **changes**: decided per container, see Q2 |
| Inactive writer `(active false)` | cannot be triggered, what runs goes on | unchanged (not triggered, nothing else changes) |
| The runtime starts or stops drawing a shape in a canvas | writes nothing | unchanged (not a writer) |
| A write that changes nothing | skipped | still skipped, but the writer becomes the owner (part 3) |
| An `on-ready` loop | no other writer may write to its containers | an ordinary writer of priority 300 (the author, 2026-11-13) |
| `on-view` sped up by a press | built | removed (author, 2026-11-12) |

These cases are outside the model, since no two writers meet in them: two moves in one score that
write to the same container at the same time (a compile error), a move that reads its `from` and `to`
when it starts, and a slider's knob that updates when its target changes.
