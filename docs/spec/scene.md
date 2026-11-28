(scene-page)=
# The scene

This page defines the scene and the tree of its shapes: the coordinates, the shapes and their
attributes, groups, frames, and what the runtime draws for each shape.

## Coordinates

This rule exists so that every position, length and angle in a world model has one meaning.

```{rule} coordinates
In the coordinates of the scene, x grows to the right and y grows up. An angle is in degrees,
counterclockwise from the direction in which x grows. A stroke width, the lengths of a dash, the
length of the head at an end of a line and the size of a font are in screen
pixels, so they keep their size on screen
whatever a canvas shows. Every other length is in the units of the scene.
```

So `(polar 1 90)` is the point `[0 1]`, straight up, and a stroke of width 2 is 2 pixels wide on
the screen in every canvas, however far the reader zooms in.

## The scene and its members

This rule exists to define the scene, which holds every shape that a canvas can show.

````{rule} the-scene
The scene is the object that `(scene N …)` declares, and a source declares at most one scene. Its
signature is ({ref}`signatures`):

```mtp-sig
(scene NAME
  (background:color|none none)
  (shift-x:real 0) (shift-y:real 0) (rotate:real 0) (scale-x:real 1) (scale-y:real 1)
  (doc:string '')
  ITEMS:(shape|variable|exists-when|let|foreach)*)
```

The runtime draws the scene over its `background` in each canvas. A `background` of `none`, the
default, is transparent. The frame of the scene, its `shift-x`, `shift-y`, `rotate`, `scale-x` and `scale-y`, sets how its
coordinates are drawn.
A variable declared in the body is not an attribute of the scene: it is read by its name, as a
variable declared at the top level is ({numref}`scopes`).
````

So `(scene s (scale-y -1) …)` has y pointing down, as in SVG, while everything in the scene is
still written, read and written to in the coordinates of the scene.

This rule exists to define the tree of the scene and its groups, which sets what each group holds and the order in which the runtime draws shapes.

```{rule} members
The members of the scene and of a group are the shapes declared in its {term}`body`, in the order of
the source after the expand step ({numref}`compile-steps`). A group is a shape, so every shape of the
scene that is not declared in the body of a motif or in a `(clip …)` is a member of exactly one group
or of the scene, and they form a tree whose root is the scene. A shape is in a group when it is a
member of that group or of a group in it, at any depth: in `(group g (group h (circle c)))`, `c` is
in `h` and in `g`. The attribute `members` of the scene and of each group is the {term}`list` of its
members, and a member may also be read by its position or its name ({numref}`dot-name-part`). The
runtime draws the members of each in this order, each member over the members before it.
```

So in `(scene s (group g (circle a) (circle b)) (circle c))`, `s.members` is `{g c}` and
`g.members` is `{a b}`, and the runtime draws `a`, then `b`, then `c` over both. Being in a group
and being a member of it differ: in `(group g (group h (circle c)))`, `c` is in `g` but is not a
member of `g`, and `g.members` is `{h}`. A
shape declared in the body of a motif is not a member of anything: it is an attribute of the shape
declared with the motif ({numref}`motif-shapes`). The shape of a `(clip …)` is not a member either
({numref}`clips`).

## Fonts

This rule exists to fix the parts of a font and their defaults, which a text uses for each part that its font does not give.

````{rule} font-parts
A font is a record ({numref}`records`) with this signature:

```mtp-sig
(font NAME
  (family:string|none none)
  (style:(string (one-of 'normal' 'italic' 'oblique')) 'normal')
  (weight:(real (>= 1) (<= 1000)) 400)
  (size:real 16)
  (doc:string ''))
```

A `family` of `none` is the font family of the page where the runtime draws the text, and `size` is
in screen pixels.
````

## Shapes

This rule exists to fix the named arguments that the shapes of every kind share, since each one is an attribute of the shape.

````{rule} shape-arguments
`(like shape)` stands for these named arguments, which the signature of every shape holds:

```mtp-sig
(shape NAME
  (shift-x:real 0) (shift-y:real 0) (rotate:real 0) (scale-x:real 1) (scale-y:real 1)
  (fill:color|none (light-dark #'#000000' #'#ffffff'))
  (stroke:color|none none)
  (stroke-width:(real (>= 0)) 1)
  (opacity:unit 1)
  (fill-opacity:unit 1)
  (stroke-opacity:unit 1)
  (dash LENGTHS:list[(real (>= 0))] OFFSET:real?)
  (line-cap:(string (one-of 'butt' 'round' 'square')) 'butt')
  (line-join:(string (one-of 'miter' 'round' 'bevel')) 'miter')
  (drawn:unit 1)
  (pointer-events:bool true))
```
````

