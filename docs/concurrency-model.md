# Concurrency model

Status: approved, 2026-11-13, with the author's decisions of that day on the gaps. It replaces
the case-by-case rules in reference.md, "Concurrency".

## The parts

1. **Writers.** The controls and the listeners. A writer has a trigger and an effect. The
   effect is either an animation, known ahead, or a gesture: an `on-drag`, a slider's knob
   while the reader holds it, and an `on-pointermove`, which write as the pointer moves. A
   writer is triggered, then emits writes to its containers until its effect ends, it is released,
   or it is cancelled. A writer that emits writes is running. `on-show` and `on-hide` write only
   a canvas's stand-ins, which no other writer writes, so they meet only each other, and the one
   triggered later wins (reference, "Showing and hiding").
2. **Containers.** The free variables and attributes that a write changes. A write to a group's attribute is a write of
   each member's. A shape's `pos` is its `x` and its `y`. An attribute that stands for several, such as a
   polyline's `x`, a line's `x` or a group's `r`, is neither free nor bound: it broadcasts each
   write to the containers that it stands for (each point's `x`). A point's `x` and its `y` are two
   containers. Writers meet only on containers, so a writer of a polyline's `x` and a writer of its `y`
   never meet. Every rule below is applied to each container on its own.
3. **Owner.** Each container has at most one owner: the running writer whose write of it was last
   accepted. A writer owns a container from its first accepted write (emitted, passed the writer's
   conditions and the container's constraints), whether or not that write changes its value.
4. **Priority.** Every writer has a priority, an int from 1 to 1000, set with `(priority n)`.
   One without it has its kind's:
   - **View, 1000:** `on-view` (the author, 2026-11-13): nothing the reader does cuts it short.
   - **Page, 300:** nothing the reader did triggered it. `on-ready`.
   - **Reader, 500:** the reader triggered it. A press, a click, a key, a flip, `on-enter`,
     `on-leave`, `on-live`, `on-quiet`, and a play or stepper the reader pressed.
   - **Gesture, 700:** the reader is making it now. An `on-drag` and a slider's knob, from the
     first accepted write to the release, and an `on-pointermove`.
5. **Constraints.** Both clamp, as before.
   - **Writer side:** the writer's conditions clamp a write before it is emitted.
   - **Container side:** the container's type constraints clamp a write when it is accepted.

`(exclusive)` is removed from the language.

## The rule for every write

A write from writer A reaches container v.

1. If v has an owner B other than A, and A's priority is lower than B's, or the same and A was
   triggered before B, the write is rejected.
2. Otherwise the write is accepted: it is clamped by v's constraints, and A becomes v's owner.
   If B owned v, B is cancelled on all its containers.

A rejected write cancels nothing. A writer whose write of a container is rejected writes that container
no more for the rest of its effect, and goes on writing its other containers. A writer triggered
again starts a new effect. A writer ends, or is released, and owns nothing after that.

At the same priority, the newer writer is the one triggered later, not the one whose write
arrives later: a toggle flipped after a play was pressed keeps its bool (open: see below).

Steps and explore mode are not part of this model: a play's or stepper's step is read from
the scene's containers (mtp-wjtd notes).

## Decided questions in the model

- **Q1 (author, 2026-11-13).** A writer that loses a container is cancelled: it stops emitting
  writes to every container.
- **Q2 (author, 2026-11-13).** Each container is decided on its own, for every writer: a writer
  whose writes are rejected on some containers still has its other writes accepted. A play pressed
  while the reader holds a drag on k moves only its other containers.
- **Q3 (author, 2026-11-13).** A rejected writer stops writing that container for the rest of its
  effect, so it does not take the container over when the owner ends.
- **Open.** A toggle's flip takes no time, so its writer ends as soon as it has written and owns
  nothing after. A play that had not yet written the bool then writes it later, and the write
  is accepted. The runtime does this now, pending the author's word.

## The existing cases, checked

| Case | Before | Under the model |
|---|---|---|
| Reader writer running, reader newcomer | newcomer wins | follows (same priority, triggered later) |
| Reader writer running, `on-view` newcomer | newcomer refused | **changes**: the `on-view` wins, at priority 1000 (the author, 2026-11-13) |
| Page writer running, any newcomer | newcomer wins | follows |
| `(exclusive)` writer running, any newcomer | newcomer refused | removed: a higher `(priority n)` instead |
| Held drag, `on-enter` onto another shape writing the dragged container | `on-enter` cancels the drag | **changes**: rejected (lower priority), its other writes accepted |
| Held drag, `on-view` writing the dragged container | refused | **changes**: the `on-view` wins, at priority 1000 |
| Grab with no move, play running on the container | play runs on | follows (no write, no ownership) |
| Held slider knob, reader newcomer writing its container | newcomer cancels the slider | **changes**: rejected (lower priority), as for a drag |
| Slider step from the keyboard | a newcomer of its own | follows (reader, not a gesture) |
| Paused play or stepper | not running | follows (owns nothing) |
| Play written under by another writer | explore mode | not concurrency: the step is read from the scene |
| A writer never cancels itself | stated as a rule | follows (A is already the owner) |
| Group attribute, `pos`, a polyline's `x` | stated case by case | follows (broadcast to containers) |
| A polyline's `x` and its `y` | did not meet | follows (each point's `x` and `y` are containers) |
| Copies of a control | two writers | follows (two writers of the same priority) |
| Refused newcomer: none of its moves happen | stated as a rule | **changes**: see Q2 |
| Newcomer meeting several running writers | refused if any refuses | **changes**: decided per container, see Q2 |
| Inactive writer `(active false)` | cannot be triggered, what runs goes on | follows (not triggered, nothing else changes) |
| Canvas showing or hiding a shape | writes nothing | follows (not a writer) |
| A write that changes nothing | skipped | still skipped, but it takes ownership (part 3) |
| An `on-ready` loop | no other writer may write its containers | follows: an ordinary writer of priority 300 (the author, 2026-11-13) |
| On-view sped up by a press | built | removed (author, 2026-11-12) |

Not about writers meeting, so outside the model: two moves of one animation at the same time
(a compile error), a move reading its `from` and `to` when it starts, and a slider's knob
updating when its target changes.
