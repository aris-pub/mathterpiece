# Reference

Every form, built-in function and constant in mtp. Each entry says exactly which parts are the name, the positional arguments, the optional arguments and the body (see the syntax document, section 8, "The form template"), the types it takes and gives, and where it is undefined.

"Undefined" means: a compile error when the inputs are known when compiling, and `none` while drawing (see the type system document, section 5.c). Constraint names, types and the declaration rule are as in the other documents.

## Coordinates

- **y points up** and x to the right, as in mathematics.
- **Angles** are counterclockwise from the positive x axis. `(polar 1 90)` is straight up; `rotate` turns counterclockwise.
- **A canvas's view box** is given by its lower-left corner (`x`, `y`) and its size (`width`, `height`), in scene units. The default is −10 to 10 in both directions. The whole view box is shown, scaled to fit the element and centered in it. A canvas's `transform` applies about the center of its view box. The reader may pan and zoom what the view box shows (see "Panning and zooming"), which changes only what the canvas shows, never the view box's attributes.
- **Stroke widths and font sizes are in screen units** (CSS pixels): a line keeps the same thickness on screen, and text the same size, whatever the view box and however the canvas is scaled.
- **Every shape has its own frame of reference.** It starts identical to the scene's; then the shape's `translate` and then its `transform` are applied (`translate` is the translation that comes first; `transform` is everything else, and may include further translations), and they apply to the shape and to everything below it in the scene tree. Both act about the origin of the container's frame, so `(rotate 30)` turns a shape around that origin, not around its own position; to turn a shape in place, put its offset inside the transform, after the rotation: `(transform (transform (rotate 30) (translate 6 -6)))`. A group's `translate` and `transform` are its own: they move its members, and are not spread over them.
- **A position is written before the transforms of the shape's containers are applied.** `(group g (translate [5 0]) (circle p (x 1)))` places `p` at x = 1, then the group's translation moves it: it is drawn at 6. The illustrator never converts anything by hand: what is written is where the shape sits before its containers move it.
- **Reading an attribute converts it through every transform that applies to the shape read but not to the expression reading it.** Inside `g`, a sibling reads `p.x` as 1, so `(circle q (x p.x))` sits exactly on `p`; outside `g`, `p.x` reads 6, where `p` is drawn. The runtime stores the 1. A shape's own `translate` and `transform` count too: `(circle p (x 1) (translate [2 0]))` is drawn at 3, and a sibling reads `p.x` as 3. Inside a function, a read uses the frame of the expression that called it. A drag's write converts the other way: it writes the value that, after every transform, lands under the pointer. Writes from animations and toggles are in the target's own frame and are not converted.

## Declarations

### Docstrings

Every declaration may take `doc@'text'`, an optional argument that says what the declared thing is: `(func clamp ((real x) (real lo) (real hi)) doc@'x, kept between lo and hi.' (min hi (max lo x)))`, `(real k 1 (>= 0.2) (<= 3) doc@'The radius of the circle.')`, `(slider size (move k (from 0.2) (to 3)) doc@'Sets the radius of the circle.')`. It goes with the declaration's other optional arguments, and in a function or a motif after the parameters and before the body.

- **`doc@'text'` is `(doc 'text')`:** the reader makes one the other, and either may be written. `mtp fmt` writes `doc@'text'`, and puts a docstring on a line of its own 2 in, with the body, whatever form it documents.

- **It is plain text, known when compiling:** an interpolated string is a compile error. It says what something is; a readout shows what it currently holds.
- **Variables, shapes, components and the rest of the objects** keep it in the compiled model (mtpc.md), and the inventory page `mtp build` writes shows each component's, each listener's and each token's. A function written into the compiled model keeps its own; a type, a motif or an interface keeps it in the compiler only.
- **It is for the illustrator and the author,** never a description for a reader, which is a separate matter (mtp-fl20).
- **It is given once:** two docstrings on one declaration are a compile error. `doc` is a reserved word.

### Imports

`(import house)` reads `house.mtp` from the folder of the file importing it, or, when there is none there, from the standard library. It gives one name, `house`, and what `house.mtp` declares is read through it: `house.ink`, `(house.dial d1)`, `(house.unit u 0.5)`. `(import house ink accent)` gives `ink` and `accent` as names of their own, and not `house`, as Python's `from house import ink, accent` does. There is no way to import every name at once: each name is written, or the file is imported whole.

- **What a file to import holds:** only top-level declarations of colors, fonts, functions, motifs, variants, types, and variables that are `const`, and its own imports. Anything else, such as a scene, a view, a control, an animation or a variable that is not `const`, makes importing it a compile error. A file with no scene still compiles by itself.
- **Names:** the file reads its own declarations by their bare names, and a local name inside it, such as a `let` or a parameter, wins over them as anywhere. A name imported by name cannot also be declared in the importing file. A name a file imported can be imported from it in turn.
- **Once:** a file imported more than once, directly or through other files, is compiled once. A file that imports itself, through the files it imports, is a compile error, as are two different files of the same name.
- **Errors** inside an imported file name that file, as `house.mtp:3:5: …`.
- **Only what is used:** an imported declaration is compiled into the compiled model only when the source uses it, directly or through another imported declaration it uses, such as a function that reads a color. A declaration nothing uses is still checked, so an error in it is still an error.
- **In the .mtpc** there are no imports: what the source uses is written into it, each under the name it is kept by, `house.ink`. An imported token's CSS custom property is named by its file: `--mtp-house-ink`, however it is imported.

### Namespaces

`(namespace theme (color ink '#1f2a44') (color paper '#f6f1e7') (real gap 0.4 (>= 0)))` declares one name, `theme`: a mutable object that is not drawn, whose members are read and written as attributes are, `theme.ink` as `c.r` is. It is declared at the top level, here or in a file to import.

- **What it holds:** variables of any type, free or bound, each declared as at the top level, and other namespaces: `(namespace colors (namespace tab10 (color blue '#1f77b4')))` gives `colors.tab10.blue`. A function, a type, a motif, a variant, a shape or a component in it is a compile error.
- **Names:** inside it, a member reads the members declared before it by their bare names, and they win over names outside: `(color soft (mix ink paper 0.5))`. Outside it, they are read only through it, `theme.soft`. A member it does not have is a compile error.
- **Writing:** a writer writes a free member by its full name, `(slider s (move theme.gap (from 0) (to 1)))`, under the same rules as any variable: not a bound one, not a `const` one, not a token. The namespace itself is never written.
- **Tokens:** a color or font member is a token, and its CSS variable is named by the namespace: `--mtp-theme-ink`, `--mtp-colors-tab10-blue`. A namespace declared in an imported file adds the file's name, `--mtp-house-theme-ink`.

### Interfaces

`(interface inky (color ink) (color paper) (real gap (>= 0)))` declares an interface: a list of attributes, each with its type and any constraints. Any object that has them, of fitting types, satisfies it, shapes and namespaces alike, but no object's own type is ever an interface (type-system.md, section 6). A parameter or a variable declared with it, such as `(inky look day)`, holds an object of any type that satisfies it, and reads only what it lists. A variable holding an object is bound. A motif's parameter declared with an interface, as `(motif card ((inky colors)) …)`, must be given a value in every instance, `(card a (colors day))`, since an object has no default. A color read through it stays the token it reads, so `(circle c (fill look.ink))` with `look` holding `day` is drawn with `--mtp-day-ink`.

### Palettes