This rule exists to fix what each attribute of `(like shape)` does to how the runtime draws the shape.

```{rule} paint-attributes
The attributes of `(like shape)` other than `shift-x`, `shift-y`, `rotate`, `scale-x` and `scale-y`
mean the following.

| Attribute | What it is |
|---|---|
| `fill` | the color of the inside of the shape, and with `none`, no fill. By default black on a light page and white on a dark one |
| `stroke`, `stroke-width` | the color and the width of the line that the runtime draws along the edge of the shape, its stroke, and with `none`, no stroke |
| `opacity`, `fill-opacity`, `stroke-opacity` | how opaque the shape, its fill and its stroke are. The alpha of a color, `fill-opacity` and `stroke-opacity` multiply, and `opacity` fades the drawn shape as a whole, so a fill does not show through a stroke that overlaps it |
| `dash`, `dash-offset` | the lengths of the dashes and the gaps between them in turn, and the distance by which that pattern is shifted along the stroke. `(dash L O)` sets `dash` to L and `dash-offset` to O, or to 0 when O is left out. With no `dash`, `dash` is `{}` and the stroke is solid |
| `line-cap`, `line-join` | the shape of the ends of a stroke, and the shape of its corners |
| `drawn` | the share of the stroke that is drawn |
| `pointer-events` | with `false`, the pointer passes through the shape to what is drawn under it, so the pointer triggers no listener on the shape |
```

So `(circle c (stroke #'black') (dash {4 2}))` has a black stroke of dashes 4 pixels long with
gaps of 2 pixels, and `(move c.dash-offset (to 12) (duration 1))` moves the dashes along the stroke.
A `fill` of `none` and a fill whose alpha is 0 look the same, but the pointer tells them apart. The
inside of a shape with a `fill` of `none` is not part of the shape for the pointer, so a press there
triggers no listener on the shape and reaches what is drawn under it. A fill whose alpha is 0 is part
of the shape, so a press on the inside triggers the listeners on the shape.

This rule exists to fix the named arguments of each kind of shape, their types and their defaults.

````{rule} shape-signatures
These are the signatures of the shapes that are not groups. Each named argument in them is an
attribute of the shape, of the type and with the default that the signature gives. `(like shape)`
stands for the arguments of {numref}`shape-arguments`, and `(like positioned)` stands for
`(x:real 0) (y:real 0)`. The shapes in the first group take their position as arguments. The shapes
in the second group take points instead, and have no `x` or `y` among their arguments, but they
still have the attributes `x` and `y`, which are worked out from their points:

```mtp-sig
; the shapes that take x and y

(circle NAME (like shape) (like positioned)
  (r:(real (>= 0)) 1)
  (doc:string ''))

(rect NAME (like shape) (like positioned)
  (width:real 1)
  (height:real 1)
  (rx:real 0)
  (ry:real 0)
  (doc:string ''))

(ellipse NAME (like shape) (like positioned)
  (rx:real 1)
  (ry:real 1)
  (doc:string ''))

(arc NAME (like shape) (like positioned)
  (r:(real (>= 0)) 1)
  (from:real 0)
  (to:real 360)
  (head-start:(string|none (one-of 'dart' 'curved' 'open' 'bar' 'dot')) none)
  (head-end:(string|none (one-of 'dart' 'curved' 'open' 'bar' 'dot')) none)
  (head-size:(real (>= 0)) 1)
  (doc:string ''))

(ring NAME (like shape) (like positioned)
  (r:(real (>= 0)) 1)
  (width:(real (>= 0)) 0.5)
  (from:real 0)
  (to:real 360)
  (doc:string ''))

(text NAME VALUE:string (like shape) (like positioned)
  (halign:(string (one-of 'start' 'middle' 'end')) 'start')
  (valign:(string (one-of 'top' 'middle' 'baseline' 'bottom')) 'baseline')
  (face:font (font_))
  (doc:string ''))

; the shapes that take points

(line NAME (like shape)
  (from:point [0 0])
  (to:point [1 0])
  (head-start:(string|none (one-of 'dart' 'curved' 'open' 'bar' 'dot')) none)
  (head-end:(string|none (one-of 'dart' 'curved' 'open' 'bar' 'dot')) none)
  (head-size:(real (>= 0)) 1)
  (doc:string ''))

(triangle NAME (like shape)
  (a:point [0 0])
  (b:point [1 0])
  (c:point [0 1])
  (doc:string ''))

(polyline NAME (like shape)
  (points:list[point] {})
  (head-start:(string|none (one-of 'dart' 'curved' 'open' 'bar' 'dot')) none)
  (head-end:(string|none (one-of 'dart' 'curved' 'open' 'bar' 'dot')) none)
  (head-size:(real (>= 0)) 1)
  (doc:string ''))

(polygon NAME (like shape)
  (points:list[point] {})
  (doc:string ''))

(bezier NAME (like shape)
  (from:point [0 0])
  (to:point [1 0])
  (controls:list[point] {[0.5 1]})
  (head-start:(string|none (one-of 'dart' 'curved' 'open' 'bar' 'dot')) none)
  (head-end:(string|none (one-of 'dart' 'curved' 'open' 'bar' 'dot')) none)
  (head-size:(real (>= 0)) 1)
  (doc:string ''))
```
````

