(concurrency)=
# Concurrency model

```{include} ../concurrency-model.md
:start-line: 1
:end-line: 4
```

## Movements of one movement group that write to one container

This rule exists because two movements of one movement group that write to the same container at once would leave the value of the container undefined.

```{rule} movements-at-once
Two movements of one movement group that write to the same container ("Containers", below) at times
that overlap are a compile error. A movement writes from its start, set by {doc}`time`, up to its start plus
its duration, and a loop that never ends writes forever. Two times overlap when they start at the same
instant, or when each starts before the other ends.
```

So `(at-once (move k (to 2) (duration 1)) (move k (to 3) (duration 1)))` is a compile error, and
`(at-once (move k (to 0) (duration 0)) (in-order (wait 2) (move k (to 1))))` is not. For a
polyline `pl`, `(at-once (move pl.x (to 3)) (move pl.points (to {[0 0] [2 0]})))` is a compile
error, and `(at-once (move pl.x (to 3)) (move pl.y (to 3)))` is not. The `shift` of a group is a
container of the group and not of its members, so `(at-once (move g.shift (to [1 1])) (move c.x (to 3)))`
is allowed for a member `c` of `g`.

```{include} ../concurrency-model.md
:start-line: 4
```