`(palette brand (ink '#1f2a44') (paper '#f6f1e7') (soft (mix ink paper 0.5)))` declares named colors, read as `brand.ink`. A palette is a namespace whose members are all colors: its type, `palette`, refines `namespace`, so a palette is accepted wherever a namespace is, and a namespace is not a palette. Each member is written as its name and its color, and reads the members before it by their bare names, as in a namespace. A palette holds colors only, never another palette. Each color is a token, `--mtp-brand-ink`.

### Colormaps

`(colormap heat [navy white crimson] (positions [-5 0 20]))` declares a function from a real to a color, of type `colormap`, an alias of `func[real color]`: a world model calls it as `(heat temp)`, and any function from a real to a color is a colormap. It is two functions composed, from the world model's own values to the interval from 0 to 1, then from that interval to the colors, both set by the one list of positions.

- **Colors:** a list of at least two, tokens or literals.
- **`(positions …)`:** in the world model's own values, known when compiling, never decreasing: a start and an end, `[-5 20]`, with the colors evenly spaced between, or one per color, `[-5 0 20]`. Two may be equal, for a hard edge: `[-4000 0 0 4000]` jumps from the second color to the third at 0. Without it, the colors are evenly spaced from 0 to 1.
- **`(discrete true)`:** each color is one solid step, the steps equal, between the start and the end; such a map takes positions only as `[start end]`. Without it, the colors mix in a straight line between neighbors, in sRGB, as `mix` does.
- **`(wrap-at x)`:** the map goes round: from the last position it mixes from the last color back into the first, reaching it at x, read as positions are, and a value past x starts again from the first position. With `(positions [0 270]) (wrap-at 360)`, four colors sit at 0, 90, 180 and 270, the fourth mixes back into the first between 270 and 360, and 370 gets the color of 10. x comes after the last position. A discrete map keeps its last color from its end to x. Without it, a value past either end gets that end's color.

Each call is compiled where it is written, so the colors it mixes stay the tokens they read: a page restyling `navy` restyles every color the map gives.

### Values and variables

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(T name value)` for any type `T` | required | the value, which may be left out | none | constraints |

`T` is any type or type expression: `(real k 1)`, `(color ink 'navy')`, `(list[color] swatches ['red' 'gold'])`, `(real|none crossing (secd theta))`, `((real (>= 0)) r 1)`. A plain `list` infers its item type from the value.

### Types

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(type name base)` | required | the base type | none | constraints |
| `(motif name params)` | required | the parameter list | none | member declarations, bound variable declarations, `foreach`, `let`, `exists-when` |
| `(variant name params shape)` | required | the parameter list; one shape declaration | none | none |

A parameter list is one typed parameter `(real t 0.5)`, a list of them `((real t 0.5) (color tint 'red'))`, or `()` for none; each may have a default. `()` is also an empty list of `let` bindings, and is never a value.

### Functions

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(func name params body)`, `(func[T] name params body)` | required | the parameter list; the body, one expression | none | none |

`func`'s parameters are always typed. Its result's type is worked out from the body, or written on the head, `func[T]`, with any constraints; the body must then be proved to fit it, and every call has that type and range. A result declared `T|none` may break its constraints: where it does, the call gives `none`. A function may call itself. A function may take the name of a built-in function, such as `sind` or `map`: from its declaration on, that name calls the illustrator's function, and above it, the built-in. It may not take the name of a special form (`if`, `let`, `foreach` …), a type (`real`, `circle`, `slider` …) or a constant (`pi`, `infty` …): that is a compile error.

    (func[point] ahead ((real d)) [d 0])                     ; [d 0] is a point
    (func[(real (>= 0) (<= 1))] nearness ((real x)) (/ (+ (sind x) 1) 2))
 `fn`, a function written in place, is a special form (below).

### The scene and shapes

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(scene name)` | required | none | `(background color)`, `(transform transform)` | shape declarations, variable declarations, `foreach`, `let`, `exists-when` |
| `(group name)` | required | none | `(translate point)`, `(transform transform)`, `(defaults …)` | shape declarations, `foreach`, `let`, `exists-when` |
| `(row name)`, `(column name)` | required | none | those of a group, `(gap real)` (default 0), `(align …)` (a row: `'top' 'middle' 'bottom'`; a column: `'left' 'middle' 'right'`; default `'middle'`) | as a group's |
| `(circle name)` | required | none | shape arguments, `(r (real (>= 0)))` | none |
| `(rect name)` | required | none | shape arguments, `(width real)`, `(height real)`, `(rx real)`, `(ry real)` (rounded corners) | none |
| `(ellipse name)` | required | none | shape arguments, `(rx real)`, `(ry real)` | none |
| `(line name)` | required | none | shape arguments, `(from point)`, `(to point)` | none |
| `(triangle name)` | required | none | shape arguments, `(a point)`, `(b point)`, `(c point)` | none |
| `(polyline name)` | required | none | shape arguments, `(points list[point])`: a path through the points in order, open at both ends, so `line-cap` shapes its ends; its fill is never drawn, as a line's | none |
| `(polygon name)` | required | none | shape arguments, `(points list[point])`: a closed region through the points, the last joined to the first, with a fill; it may be a clip | none |
| `(curve name)` | required | none | shape arguments, `(from point)`, `(to point)`, `(controls list[point])`: a Bézier curve from `from` to `to`, bent toward its controls: one control makes a quadratic, two a cubic, and how many must be known when compiling. By default it arches from `[0 0]` to `[1 0]` with the control `[0.5 1]`. Its fill is never drawn, as a line's | none |
| `(arc name)` | required | none | shape arguments, `(r (real (>= 0)))`, `(from real)`, `(to real)`: part of the outline of the circle of radius `r` around its position, from the angle `from` to the angle `to`, in degrees. It runs counterclockwise when `to` is larger and clockwise when it is smaller, at most one full turn, so moving `to` from 0 to 360 draws the circle growing. Its fill is never drawn, as a line's | none |
| `(ring name)` | required | none | shape arguments, `(r (real (>= 0)))`, `(width (real (>= 0)))`, `(from real)`, `(to real)`: the region between the circle of radius `r` around its position and the circle of radius `r − width`, over the same angles as an arc. A `width` of `r` or more reaches the center: a pie slice, or with no angles a disk. It has a fill, and its stroke outlines every edge; the pointer reaches only the ring itself, so a click in its hole goes to what is under it. It may be a clip | none |
| `(text name value)` | required | the string | shape arguments, `(font font)`, `(halign …)`, `(valign …)`; its font is only given as a declared font variable, never as separate size or family arguments | none |
| `(M name)`, for a motif or variant `M`, such as `(dial d1)` for a motif `dial` | required | none | its parameters; for a motif, those of an instance (see "Containers"); for a variant, the arguments its base takes | none |

Shape arguments are the optional arguments the shapes share:

- **Position**, taken by a circle, a rect, an ellipse, an arc, a ring, a text and a motif instance: `(x real)` `(y real)`, or `(pos point)`, which writes `x` and `y` together, as one point (`c.pos` is `[c.x c.y]`; `pos` is not kept apart from them). A line, a triangle, a polyline, a polygon and a curve take none: their position is computed from their ends, corners or points, and may still be read and written (see below). A group takes none either: its `x`, `y` and `pos` are its members' (see "Containers").
- **Transforms**, taken by every shape, groups included: `(translate point)`, the translation part of its transform, and `(transform transform)`.
- **Fill and stroke**, taken by every shape except containers (below): `(fill color|none)`; `(stroke color|none)`; `(stroke-width (real (>= 0)))`; `(opacity (real (>= 0) (<= 1)))`, `(fill-opacity (real (>= 0) (<= 1)))`, `(stroke-opacity (real (>= 0) (<= 1)))`.
- **Line styles**, taken by every shape except containers: `(dash lengths offset)`, `(line-cap …)` and `(line-join …)`.
- **Pointer events**, taken by every shape, groups included: `(pointer-events bool)`, true by default. With false, the pointer passes through the shape to whatever is drawn under it, as with CSS's `pointer-events: none`: no listener on the shape hears it, and it cannot be dragged. As in CSS, a group's value reaches its members, and a member that gives its own keeps it, so `(group labels (pointer-events false) …)` lets the pointer through every label. A group may also give it in `(defaults …)`, but not both. A dot that follows the pointer, `(on-pointermove v p)` with `(circle_ (pos p) (pointer-events false))`, lets the pointer reach the shapes under it.
- **Heads**, taken by a line, a polyline, a curve and an arc, the shapes with ends: `(head-start kind)` and `(head-end kind)`, each `none` (the default: no head), `'dart'`, `'curved'`, `'open'`, `'bar'` or `'dot'`, and `(head-size real)`, 1 by default. A head is drawn in the shape's stroke, turned along the shape at its end, the start's pointing back, away from the shape; it is five stroke widths long times `head-size`, in screen pixels, so it keeps its size when the reader zooms. A shape with no stroke has no heads. `(line v (to [3 1]) (stroke ink) (head-end 'dart'))` is a vector; `(head-start 'bar') (head-end 'bar')` marks a length.

`(dash lengths offset)` gives a dashed stroke. `lengths`, a list of reals of at least 0, alternate dash and gap, in screen pixels like `stroke-width`, and the optional `offset`, a real (0 if left out), shifts where the pattern starts. The offset is an attribute of its own, `dash-offset`, which a world model reads as `l.dash-offset` and an animation moves, as in `(move l.dash-offset (to 12))`, so that the dashes march along the stroke. It is given only inside `dash`, never as `(dash-offset …)`. `(line-cap 'butt'|'round'|'square')` is the shape of a stroke's ends, and `(line-join 'miter'|'round'|'bevel')` the shape of its corners.

These mirror SVG on purpose (`dash` is its `stroke-dasharray` and `stroke-dashoffset`, `line-cap` and `line-join` its `stroke-linecap` and `stroke-linejoin`): a color's alpha, `fill-opacity` and `stroke-opacity` multiply, and `opacity` fades the drawn shape as a whole, so a fill does not show through an overlapping stroke.

`halign` is one of `'start' 'middle' 'end'`; `valign` is one of `'top' 'middle' 'baseline' 'bottom'`, where `'baseline'` is the line the letters sit on and `'bottom'` is the bottom of the lowest letters.

A text shows its string as written, every space kept: `'   x'` is indented by three spaces, and `'a  b'` has two spaces between its letters. A text is one line, so a tab or a newline (`'\n'`) in its string is shown as one space.

Where each shape is placed by its position: a circle's, an ellipse's, an arc's and a ring's center, a rect's center, a text's anchor point (chosen by `halign` and `valign`). A line's position is its midpoint, a triangle's its centroid, a polyline's or a polygon's the mean of its points (`[0 0]` with none), and a curve's the mean of its ends and its controls. They are computed from the ends, corners or points, so these shapes are declared by them and never given `x`, `y` or `pos`; a writer that writes the position moves every end, corner or point together, and may only do so when they are free.

A scene's `transform` says how its own coordinates are drawn: `(scene s (transform (scale 1 -1)) …)` has y pointing down, as in an SVG. Everything in the scene is written, read and written to in the scene's own coordinates, a canvas's view box is given in them, and the pointer is converted back into them for drags and clicks. Everything follows the transform as drawn, texts included, and the anchor names `top` and `bottom` stay with y: `top` is toward larger y.

`(exists-when name bool)` is an item of a scene, group, `foreach` or motif body, recognized by its head; it is not a special form. It is written after the shape it names, which is declared `T|none`. While `bool` does not hold, the shape does not exist in the scene: no canvas draws it, the pointer does not reach it, and every read of it or of its attributes is `none`. When it is a container, its members do not exist either, so every member of a container declared `T|none` is `T|none` too. A shape takes one `exists-when` at most. A canvas's `when` is different: it shows or hides what exists.

### Containers

A group (a row and a column included) and a motif instance are **containers** (see the data model): they hold shapes and draw nothing themselves. So none has a `fill`, `stroke`, `stroke-width`, `opacity`, `fill-opacity`, `stroke-opacity`, `dash`, `line-cap` or `line-join` of its own.

- **They spread.** On a container, these attributes are read and written on each member, and on a group so are `x`, `y` and `pos`: reading one gives every member's, and writing one writes every member's, a member that gave its own value included. A container's `translate` and `transform` are its own, and are not spread (see "Coordinates").
- **Defaults.** A container's declaration gives these attributes to its members in `(defaults …)`: `(group labels (defaults (fill ink) (font note) (halign 'middle')) …)`. The defaults may also give the texts inside it their `font`, `halign` and `valign`; never `x`, `y` or `pos`, since a container is moved by its `translate`. A member that gives its own value keeps it, as a move's own `ease` wins over the defaults around it, and the nearest container's default wins over one further out.
- **A text** takes no `stroke`, `stroke-width`, `dash`, `line-cap` or `line-join` from a container's defaults, since a stroke would outline its letters; it keeps its own.
- **Heads** in a container's defaults, `(defaults (head-end 'dart') (head-size 2))`, go to its members that have ends: lines, polylines and arcs. A member without ends, such as a circle, takes none, and a member's own head wins.
- **A clip.** A container may take `(clip shape)`, an optional argument, with a circle, rect, ellipse, triangle, polygon or ring declared inside it: `(group plot (clip (rect window (pos [260 -71]) (width 412) (height 126))) …)`. Its members are drawn only inside that shape, and what lies outside it is cut off. The shape is in the container's own frame, as its members are, but it is not one of them: it is never drawn (no canvas may show it), it is not counted, spread over or placed by a row, and it always exists. Like any shape it may be bound, read and moved, so `(move window.width (to 0))` hides the members, closing in on them from both sides. The container's box is its members' box cut to the clip's (see "Placing"), and the pointer does not reach what the clip cuts off: a click or drag there does nothing.
- **A fixed size.** A group may take `(fixed-size true)`, an optional argument known when compiling: `(group grip (translate [1 2]) (fixed-size true) (circle_ (r 6)) (rect_ (width 3) (height 14)))`. Its members are measured in screen pixels around the group's position, as stroke widths and font sizes are, so they keep their size on screen on every canvas, whatever the view box, the zoom or the canvas's width on the page. Only the scale changes: up is up, and the group's own `transform` and the canvas's turn and skew its members as usual. Any shape can be a member, so a handle can be a circle, a square, a bar, or several shapes together. Inside it, one unit is one pixel, so its texts' font sizes and its heads need no converting.
  - **Its position** is one point: `x`, `y` and `pos` give where its `translate` and its containers put it, not its members' positions. Whatever reads its members from outside sees them all there, since in scene units they have no size; its **box** is that point, of no size (see "Placing").
  - **A drag** on it, `(on-drag grip grip.pos)`, moves it by its `translate`, from a press on any member, so its `translate` must be free. A drag on one of its members is a compile error: drag the group instead.
  - **A container's defaults** may give it, `(group corners (defaults (fixed-size true)) (group a …) (group b …))`: it goes to the groups among the members, and no further down. A member's own `(fixed-size false)` wins.
  - **It cannot hold another** fixed-size group, whose members would already be in pixels. `(fixed-size false)`, or nothing, is a group as any other.
- **A motif instance** also has a frame of its own, and its parameters. It takes `x`, `y` and `pos`, which move its frame, and so its members, before its `translate` and `transform`.