`VALUE` is the attribute `value` of a text, and `(font_)` is the font whose parts all have their
defaults ({numref}`font-parts`).

:::{admonition} Code differs
:class: note
- The compiler names the shape `bezier` `curve` (compiler.py:313). Bead mtp-qnws.
- A text takes its font with `(font F)`, the attribute `font`, whose default is `none` for the
  font of the page (compiler.py:332). Bead mtp-1vyc.
:::

This rule exists to fix what the runtime draws for each kind of shape.

```{rule} shape-kinds
The runtime draws each kind of shape as the table below gives. A line, a polyline, a bezier and an
arc have no inside, so the runtime draws no fill for them, whatever their `fill` is. The `controls`
of a bezier are one point or two, and their number is known when compiling ({numref}`known-lengths`),
or it is a {term}`compile error`.

| Shape | What the runtime draws |
|---|---|
| circle | the disk of radius `r` around its position |
| rect | the rectangle of size `width` by `height` whose center is its position. With `rx` and `ry` both above 0, its corners are rounded by the ellipse of radii `rx` and `ry`, each at most half of its side |
| ellipse | the ellipse of radii `rx` across and `ry` up around its position |
| line | the segment from `from` to `to` |
| triangle | the triangle with the corners `a`, `b` and `c` |
| polyline | the path through its points in order, open at both ends |
| polygon | the region inside the path through its points in order and back to the first |
| bezier | the Bézier curve from `from` to `to` with its controls: quadratic with one control, cubic with two |
| arc | the part of the circle of radius `r` around its position from the angle `from` to the angle `to`, counterclockwise when `to` is larger and clockwise when it is smaller, and at most one full turn |
| ring | the region between the circle of radius `r` and the circle of radius `r` minus `width` around its position, over the angles of an arc. With a `width` of `r` or more, the region reaches the center. The pointer reaches only the region itself |
| text | its `value` on one line, every space kept and a tab or a line feed drawn as one space, in the font `face`. `halign` puts the start, the middle or the end of the text at its position, and `valign` puts there its top, its middle, the line on which its letters sit, or the bottom of its lowest letters |
```

So `(circle c (r 2) (fill #'teal'))` is a disk of radius 2 around `[0 0]`, and `(arc a (to 90))` is
the quarter of the circle of radius 1 from the point `[1 0]` to the point `[0 1]`.

This rule exists to fix the position of each shape that has no position of its own, and what a write to that position does.

```{rule} positions
A line, a triangle, a polyline, a polygon and a
bezier have no `x` and no `y` of their own. Their `x` and `y` are the mean of their ends, corners or
points: of `from` and `to` for a line, of `a`, `b` and `c` for a triangle, of the points for a
polyline and a polygon, `[0 0]` when there are none, and of `from`, `to` and the controls for a
bezier. A write of a value v to the `x` of such a shape adds v minus its current `x` to the x of each
of those points, so that their mean becomes v, and a write to its `y` does the same with the y.
```

So with `(line l (from [0 0]) (to [2 0]))`, `l.x` is 1, and a write of 3 to `l.x` moves the line to
go from `[2 0]` to `[4 0]`. By {numref}`writable-targets`, such a write is allowed only when each of
the points is free.

This rule exists to fix how the runtime draws the marks at the ends of a line, a polyline, a bezier and an arc.

