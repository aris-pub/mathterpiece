# Concurrency model (draft for review)

Status: draft, 2026-11-13. Nothing here is built. It replaces the case-by-case rules in
reference.md, "Concurrency", once approved.

## The parts

1. **Writers.** The controls and the listeners. A writer is triggered, then emits writes to
   its targets until it ends, is released, or is cancelled. A writer that emits writes is
   running.
2. **Targets.** The free values a write changes. A write to a group's attribute, a shape's
   `pos`, or the `x` of a line is expanded to the free values it changes (each member's
   attribute, the `x` and the `y`, the line's ends). Every rule below is applied to each of
   these values on its own.
3. **Owner and lock.** Each target has at most one owner: the running writer whose write it
   last accepted. An owner with `(exclusive)` locks the target while it runs.
4. **Priority.** Every writer has one of three priorities.
   - **Held:** the reader is holding it now. An `on-drag` from its first accepted write to
     the release, and a slider's knob from its first accepted write to the release.
   - **Reader:** the reader triggered it. A press, a click, a key, a flip, `on-enter`,
     `on-leave`, `on-pointermove`, `on-live`, `on-quiet`, and a play or stepper the reader
     pressed.
   - **Page:** nothing the reader did triggered it. `on-view` and `on-rest`.
5. **Constraints.** Both clamp, as today.
   - **Writer side:** the writer's conditions clamp a write before it is emitted.
   - **Target side:** the target's type constraints clamp a write when it is accepted. A write
     that then changes nothing is not a write: it is skipped, and it takes no ownership.

## The rule for every write

A write from writer A reaches target t.

1. If t is locked by another writer, the write is rejected.
2. Otherwise, if t has an owner B other than A, and A's priority is lower than B's, the write is
   rejected.
3. Otherwise the write is accepted: it is clamped by t's constraints, and A becomes t's owner.
   If B owned t, B is cancelled (Q1).

A rejected write cancels nothing. A writer ends, or is released, and owns nothing after that.

Steps and explore mode are not part of this model: a play's or stepper's step is read from
the scene's values (mtp-wjtd notes).

## Decided questions in the model

- **Q1, decided (author, 2026-11-13).** A writer that loses a target is cancelled: it stops
  emitting writes to every target.
- **Q2, decided (author, 2026-11-13).** Each target is decided on its own, for every writer:
  a writer whose writes are rejected on some targets still has its other writes accepted. A
  play pressed while the reader holds a drag on k moves only its other values. Today's rule
  that a refused newcomer makes none of its moves at all goes away.

## The existing cases, checked

| Case | Today | Under the model |
|---|---|---|
| Reader writer running, reader newcomer | newcomer wins | follows (same priority, newest wins) |
| Reader writer running, page newcomer (`on-view`) | newcomer refused | follows (lower priority) |
| Page writer running, any newcomer | newcomer wins | follows |
| `(exclusive)` writer running, any newcomer | newcomer refused | follows (lock) |
| `(exclusive)` writes that take no time | lock taken and released | follows (lock while it runs) |
| Held drag, `on-enter` onto another shape writing the dragged value | `on-enter` cancels the drag | **changes**: rejected (lower priority), its other writes accepted (author, 2026-11-13) |
| Held drag, `on-view` writing the dragged value | refused | follows (lower priority) |
| Grab with no move, play running on the value | play runs on | follows (no write, no ownership) |
| Held slider knob, reader newcomer writing its value | newcomer cancels the slider | **changes**: rejected (lower priority), as for a drag |
| Slider step from the keyboard | a newcomer of its own | follows (reader, not held) |
| Paused play or stepper | not running | follows (owns nothing) |
| Play written under by another writer | explore mode | not concurrency: the step is read from the scene |
| A writer never cancels itself | stated as a rule | follows (A is already the owner) |
| Group attribute, `pos`, a line's `x` | stated case by case | follows (expanded to free values) |
| Copies of a control | two writers | follows (two writers of the same priority) |
| Refused newcomer: none of its moves happen | stated as a rule | **changes**: see Q2 |
| Newcomer meeting several running writers | refused if any refuses | **changes**: decided per target, see Q2 |
| Inactive writer `(active false)` | cannot be triggered, what runs goes on | follows (not triggered, nothing else changes) |
| Canvas showing or hiding a shape | writes nothing | follows (not a writer) |
| A write that changes nothing | skipped | follows (part 5) |
| Background loop counted as rest | no other writer may write its values | follows (no other writer, no conflict) |
| On-view sped up by a press | built | removed (author, 2026-11-12) |

Not about writers meeting, so outside the model: two moves of one animation at the same time
(a compile error), a move reading its `from` and `to` when it starts, and a slider's knob
following its target.