### Tokens

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(color name value)` | required | a color | none | constraints |
| `(font name)` | required | none | `(family string)`, `(style …)`, `(weight (real (>= 1) (<= 1000)))`, `(size real)` | none |

A font's `style` is one of `'normal' 'italic' 'oblique'`.

Each part is known when compiling, or reads the same part of another font: `(font variable (family fonts.serif.family) (style 'italic') (size 18))`. Such a part takes the other font's value, and its CSS falls back to the other font's variable, `var(--mtp-variable-family, var(--mtp-fonts-serif-family, …))`, so a page restyling the family restyles this font too, unless it restyles this one itself.

Color and font variables are tokens: the page may restyle them with CSS, so no writer (control or listener) can write them (see the data model, "What changes, and what follows" and "On the page").

### Transitions and animations

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(transition name target)` | required; declared only at the top level | the target: a `name`, the variable or attribute it moves, or `none` for a pure transition | `(from v)`, `(to v)`, `(duration real)`, `(ease …)`, `(path …)`, `(like t)` | none |
| `(move target)` | none; written only inside an animation, a slider or a canvas | the target, as for `transition` | the same as `transition` | none |
| `(animation name)` | required, except when written inline as an item of a control or listener | none | `(defaults (duration real) (ease …))`, `(loop)`, `(loop n)` | moves, `at-once` and `in-order` forms, and the names of animations and transitions |

A **transition** is a trajectory from `from` to `to`, along `path`, over `duration`, with `ease`, and the variable or attribute it moves, its target. Two forms make one: `(transition name target …)` declares a named one at the top level, and `(move target …)` writes one in place, with no name, inside an animation, a slider or a canvas. Every argument but the target may be left out, and is then none. A **pure** transition has `none` as its target and keeps only the trajectory. `(like t)` copies the arguments of the transition named `t`, and the form's own arguments win over them, wherever `(like …)` is written. A transition with no `from` starts from the value of what it moves; with no `to`, ends there.

The body of an animation holds moves, `(at-once …)` and `(in-order …)`, and the names of animations and transitions, which stand for what they name: `(move k (to 1) (duration 2))` moves `k`; `(at-once …)` runs what it holds together and `(in-order …)` one after another, and items written in a row run one after another; the name of an animation runs that animation there, and the name of a transition runs that transition. A move whose target is `none` writes nothing, so in an animation it may give only a duration: `(move none (duration 1))` waits a second, and `(wait 1)` is a shorter way to write it (`(wait)` waits the default duration). A `(foreach …)` in the body puts its moves where it is written, once for each item, as it puts declarations: together inside `at-once`, one after another inside `in-order` or in a row, so `(at-once (foreach b bubbles (move b.popped (to false))))` writes every bubble's at once.

An animation, `at-once` and `in-order` take the optional argument `(defaults (duration real) (ease …))`, either part may be left out, so that the moves inside them need not each give their own: a move's own `duration` or `ease` wins, and otherwise the nearest enclosing default applies.

An animation (not `at-once` or `in-order`) also takes `(loop n)`, which plays its body n times in a row, n an int of at least 1 known when compiling, or `(loop)`, which plays it forever; a round must take some time. Each round starts again from the start of the body: a move with no `from` starts from the value of what it moves then, so it carries on from where the last round left it, and one with a `from` jumps back to it. An animation that loops n times lasts n times as long as one round; one that loops forever has no `duration`, and reading it is a compile error.

Eases: a function of a real from 0 to 1, `func[(real (>= 0) (<= 1)) real]`, or `(step n)`, which is built in. The usual eases are functions in the standard library's `ease` file: `(import ease cubic-in-out)` and `(ease cubic-in-out)`; see "The standard library". An ease is only called from 0 to 1, so a function defined only there fits, and so does one defined on every real, such as a `func[real real]`. `(step n)` is n equal jumps, each at the start of its interval: a 1 s `(step 4)` move from 0 to 4 shows 1 at once and reaches 4 at 0.75 s. A function's value may go past 1 or below 0: a number or a point moved by it goes past its ends, as a spring overshoots, and is still brought into its type's constraints; a color or a bool stops at them. A move with no ease moves in a straight line.

A bool, a string or a choice (section 5.d of the type system) cannot change smoothly, so its ease must be piecewise constant and take only the values 0 and 1: where it is 0 what moves holds its start value, where it is 1 its end value. Such eases are only built in, and for now there is one: `(step-ease p)`, with `p` from 0 to 1 known when compiling, which is 0 before progress `p` and 1 from `p` on (`(step-ease 0)` changes at the start, `(step-ease 1)` at the end). An illustrator cannot write one, since the compiler could not check it.

By default a bool, a string or a choice changes at the start of its move and holds its new value for the rest of the duration, so a move that is cancelled never leaves it in between. An enclosing default ease that is not such an ease does not apply to it.

A move may end, or start, at `none` only when what it moves is declared `T|none`: `(real|none m 2)` may be moved by `(move m (to none))`. A color mixes `none` as transparent, as everywhere. Anything else cannot move smoothly to or from `none`, so it changes as a bool does: at the start of its move, or where a `(step-ease p)` says, and a path is not used.

Paths: a straight line between the ends by default, or a function taking the two ends and the progress.

`a.steps` is the list of transitions an animation plays, in the order it plays them: through `at-once` (in the order written), `in-order` and the animations it names, with each wait as a transition that moves nothing, and for an animation that loops, one round. Its length is known when compiling, so `(foreach t a.steps …)` works, and each step is read like any transition, `a.steps[0].duration`. A transition's `duration` can be read wherever a transition is, such as `(fn ((transition s)) s.duration)`; its `from` and `to` only on a step or a named transition, since their type depends on what it moves. A step does not know when it starts, since that depends on the steps before it: the sum of their durations, in an animation that plays them one after another.

### Components