```{rule} line-heads
`head-start` and `head-end` name the kind of mark, the head, that the runtime draws at the start and
at the end of the shape, and `none` names no head. The runtime draws a head in the stroke of its
shape, at its end of the shape, turned along the shape there, the head at the start pointing away
from the shape. Its length is five stroke widths times `head-size`. A shape with no stroke has no
head.
```

So `(line v (to [3 1]) (stroke #'black') (head-end 'dart'))` is drawn as an arrow from `[0 0]` to
`[3 1]`, with its point at `[3 1]`. `(line m (to [3 0]) (stroke #'black') (head-start 'bar') (head-end 'bar'))`
is drawn as a segment with a short bar across each end.

This rule exists to fix how much of the stroke of a shape the runtime draws for each value of `drawn`, since a movement of `drawn` draws a shape as a pen would.

```{rule} drawn-strokes
The runtime draws the share `drawn` of the stroke of a shape, measured along the stroke from its
start, and the fill whole. The stroke of each shape starts and runs as the table below gives, and is
dashed as it is when whole. A head at the end of the stroke is drawn at the end of the share drawn,
and a head at its start is drawn when `drawn` is above 0. The stroke of a text is always drawn whole,
so `drawn` changes nothing on a text.

| Shape | Where its stroke starts, and the way it runs |
|---|---|
| circle, ellipse | at the angle 0, counterclockwise |
| rect | on its bottom side, at the left end of its straight part, counterclockwise |
| line, polyline, bezier | at its first point, along its points to the last |
| triangle | at `a`, through `b` and `c`, and back to `a` |
| polygon | at its first point, along its points, and back to the first |
| arc | at `from`, to `to` |
| ring over a full turn | two circles, each drawn as a circle, both at once from the angle `from` |
| ring over part of a turn | at `from` on its outer edge, along that edge to `to`, in to the inner edge or to the center, back along the inner edge, and out to where it started |
```

So `(move c.drawn (from 0) (to 1) (duration 1))` draws the stroke of a circle `c` over one
second. A shape whose `stroke` is `none` or whose `stroke-width` is 0 shows no stroke and no heads,
so a change of its `drawn` shows nothing.

## Frames

This rule exists to fix how the frames of a shape and of the collections that hold it place the shape in the scene.

```{rule} frames
The frame of a shape, a collection or the scene is its `shift-x`, `shift-y`, `rotate`, `scale-x`
and `scale-y` ({doc}`data-model`). The runtime draws a shape by applying its own frame to everything
that its attributes place, its position included, then the frame of each collection that it is in,
from the nearest out, and last the frame of the scene. `(shift P)` gives `shift-x` the x of P and
`shift-y` its y, and a form that gives `shift` with `shift-x` or `shift-y` is a compile error.
```

So `(group g (shift-x 5) (circle p (x 1)))` draws `p` at x 6, while the attribute `p.x` holds 1.

:::{admonition} Open question Q-world-model-1
:class: warning
The order in which the parts of one frame apply, and the point about which `rotate` and the scales
apply, are not decided. The options:

- (a) As the compiler does today with a `translate` and a `transform`: the shift first, then the
  rotation and the scales, about the origin of the frame of the collection.
- (b) As CSS applies its `translate`, `rotate` and `scale` properties: the scales first, then the
  rotation, then the shift, so that a shape turns about its own origin.
:::

:::{admonition} Code differs
:class: note
The compiler has no frame attributes: a shape takes `(translate P)` and `(transform T)`, applied in
that order (compiler.py:217-220, web/src/runtime.ts:410-428). Bead mtp-1vyc.
:::

## Collections

This rule exists to fix the named arguments of the forms that declare a group.

````{rule} collection-signatures
`(group …)`, `(row …)` and `(column …)` each declare a group, and have these signatures:

```mtp-sig
(group NAME
  (shift-x:real 0) (shift-y:real 0) (rotate:real 0) (scale-x:real 1) (scale-y:real 1)
  (defaults ITEMS:(A V)*)
  (clip:circle|rect|ellipse|triangle|polygon|ring|none none)
  (fixed-size:bool false)
  (doc:string '')
  MEMBERS:(shape|exists-when|let|foreach)*)

(row NAME (like group)
  (gap:real 0)
  (align:(string (one-of 'top' 'middle' 'bottom')) 'middle'))

(column NAME (like group)
  (gap:real 0)
  (align:(string (one-of 'left' 'middle' 'right')) 'middle'))
```

As for every other shape ({numref}`shape-signatures`), each named argument of a group is an
attribute of it, of the type and with the default that the signature gives. The one exception is
`(defaults …)`, which holds items and not a value, so it is a clause and not an attribute. Apart from
these, its `name` and its `members` ({numref}`members`), a group has no attribute of its own.
````

:::{admonition} Code differs
:class: note
The compiler has no frame attributes on a collection, only `(translate P)` and `(transform T)`
(compiler.py:334). Bead mtp-1vyc.
:::

This rule exists to define what reading and writing an attribute of a collection does, when the attribute belongs to its members.

```{rule} spreads
For a collection `g` and an attribute `A` that `g` does not have, `g.A` is a spread. A read of
`g.A` evaluates to the list of the `A` of each member of `g`, in order, with `none` for a member that has
no `A`. A write of a value to `g.A` writes that value to the `A` of each shape in `g`, at any depth,
that is not a collection. The type of a spread is given in {numref}`form-types`, and when a spread
may be written to in {numref}`writable-targets`.
```

So with `(group g (circle a (r 1)) (circle b (r 2)))`, `g.r` is `{1 2}`, and a movement of `g.r` to
3 writes 3 to `a.r` and to `b.r`. With `(group h (circle a (r 1)) (group k (circle b (r 2))))`,
`h.r` is `{1 {2}}`, and a write of 3 to `h.r` writes 3 to `a.r` and to `b.r`.

:::{admonition} Code differs
:class: note
Reading a spread of an attribute that a member does not have is the compile error "every member of g
must have 'r'" (compiler.py:6571), and so is a spread over a member that is a collection, as `h.r`
above. Bead mtp-ydd4.7.104.
:::

This rule exists to fix which attributes a collection may set on its members, since each member has only some of them.

```{rule} default-attributes
A collection may set these attributes on its members, and only on the members that have them:
every attribute of `(like shape)` except the frame, but no `stroke`, `stroke-width`, `dash`,
`dash-offset`, `line-cap`, `line-join` or `drawn` on a text. It may also set `halign`, `valign` and
`face` on a text, `head-start`, `head-end` and `head-size` on a line, a polyline, a bezier and an arc,
and `fixed-size` on a group.
```

So `(group labels (defaults (fill #'gray') (halign 'middle') (stroke #'black')) …)` sets the
fill and the alignment of each text in `labels`, and the stroke of each other shape, but not the
stroke of a text, since a stroke would outline its letters. A collection never sets a position or a
frame on its members: it moves them with its own frame.

## Defaults on a group and on a shape declared with a motif

This rule exists so that a group can set an attribute once for all its members.

```{rule} collection-defaults
A `(defaults (A V)…)` on a group sets `A` to `V` on each shape in the group that a group may set
`A` on and whose declaration does not set `A`, the nearest group winning. On a
member declared with a motif, each `(A V)` is added to its own `(defaults …)`. On a shape declared with
a motif, which is not a collection ({doc}`data-model`), it sets `A` on every shape of the motif's body,
at any depth, that has `A` and does not set it. Each `A` must be an attribute that a group may set
on its members ({numref}`default-attributes`), or it is a {term}`compile error`.
```

## Rows and columns

This rule exists to fix where a row and a column place their members, so that every runtime lays them out the same way.

```{rule} rows-and-columns
A row and a column are groups that place their members one after another. The first member that
exists stays where its own attributes place it. Each next member that exists is moved so that its box
starts `gap` after the box of the member before it, to the right in a row and down in a column, and
lined up with the box of the first member by the side that `align` names, or by their middles
when `align` is `'middle'`. A member
that does not exist takes no space. A row or a column that holds a text, at any depth, is a compile
error.

The box of a member is the smallest rectangle, with sides along the axes, around its geometry after
its own frame, in the frame of the row or the column, with strokes and heads left out. The move that
a row or a column gives a member applies after the frame of the member.
```

So `(row cells (gap 2) (foreach q 5 (rect_ (width 32) (height 26))))` places five cells 2 apart,
from left to right.

## Clips

This rule exists so that a collection can show its members only inside a region.