A view, a control and a readout must have a name: a page places each by its name (see the data model, "On the page"), so one with no name could never be shown, and is a compile error. A listener has no name.

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(canvas name)` | required | none | `(toggle-duration t)` and `(toggle-ease e)`, for toggling the shapes its items give, `(x real)` `(y real)` `(width real)` `(height real)`, `(transform transform)`, `(pan bool)`, `(zoom bool)` or `(zoom lo hi)` | bare names of shapes to show (the scene's name shows the whole scene), and expressions that give a shape, none, or a list of them, such as `(when bool name)`, `(when bool [a b])` or `(if bool a b)`, drawn in the order written, each on top of those before it |
| `(readout name value)` | required | the string (a number is shown by interpolating it: `$'{k:.2f}'`) | `(font font)`, a declared font variable, the only way to set its font | none |
| `(slider name move)` | required | a move, or the name of a transition, with a target, `from` and `to`, and no `duration` or `ease` | `(label string)`, `(step int)` (the number of positions its knob stops at, at least 2), `(active bool)` | conditions |
| `(button name)` | required | none | `(animation …)`, `(label string)`, `(active bool)` | conditions |
| `(play name)` | required | none | `(animation …)`, `(label string)`, `(buttons bool)`, `(autoplay)`, `(autoplay name)`, `(active bool)` | conditions |
| `(toggle name target)` | required | the target: a `name`, the bool it writes, or `none`, and then it holds its own bool | `(label string)`, `(value bool)` (only with `none`), `(active bool)` | conditions |
| `(on-drag shape target)` | none | the shape; the target, a `name`, the variable or attribute the drag writes | `(active bool)` | conditions |
| `(on-click shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)` | conditions |
| `(on-release shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)` | conditions |
| `(on-dragend shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)` | conditions |
| `(on-view canvas)` | none | the canvas | `(animation …)`, `(active bool)` | conditions |
| `(on-enter shape)` | none | the shape | `(animation …)`, `(active bool)` | conditions |
| `(on-leave shape)` | none | the shape | `(animation …)`, `(active bool)` | conditions |
| `(on-pointermove shape target)` | none | the shape or the canvas; the target, a `name`, the point it writes | `(active bool)`, `(stop-propagation bool)` | conditions |

A canvas **toggles** the shapes its items give: when an item starts or stops giving a shape, as `(when show d)` does when `show` changes, or `(if show d c)` does by giving one shape for another, the canvas shows or hides that shape. A toggle takes the canvas's `(toggle-duration t)`, in seconds, 0 (at once) if left out, with its `(toggle-ease e)`, `'linear'` if left out, any ease an animation takes: over that time the items' opacity, as the canvas shows them, goes from 0 to 1 or back. A canvas takes no `move`. The canvas never writes the scene: the opacity is its own. "Toggle" is the word for a canvas showing or hiding one of its items.

## Defaults

What an attribute is when the illustrator leaves it out:

| What | Default |
|---|---|
| `x`, `y`, `translate` | 0, so `[0 0]` |
| `transform` (of a shape, the scene or a canvas) | the identity |
| `fill` | black, `'#000000'` |
| `stroke` | `none` |
| `stroke-width` | 1 (a screen pixel) |
| `opacity`, `fill-opacity`, `stroke-opacity` | 1 |
| `dash` | none, a solid stroke; offset 0 |
| `line-cap`, `line-join` | `'butt'`, `'miter'` |
| circle `r` | 1 |
| rect `width`, `height` | 1; corners `rx`, `ry` 0 |
| ellipse `rx`, `ry` | 1 |
| line | from `[0 0]` to `[1 0]` |
| triangle | corners `[0 0]`, `[1 0]`, `[0 1]` |
| polyline, polygon | `points` `[]`: no points, so nothing is drawn |
| arc, ring | `r` 1, `from` 0, `to` 360: whole; ring `width` 0.5 |
| line, polyline, curve and arc heads | `head-start` and `head-end` `none`, `head-size` 1 |
| row and column `gap`, `align` | 0, `'middle'` |
| text | `halign` `'start'`, `valign` `'baseline'` |
| a font's parts | family: the page's font; style `'normal'`; weight 400; size 16 (screen pixels) |
| scene `background` | `none` |
| canvas view box | −10 to 10 in both directions |
| transition `ease` | none: a straight line |
| transition `duration` | none: a move with no duration takes the default duration of the nearest animation, `at-once` or `in-order` around it, and is a compile error if there is none |
| control `label` | the control's name |
| toggle `value` | `false` |
| slider `step` | none: the slider moves continuously |
| play `buttons` | `false` |
| canvas `pan`, `zoom` | `true`: the reader may pan and zoom it, from the view box up to 10 times closer |

Every type has a value used when no value or default is given: in a variable declared without one, `(real k)`, and in a parameter without a default that an instance or call leaves out.

| Type | Its value |
|---|---|
| `int`, `ratio`, `real`, `complex` | 0 |
| `bool` | `false` |
| `string` | `''` |
| a choice type | its first choice |
| `color` | black |
| `font` | the font defaults above |
| `point` | `[0 0]` |
| `list[T]` | `[]`; with a `(length n)` constraint, n items each with T's value |
| `transform` | the identity |
| `T\|none` | `none` |
| a narrowed number whose 0 breaks its constraints | its lower bound if that bound is allowed (`(>= 1)` gives 1); otherwise there is none, and leaving a value out is a compile error |
| shapes, functions, transitions, animations | none: leaving one out is a compile error |

## Writes and conditions

Every control and listener emits writes to its target (or, through its animation, to the variables and attributes the animation moves).

- **Conditions** are items of a control or listener: any bool expression, recognized as an item because its head is a comparison or another function giving a bool, such as `(>= theta 0)` or `(<= u.x 5)`. They belong to that writer only. Before a write is emitted it is brought into every condition: a condition that compares the variable or attribute written with a value not depending on it, `(>= theta 0)`, `(< theta (* 2 k))`, clamps the write to that limit. Any other condition is a compile error: the compiler must see a direct limit on what is written, and never searches for a value. A drag of a shape's own `pos` writes its `x` and its `y`, so its conditions may limit either, as `(on-drag c c.pos (<= c.x 5) (>= c.y 0))`; `c.pos.x` and `c.pos[0]` are `c.x`. `(when bool)` is different: it decides whether the writer is active (see the data model, "Writers"). An inactive control is shown disabled.
- **Constraints on the target** (on its type) then apply to every write it receives, from any writer: a range clamps, an int rounds, a value that wraps is brought into its interval, a choice holds its last valid value. A write that changes nothing is skipped.

### Dragging

- **The press** hits the topmost shape under the pointer, then goes up the scene tree to the nearest shape with an `on-drag` that is active, its `(active bool)` holding. That shape is dragged.
- **The target** is the shape's own position or a number its position depends on.
- **A target that is the shape's own `x`, `y` or `pos`** follows the pointer's motion, keeping the offset the pointer had from the shape at the press: the shape does not jump to center itself under the pointer. A target of `x` alone or `y` alone follows the pointer along that axis only.
- **A target that is a number the shape's position depends on** (`theta` in `(polar 1 theta)`) takes the value that brings the shape closest to where the pointer has moved it. The search starts from the current value and stays near it, so the shape never jumps to another position equally close (the far side of a circle). When no value reaches the pointer exactly, the closest is taken.
- **A group** moves every member by the pointer's motion, and a group with `(fixed-size true)` its `translate` (see "Containers").
- **Any other target is a compile error**, such as an arc's `to`, a ring's `width` or a circle's `r`: the drag moves the shape's position, and these never move it, so no value brings the shape any closer to the pointer. To drag one, declare the number as a variable, have the shape read it, and drag a point whose position depends on it: `(real theta 60) (arc mark (r 1.1) (to theta)) (circle tip (pos (polar 1.1 theta)) (r 0.15)) (on-drag tip theta)`. examples/arcs.mtp does this.

### Panning and zooming

- **Pan:** dragging where no draggable shape is moves what the canvas shows with the pointer, but only inside the view box: the reader never sees past what the illustrator framed, so a pan moves something only once the reader has zoomed in.
- **Zoom:** the wheel, or a pinch on a trackpad or with two fingers, zooms about the pointer. While the pointer is over a canvas that zooms, the wheel does not scroll the page. It zooms between bounds: `(zoom lo hi)`, two reals known when compiling with 1 ≤ lo ≤ hi, from lo times closer than the view box to hi times; by default from 1, the view box itself, to 10. A canvas never shows more than its view box.
- **A double click** goes back to the view box the illustrator gave.
- **Neither writes anything:** they are the canvas's own state, like its toggles, so stroke widths and font sizes stay the same on screen. `(pan false)` or `(zoom false)` turns either off.

### Controls

- **Slider:** it shows its move's path as a track, and the reader scrubs along it: its knob runs from 0 to 1, its `position`, and the target lies that far along the path from `from` to `to`. Clicking the track jumps there; dragging the knob gives the speed. So the move must give a target, `from` and `to`, neither of which may be `none`, and may give a `path`, but no `duration` and no `ease`. With `(step n)` the knob stops at n evenly spaced positions.
- **A slider follows its target:** when another writer changes the variable or attribute its move writes, the knob goes to the position whose value is closest to its new value. Its starting position is found the same way.
- **Button:** a press plays its animation from the start, over time; a press while it runs starts it again.
- **Play:** a press plays the animation, and its label reads "pause" while it runs. A press while it runs pauses it, and the next resumes it; after the end, a press plays it again from the start.
- **A play's buttons:** with `(buttons true)` a play also shows one button per item of its animation's body (or, when the body is a single `in-order`, per item of that), lit while that item runs: clicking one, whatever the state, first cancels every writer moving any variable or attribute the play moves, the play itself included, so a play that was playing stops; then that item runs alone, over time, from wherever things are, and its button is lit while it runs. The play's next press plays from the start.
- **Autoplay:** with `(autoplay)` a play starts by itself when the page loads, in view or not; with `(autoplay name)`, `name` a view or a control declared before it, it starts the first time that comes into view on the page.
- **Toggle:** a checkbox writing its target bool, or holding its own value when its target is `none`; `(value bool)` sets that own value's start, and is an error with a target. On a group's attribute it writes every member, reads true only when every member's is true, and shows a mixed state when the members differ; a click on a mixed toggle sets every member to true. A toggle is read through its value, `show.value`, like any other attribute.
- **On-click:** a click on the shape plays its animation, as a button does. As JavaScript's `click`, a press and a release make a click on the nearest shape that is or holds both the shape pressed and the one released over, whatever the pointer did between (a drag or a pan too).
- **On-release:** like JavaScript's `pointerup`, the pointer released over the shape plays its animation, wherever the press began.
- **On-dragend:** like JavaScript's `dragend`, a drag of the shape that ends plays its animation. A drag starts only once the pointer moves, so a press and release with no move between ends none. The shape is the one whose `on-drag` the drag follows.
- **Order:** a release sets off, in this order, the `on-release` of the shape under the pointer, the `on-dragend` of the shape dragged, and the `on-click`: JavaScript sends `pointerup` before `click`, and `on-dragend` comes between them.
- **Bubbling:** as in the DOM, a click, a release, the end of a drag and a pointer move go up the scene tree from the shape they happen on, and set off every listener of their kind on that shape and on each container holding it whose `(active bool)` holds, innermost first; a pointer move then reaches the canvas's `on-pointermove`. A listener with `(stop-propagation bool)`, while the bool holds, stops the event at its shape, as JavaScript's `stopPropagation()`: the other listeners on that shape still run, and none further up. `on-enter` and `on-leave` take no `stop-propagation`, since JavaScript's `pointerenter` and `pointerleave` do not bubble, and neither does `on-drag`, since a press drags one shape only.
- **On-view:** the first time the canvas comes into view on the page, it plays its animation, as a button does; it never plays again.
- **On-enter and on-leave:** like JavaScript's `pointerenter` and `pointerleave`, the pointer coming onto the shape plays the `on-enter`'s animation, and the pointer going off it, or off the canvas, plays the `on-leave`'s. As in JavaScript, the pointer is over every shape up the scene tree from the one under it: a group is entered from any of its members, and left only when the pointer is off all of them. Each shape plays its own listener, the first of its kind whose `(active bool)` holds; when the pointer moves from one shape to another, the leaves come first, the innermost first, and then the enters, the outermost first.
- **On-pointermove:** like JavaScript's `pointermove`, while the pointer is over the shape, or anywhere over the canvas, each move writes the pointer's position to the target, a point variable or attribute, in the scene's coordinates. When the target is a shape's own `pos`, it is written in the frame the shape's `x` and `y` live in, so the shape sits under the pointer, and a condition may limit either, as `(on-pointermove v lens.pos (<= lens.x 5))`. A group, a fixed-size one too, follows the pointer by its `translate`, written in the frame of the group's container; a group's `pos` is a compile error, since writing it would put every member at the pointer, and so is a target inside a fixed-size group.
- **Touch screens:** as JavaScript's pointer events do, a finger enters a shape when it comes down and leaves when it lifts, and `on-pointermove` writes only while it is down. A canvas that an `on-pointermove` listens to, or that draws a shape one listens to, keeps the page from scrolling under a finger on it.
- **Two writers on one target:** a writer that starts moving a variable or an attribute cancels any other writer moving it. The newest wins, whatever its kind.

## Rounding

One rule, the same in the compiler and the runtime, wherever a number is rounded: `round`, a write into an int, and a format spec such as `{x:.2f}`. **Halves round away from zero:** 2.5 gives 3, −2.5 gives −3, and 0.125 to two decimal places gives 0.13. Rounding works on the number's shortest exact decimal form, not its binary value, so 2.675 to two decimal places gives 2.68.

## Special forms

| Form | Evaluates |
|---|---|
| `(if c a b)` | `c`, then only `a` or `b` |
| `(when c x)` | `c`, then `x` while it holds; otherwise none. It is `(if c x none)`, and takes one value: several go in a list, `(when c [a b])` |
| `(cond (c1 v1) (c2 v2) … (else v))` | the tests in order, then only the value of the first that holds |
| `(and a b …)` | left to right, stopping at the first false |
| `(or a b …)` | left to right, stopping at the first true |
| `(let ((n1 v1) (n2 v2) …) body)` | each value, in order (each may use the names before it), then the body, a single expression; in a scene, group, foreach or motif body, its body holds declarations instead, as that body does, and each value is worked out where the `let` is written |
| `(fn params body)` | nothing until called; binds its parameters in its body. A single parameter may be a bare name, typed by where the function is used; several must all be typed |
| `(. X Y)` | `X`, and `Y` unless it is an attribute name |
| `(name s)` | `s`, a string, which becomes a name |
| `(as T literal)` | nothing: the literal, with the type `T`, for a literal where nothing else gives it one, as in `(as color 'gold')` or `(as point [0 0])`; anything but a literal is a compile error |
| `(type-of x)` | nothing while drawing: `x`, any one expression, is compiled only for its type, and the form gives that type as a string, for debugging. The string is known when compiling, even when `x` is not, and is the type as a type expression writes it: `'int'`, `'ratio'`, `'real'`, `'real\|none'`, `'list[int]'`, `'func[real real]'`, `'circle'`, `'group'`, `'slider'`; a named type, motif or variant by its name (`'unit'`, `'dial'`); a narrowed type with the constraints it was declared with, `'(real (>= 0))'` for `(real k 1 (>= 0))`. A range the compiler proves is not shown: `(type-of (sind k))` is `'real'`. A compile error in `x` is still an error, and a type is not an expression, so `(type-of int)` is an error |
| `(foreach i n decl…)`, `(foreach x xs decl…)`, `(foreach ((i n) (x xs) …) decl…)` | when compiling: the declarations once for each `i` from 0 to n−1, or once for each item `x` of the list `xs` (`g.pos`, the list of every member's position, too; `(foreach i n …)` is `(foreach i (range n) …)`), or each member of a group `g`; the count, or the list's length, must be known when compiling, while the items may be known only while drawing. With several names, written as `let` writes its names, the declarations once for every combination, the last name changing fastest, as `foreach` nested in that order would give: `(foreach ((i 2) (j 3)) …)` goes through (0, 0), (0, 1), (0, 2), (1, 0) and on; each source may use the names before it, so `(foreach ((i 4) (j (range i))) …)` goes through the pairs with `j` below `i` |

## Operators

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `+` `-` `*` | numbers, any count (`-` with one argument negates); points and lists of numbers of equal known length, item by item; `*` also takes real numbers among them, which multiply each item | the broadest input type | a result too large for a real |
| `/` | two numbers | an int over an int gives a ratio; otherwise the broadest input type | dividing by 0 |
| `^` | two numbers | an int to a non-negative int power gives an int, to a negative int power a ratio; a complex input gives a complex; otherwise a real | 0 to a negative power; a negative base to a power that is not an int; a result too large for a real |
| `mod` | two numbers | number, with the sign of the divisor: `(mod -1 360)` is 359 | by 0 |
| `abs` | a number | the same type; a complex gives a real | never |
| `=` `!=` | any two of one type | bool | never (`(= none none)` is true) |
| `<` `<=` `>` `>=` | two reals | bool | never |
| `not` | a bool | bool | never |

## Functions

### Numbers

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `sqrt` | real | real | negative input |
| `round` | real, and optionally a number of decimal places `n` (an int; negative rounds to tens, hundreds, …) | int without `n`, real with it | never |
| `floor` `ceil` | real | int | never |
| `exp` | real | real | a result too large for a real |
| `log` | real, and optionally a base (e if left out) | real | input 0 or below; base 0 or below, or 1 |
| `min` `max` | reals and lists of reals, any count: a list counts as its items, so `(max g.r)` is the largest radius in a group `g` | real | no items at all, as from a list that may be empty |
| `lerp` | `a`, `b`, `t` (reals or points) | the same type | never |
| `rand` | none (0 to 1), or `lo hi` | real, drawn once per page load and never again; each copy of a `rand` (in each `foreach` copy, each motif instance) draws its own; a `rand` inside a function is a compile error for now | never |

### Angles

Two full families: the trigonometric functions whose names end in `d` (`sind`, `asind`, …) take or give degrees; the others take or give radians. `polar`, `to-polar` and `rotate` use degrees.

| Radians | Degrees | Takes | Gives | Undefined (in degrees; the radian versions compute numerically and give `none` only where the result is not a number, since π/2 cannot be hit exactly) |
|---|---|---|---|---|
| `sin` `cos` | `sind` `cosd` | an angle | real | never |
| `tan` | `tand` | an angle | real | at 90 + 180k |
| `sec` | `secd` | an angle | real | at 90 + 180k |
| `csc` `cot` | `cscd` `cotd` | an angle | real | at 180k |
| `asin` `acos` | `asind` `acosd` | real | an angle | outside −1..1 |
| `atan` `acot` | `atand` `acotd` | real | an angle | never |
| `asec` `acsc` | `asecd` `acscd` | real | an angle | strictly between −1 and 1 |

Conversions: `rad` (radians to degrees), `turn` (turns to degrees), `deg` (degrees, unchanged), `to-rad` (degrees to radians), `to-turn` (degrees to turns). No conversion is ever undefined.

### Points

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `polar` | radius, angle | point | never |
| `to-polar` | point | `[radius angle]` | the angle at the origin |
| `dist` | two points | real | never |

### Placing

Eight functions give a point on a shape's box, so a shape can be placed against another instead of at a hand-picked position: `(top s)`, `(bottom s)`, `(left s)` and `(right s)` give the middle of that side of `s`'s box, and `(top-left s)`, `(top-right s)`, `(bottom-left s)` and `(bottom-right s)` that corner. An optional second argument pushes the point out by a gap, in scene units, on each side the name says: `(top-right p 0.05)` is 0.05 to the right of the box and 0.05 above it. `top` is toward larger y. The point is as the reading expression sees it, through every `translate` and `transform` it does not share with the shape, as any read of a position is, and it follows the shape: it is recomputed whenever the shape changes.

| Function | Takes | Gives |
|---|---|---|
| `top` `bottom` `left` `right` `top-left` `top-right` `bottom-left` `bottom-right` | a shape, and a gap (default 0) | point; `none` when the shape does not exist |

The point says where the placed shape is anchored, and the placed shape's own alignment says which way it grows from it: `(text_ 'x' (pos (top-right x 2.5)) (valign 'bottom'))` sits above and to the right of `x`.

A shape's **box** is:

- for a circle, a rect, an ellipse, a line, a triangle, a polyline and a polygon (with at least one point; with none, `none`), a curve (around the curve itself, not its controls), an arc and a ring (`none` when `from` equals `to`), the smallest rectangle, with sides along the axes, around its geometry, in scene units; strokes are left out, since their widths are in screen pixels;
- for a shape that is rotated or scaled, the smallest such rectangle around its own box's four corners after its `transform`, which is exact for rects and lines and a little larger than the shape for a rotated circle or ellipse;
- for a group with `(fixed-size true)`, its position, a rectangle of no size, since its members have no size in scene units;
- for a container, the smallest such rectangle around its members' boxes, of the members that exist; `none` when none do; with a clip, that rectangle cut to the clip's box, or, when they do not overlap, a rectangle of no size at the edge of the clip's box nearest the members;
- for a text, not known when compiling, since its size can only be measured in the browser: placing against a text, or a container holding one, is a compile error for now.

A **row** or a **column** is a group that places its members one after another: the first member that exists stays where its own position puts it, and each next one is moved so its box starts a `gap` after the box of the one before, to the right in a row and downward in a column, lined up with the first member by the edge `align` names (by their middles by default).

A member that does not exist takes no space, so the next one moves up into its place; a member that should keep its space can be made transparent instead. A member's own `translate` and `transform` compose with the move its row gives it, as transforms always do, and reading a member's `x`, `y` or `pos` gives where it is drawn. Since a text's box is not known when compiling, a row or a column cannot hold a text yet.

`(row cells (gap 2) (foreach q 5 (rect_ (width 32) (height 26))))` lays five cells out 2 apart.

Only these eight points are built in. For another, a motif declares a member at it, such as a transparent circle, `(circle tip (pos [0 6]) (r 0) (fill none) (stroke none))`, and a shape is placed at `(pos h.tip.pos)`, which follows the instance wherever it is moved.

### Transforms

| Function | Takes | Gives |
|---|---|---|
| `rotate` | degrees | transform |
| `scale` | one factor, or `sx sy` | transform |
| `translate` | `dx dy` | transform |
| `transform` | transforms, any count | their composition |

### Colors

| Function | Takes | Gives |
|---|---|---|
| `mix` | two colors, `t` in 0..1 | color |
| `lighten` `darken` | a color, `t` in 0..1 | color |

A color literal is any CSS color: a name (`'crimson'`), `'#rrggbb'`, `'#rrggbbaa'`.

### Collections

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `map` | a collection, or an int `n`, which stands for `(range n)`, and `func[T U]` | `list[U]` | never |
| `where` | a collection, `func[T bool]` | the members for which it holds | never |
| `sort` | a collection, `func[T real]` | the members, by key, smallest first | never |
| `reverse` | a list | the list reversed | never |
| `reduce` | a collection, a start, `func[A T A]` | `A` | never |
| `sum` | a list of numbers | number | never |
| `count` | a collection, optionally `func[T bool]` | int | never |
| `any` `all` | a list of bools, or a collection and `func[T bool]` | bool | never |
| `somes` | `list[T\|none]` | `list[T]` | never |
| `range` | `n`, which stands for `(range 0 n (gap 1))`; `start stop (gap g)`: from `start`, `g` apart, up to `stop` but not including it, so `(range 0 5 (gap 1))` is `[0 1 2 3 4]` and `(range 5 0 (gap -2))` is `[5 3 1]`; or `start stop (num n)`: `n` items evenly apart from `start` to `stop`, both included, so `(range 0 1 (num 5))` is `[0 0.25 0.5 0.75 1]` | a list of ints when the ends and the gap are ints (with `num`, when the ends are ints known when compiling and every item is whole), of reals otherwise; with every argument known when compiling, a list of known length, and otherwise one whose length is known only while drawing | a gap of 0, a negative `num`, more than a million items |
| `xs[i]`, `g[k]` | a position or key | an item | a position out of range, a missing key |

A function given to one of them takes its parameter's type from the items, and, when the list is known when compiling, their range, whether the parameter is written bare, `(fn k …)`, or with its type, `(fn ((int k)) …)`. So `(map 3 (fn ((int j)) xs[j]))` on a list of three or more reads positions 0 to 2 only, and is never `none`.

### none

| Function | Takes | Gives |
|---|---|---|
| `or?` | `x`, `d` | `x`, or `d` when `x` is none |
| `none?` `some?` | any value | bool |

## The standard library

Files of declarations in `mathterpiece/stdlib/`, imported by name like any other file (see "Imports"): `(import math clamp)`, or `(import math)` and `math.clamp`. Nothing in them is seen without an import. Everything else in this reference is built in.

### colors

Palettes of named colors, read by name: `(import colors)` and `colors.okabe-ito-named.orange`, or `(import colors okabe-ito-named)` and `okabe-ito-named.orange`. Each color is a token, restyled by a page through its CSS variable, `--mtp-colors-okabe-ito-named-orange`.

| Palette | Colors |
|---|---|
| `okabe-ito-named` | Okabe and Ito's eight, which stay apart for readers with any common color blindness: `orange`, `sky-blue`, `bluish-green`, `yellow`, `blue`, `vermillion`, `reddish-purple`, `black` |
| `tab10-named` | matplotlib's default ten: `blue`, `orange`, `green`, `red`, `purple`, `brown`, `pink`, `gray`, `olive`, `cyan` |

The same colors by number, as series and categories take them one after another: `(okabe-ito k)` is color k, counting from 0, and `(tab10 k)` likewise; after the last color they start again, so `(okabe-ito 8)` is orange. Each is a discrete colormap that reads its palette's own colors, so a page restyling one restyles both.

Colormaps from 0 to 1, called as `(colors.viridis 0.3)`, or `(viridis 0.3)` after `(import colors viridis)`. A world model gives its own values its own way: `(viridis (/ depth 50))`, or a function of its own, `(func depth-color ((real m)) (viridis (/ m 50)))`, which is a colormap too.

| Colormap | Colors |
|---|---|
| `okabe-ito`, `tab10` | the palettes above, by number |
| `viridis` | dark purple through blue and green to yellow, readable with the common kinds of color blindness |
| `magma` | black through purple and red to pale yellow, also readable with them |
| `cividis` | dark blue through grey to yellow, made for them |
| `blue-white-red` | diverging: blue to white at 0.5 to red, ColorBrewer's eleven |

The first three are sampled from matplotlib's own at 17 points, so close to them that the difference does not show.

### fonts

Families of fonts: `(import fonts serif)`, or `(import fonts)` and `fonts.serif`. Each is a list of fonts to try in order, as CSS writes it, ending in a family every browser has, with the default style, weight and size. Each is a token, restyled by a page through `--mtp-fonts-serif-family` and the rest.

| Font | Family |
|---|---|
| `serif` | Georgia, Times New Roman, then any serif |
| `sans` | the system's own sans serif, Segoe UI, Helvetica, Arial, then any sans serif |
| `mono` | the system's monospace, Menlo, Consolas, then any monospace |
| `math` | Latin Modern Math, STIX Two Math, Cambria Math, then any serif: fonts made for mathematics |

### math

| Function | Takes | Gives | None when |
|---|---|---|---|
| `dot` | two lists of reals | the sum of their products, item by item | their lengths differ |
| `clamp` | `x`, `lo`, `hi` | `x` kept between `lo` and `hi` | never |
| `smoothstep` | `a`, `b`, `x` | 0 up to `a`, 1 from `b` on, and an S between them, flat at both ends | `a` is `b` |
| `mean` | a list of reals | the mean of its items | the list is empty |
| `norm` | a point | its distance from the origin | never |
| `normalize` | a point | the point in the same direction at distance 1 | the point is `[0 0]` |
| `cross` | two points | the 2D cross product: positive when the second is counterclockwise from the first | never |
| `midpoint` | two points | the point halfway between them | never |

A result that may be none is held in a variable declared `T|none`, or given a default with `or?`.

### types

Types that other files share: `(import types unit)`, or `(import types)` and `types.unit`.

| Type | Is |
|---|---|
| `unit` | a real from 0 to 1, `(type unit real (>= 0) (<= 1))`, such as how far along a move is |

### ease

Functions to give a move as its ease, `(import ease bounce-out)` and `(ease bounce-out)`, or `(import ease)` and `(ease ease.bounce-out)`: each takes the progress from 0 to 1 and gives how far along the move is, 0 at its start and 1 at its end. Each takes a `unit`, from the `types` file, and gives a real. Four kinds, each in three forms: an `-out` ease does its effect at the end, an `-in` ease is the `-out` one turned around, and an `-in-out` ease runs the `-in` one over the first half and the `-out` one over the second.

| Kind | What it does |
|---|---|
| `linear` | a straight line, as a move with no ease takes: to undo an ease given around a move |
| `cubic-in`, `cubic-out`, `cubic-in-out` | the usual eases, starting slowly, ending slowly, or both |
| `spring-in`, `spring-out`, `spring-in-out` | a spring released from rest: past the end once, then it settles |
| `bounce-in`, `bounce-out`, `bounce-in-out` | lands and bounces three times, each bounce smaller |
| `elastic-in`, `elastic-out`, `elastic-in-out` | past the end and back and forth, each swing smaller |
| `back-in`, `back-out`, `back-in-out` | about 10% past the end, and back |

An ease that goes past 1 or below 0 takes what it moves past its ends (see "Transitions and animations").

### marks

Motifs to draw over a world model: `(import marks axes grid)`, then `(axes_)` and `(grid_ (step 2))` in a scene. Every mark is visible with no arguments. Each draws in the color `ink` of this file, a token a page restyles through `--mtp-marks-ink`, unless given `(stroke color)`; anything else, such as its stroke width, it takes from `(defaults …)` like any instance.

| Mark | Parameters | Draws |
|---|---|---|
| `axes` | `left`, `right`, `bottom`, `top` (from -10 to 10, the default view box), `stroke`, `arrows` (false) | the x and y axes through the origin, with a head at their positive ends when `arrows` is true |
| `grid` | `left`, `right`, `bottom`, `top` (from -10 to 10), `step` (1), all `const`; `stroke`, `stroke-opacity` (0.25) | a faint line at every multiple of `step` between the bounds, across and up |
| `angle-mark` | `from` (0), `to` (90), `r` (22), `label` (''), `stroke` | at its position, an arc of radius `r` from the direction `from` to the direction `to`, counterclockwise, and its label just outside the arc's middle; a right angle is marked with a square instead. It is a fixed-size group, so `r` is in screen pixels and the mark keeps its size when the reader zooms |
| `measure` | `from` ([0 0]), `to` ([1 0]), `label` (''), `stroke` | a line from one point to the other with a bar at each end, and its label 6 screen pixels above the middle, whatever the zoom |

## Constants

| Name | Value |
|---|---|
| `pi`, `π` | 3.14159… |
| `tau`, `τ` | 6.28318… |
| `euler` | 2.71828… |
| `infty`, `∞` | infinity, above every number; written `(- infty)` below them (see the type system, section 5.c) |

## Interpolated strings

`$'…{expr}…'` shows each `{expr}`, optionally followed by a format after a colon, using Python's format mini-language: `{x:.2f}` (2 decimals), `{x:+.3f}`, `{p:.0%}` (percent), `{n:d}`, `{x:e}`, `{x:g}`, with fill, alignment and width (`{x:>8.2f}`).