```{rule} clips
`(clip S)` on a collection, or on a shape declared with a motif, holds the declaration of a shape S,
which is a circle, a rect, an ellipse, a triangle, a polygon or a ring.
The runtime draws the members of the collection, or the shapes of the motif's body, only inside S,
and the pointer does not reach what S cuts off. S is in the frame of the collection, is never drawn,
is not a member, and always exists, so declaring it `H|none` is a compile error. Like any shape, S may
be read, and its free attributes written to.
```

So in `(group plot (clip (rect window (width 4) (height 2))) …)`, the members of `plot` are drawn
only inside `window`, and `(move window.width (to 0) (duration 1))` hides them, closing in from both
sides.

## Fixed-size groups

This rule exists so that a group can keep the same size on screen, as a handle that the reader drags must.

```{rule} fixed-size-groups
In a group with `(fixed-size true)`, one unit is one screen pixel: the runtime draws its members as if
the units of the scene were pixels, whatever a canvas shows. The frames of the group and of the
collections that it is in apply to its members as to any shape. An expression outside the group that
reads a member reads it at the origin of the group, and the box of the group is that point. The value of
`fixed-size` is known when compiling, and a fixed-size group in a fixed-size group, at any depth, is
a compile error.
```

So `(group grip (shift [1 2]) (fixed-size true) (circle_ (r 6)))` is a disk of radius 6 pixels at
`[1 2]`, of the same size on screen in every canvas and at every zoom. A drag of a fixed-size group
writes to its `shift` ({numref}`drag-group-shift`).

## Shapes that may not exist

This rule exists so that a shape can be in the scene only part of the time.

```{rule} exists-when
`(exists-when S C)`, in a body that may hold it, names a shape S declared before it with
`(H|none N …)`, and C is a `bool`. S exists while C is true, and a shape declared with `H|none` and no
`exists-when` always exists. While S does not exist, the runtime draws it in no canvas, the pointer
does not reach it, and every read of S or of an attribute of S evaluates to `none`. Every shape in a
collection declared with `H|none` is of a type that includes `none`, and does not exist while the
collection does not. A shape has at most one `exists-when`.
```

So with `(bool on true)`, `(circle|none c (r 1)) (exists-when c on)` is drawn only while `on` is
true, and `(+ c.r 1)` has the type `real|none`. An `exists-when` in a formula names a term
({numref}`terms`).

## Shapes declared with a motif or a variant

This rule exists to define the shape that `(M …)` declares for a motif `M`, and its attributes.

```{rule} motif-shapes
`(M N (P X)… ARGS…)` declares an `M`: a shape of type `M` whose attributes are its parameters, the
shapes and variables of the body of `M` ({doc}`data-model`), `x` and `y`, of type `real` and default
0, and the frame. Each parameter `P` holds its argument X, or its default when the form gives none,
and is free, bound or const as a variable whose value is X ({numref}`variables`). The `x` and the `y`
of an `M` place the origin of its body, and its frame applies after them ({numref}`frames`). `ARGS…`
may hold a `(defaults …)` ({numref}`collection-defaults`) and a `(clip …)` ({numref}`clips`). A read or
a write of an attribute of an `M` that a collection may set ({numref}`default-attributes`) is a spread
over the shapes of its body ({numref}`spreads`).
```

So with `(motif dot (((real (>= 0)) size 1)) (circle c (r size)))`, `(dot d1 (size 0.5) (x 2))`
is a circle of radius 0.5 around `[2 0]`, `d1.size` is a free attribute that a slider may write to,
and `d1.c.r` follows it. `d1.fill` is the list of the fill of `d1.c`. The runtime draws the shapes of
the body of an `M` in the order written, at the place of the `M` in the order of its collection.

:::{admonition} Code differs
:class: note
The compiler writes a shape declared with a motif as a collection of the shapes of its body (bead
mtp-ar1u), and gives it `(translate P)` and `(transform T)` for its frame (compiler.py:339). Bead
mtp-1vyc.
:::

This rule exists to define the shape that `(V …)` declares for a variant `V`.

```{rule} variant-shapes
`(V N (P X)… ARGS…)` declares a `V`: the shape S of the variant ({numref}`motif-and-variant-types`),
with each parameter `P` replaced by its argument X, or by its default when the form gives none, and with
the named arguments `ARGS…` of the kind of S. Each parameter is an attribute of the `V`, as for a
motif ({numref}`motif-shapes`).
```

So with `(variant square ((real side 1)) (rect_ (width side) (height side)))`, `(square q (side 2)
(fill #'teal'))` is a teal rect of width and height 2, `q.side` is 2, and `q.width` follows `q.side`.
