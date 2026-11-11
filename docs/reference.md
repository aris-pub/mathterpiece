# Reference

Every form, built-in function and constant in mtp. Each entry says exactly which parts are the name, the positional arguments, the optional arguments and the body (see the syntax document, section 8, "The form template"), the types it takes and gives, and where it is undefined.

"Undefined" means: a compile error when the author writes the inputs known when compiling, as in `(sqrt -1)`, and `none` while drawing. A call of a function with known arguments is worked out while compiling, and there an undefined value in its body is `none`, as while drawing, so `or?` in the body catches it (see the type system document, section 5.c). Constraint names, types and the declaration rule are as in the other documents.

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

### Copying a declaration

`(like x)` gives a declaration every argument `x` was written with that it does not give itself: `(circle b-tip (like a-tip) (pos [-1.3 1]) (fill teal))` has `a-tip`'s radius, fill opacity and stroke, and its own position and fill.

- **What is copied is what was written,** compiled again in the new declaration, so the copy follows whatever `x`'s arguments read: if `x`'s radius is `(* 2 k)`, so is the copy's. The copy has its own free values: a drag on `x` does not move it. An argument that should follow `x` itself is written `(r x.r)`.
- **A position written whole** still gives the coordinate the copy leaves out: with `x` at `(pos [1 2])`, `(like x) (x 5)` is at `[5 2]`.
- **Who takes it:** a shape, a motif instance (its arguments and its `(defaults …)`), a variant instance (its parameters and arguments), a font, and a transition or a move. `x` is declared before, and is of the same kind: a circle from a circle, an instance from an instance of the same motif or variant. A container takes none, since its members are its own. One `(like …)` at most, and it comes first, before every other keyword argument; a positional argument, such as a text's string, still comes before it.
- **A variant is different:** it declares a new type of shape. A `(like …)` written the same way in many places is a sign a variant is wanted.

### Names inside the scene, groups and motifs

A shape or a variable declared inside the scene, a group or a motif may not take a name the file declares at its top level or imports by name: inside, it would hide that name, so a read of the name there would get the shape, not the top-level declaration. It is a compile error at the declaration, and the message names both: `(color mark 'red') (motif m () (group mark …))` is `group 'mark' would hide the top-level color 'mark' (1:8): give it another name`. The same holds inside the motifs of an imported file, against that file's own top-level names.

- **A `let` name may hide a top-level name:** it is written right where it is read.
- **A parameter may hide a top-level name**, as in Python: inside a function or a motif, `x` is its parameter `x`, and outside it, the top-level `x`. `(real x 1) (func f ((real x)) (* 10 x))` makes `(f 2)` 20.
- **Only top-level names count:** two motifs may each have a member `c`, and so may the scene. A file imported whole gives only its own name, `house`, so a member `ink` does not hide `house.ink`.

### Imports

`(import house)` reads `house.mtp` from the folder of the file importing it, or, when there is none there, from the standard library. It gives one name, `house`, and what `house.mtp` declares is read through it: `house.ink`, `(house.dial d1)`, `(house.unit u 0.5)`. `(import house ink accent)` gives `ink` and `accent` as names of their own, and not `house`, as Python's `from house import ink, accent` does. There is no way to import every name at once: each name is written, or the file is imported whole.

- **What a file to import holds:** only top-level declarations of colors, fonts, functions, motifs, variants, types, variables that are `const`, and seeds (see "Random values and seeds"), and its own imports. Anything else, such as a scene, a view, a control, an animation or a variable that is not `const`, makes importing it a compile error. A file with no scene still compiles by itself.
- **Names:** the file reads its own declarations by their bare names, and a local name inside it, such as a `let` or a parameter, wins over them as anywhere. A name imported by name cannot also be declared in the importing file, at its top level or inside its scene, groups or motifs (see "Names inside the scene, groups and motifs"). A name a file imported can be imported from it in turn.
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

#### Free starting values

A value given by an expression is bound to it and follows it for as long as the page is open. `free@` makes the opposite: `(list bars free@(shuffled deal))` declares `bars` **free**, starting at the expression's value when the live model is built, and never following it after; any writer may then change it. It may be written wherever a variable's value or a shape's attribute is given, `(circle p (pos free@(meet l1 l2)))`, and nowhere else: not inside an expression. The expression may read whatever a bound expression in the same place may read, other starting values included. One known when compiling is that value, free and not `const`. A `const` variable and a token (a color or font variable) cannot start `free@`.


#### Random values and seeds

Every random value is computed from a **seed**, a free variable of the built-in type `rand-seed`, a whole number of at least 0: `(rand-seed dots 42)`. A random value is bound to its seed and to the place it is written in the source (each `foreach` copy and each motif instance is a place of its own), so the live model is the same on every refresh, and a new seed draws every value that follows it again.

- **Which seed:** a random function follows the only seed the file declares or imports, or the one it names, `(rand 0 1 (seed dots))`. With several, naming one is required. The standard library's `rand` file holds a seed for files that need no seed of their own: `(import rand)`, and random values follow `rand.seed`, which starts at 0. A file that uses something random and neither declares nor imports a seed is a compile error: no file has a seed it did not ask for.
- **The functions:** `(rand)` and `(rand lo hi)` (a real), `(rand-int lo hi)` (an int, both ends included), `(pick xs)` (an item of `xs`, or none when it is empty) and `(shuffle xs)` (the items of `xs` in a random order). Inside a function each is a compile error for now.
- **Rolling the dice** is a write of the seed, as any write is: `(move dots (to (next-seed dots)))`, which `(roll-dice dots)` stands for in an animation, an instant move. `(roll-dice)` rolls the only seed the file declares or imports. A roll redraws only what follows the seed rolled, so a shuffle button with a seed of its own leaves a scatter plot elsewhere where it is. Rolls are reproducible too: the same seed and the same rolls give the same values.
- **A starting state that is random:** a free variable may start at a random value, `(list[int] bars free@(shuffle (range 16)))`, and then never follow the seed (see "Free starting values").

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
| `(func name params body)`, `(func[T] name params body)` | required | the parameter list; the body, one expression, which never holds a declaration: a function computes, and a motif or a variant declares (syntax, "Values and objects") | none | none |

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
- **Drawn**, taken by every shape except containers: `(drawn (real (>= 0) (<= 1)))`, 1 by default, the share of the outline that is drawn (see below).
- **Pointer events**, taken by every shape, groups included: `(pointer-events bool)`, true by default. With false, the pointer passes through the shape to whatever is drawn under it, as with CSS's `pointer-events: none`: no listener on the shape hears it, and it cannot be dragged. As in CSS, a group's value reaches its members, and a member that gives its own keeps it, so `(group labels (pointer-events false) …)` lets the pointer through every label. A group may also give it in `(defaults …)`, but not both. A dot that follows the pointer, `(on-pointermove v p)` with `(circle_ (pos p) (pointer-events false))`, lets the pointer reach the shapes under it.
- **Heads**, taken by a line, a polyline, a curve and an arc, the shapes with ends: `(head-start kind)` and `(head-end kind)`, each `none` (the default: no head), `'dart'`, `'curved'`, `'open'`, `'bar'` or `'dot'`, and `(head-size real)`, 1 by default. A head is drawn in the shape's stroke, turned along the shape at its end, the start's pointing back, away from the shape; it is five stroke widths long times `head-size`, in screen pixels, so it keeps its size when the reader zooms. A shape with no stroke has no heads. `(line v (to [3 1]) (stroke ink) (head-end 'dart'))` is a vector; `(head-start 'bar') (head-end 'bar')` marks a length.

`(dash lengths offset)` gives a dashed stroke. `lengths`, a list of reals of at least 0, alternate dash and gap, in screen pixels like `stroke-width`, and the optional `offset`, a real (0 if left out), shifts where the pattern starts. The offset is an attribute of its own, `dash-offset`, which a world model reads as `l.dash-offset` and an animation moves, as in `(move l.dash-offset (to 12))`, so that the dashes march along the stroke. It is given only inside `dash`, never as `(dash-offset …)`. `(line-cap 'butt'|'round'|'square')` is the shape of a stroke's ends, and `(line-join 'miter'|'round'|'bevel')` the shape of its corners.

These mirror SVG on purpose (`dash` is its `stroke-dasharray` and `stroke-dashoffset`, `line-cap` and `line-join` its `stroke-linecap` and `stroke-linejoin`): a color's alpha, `fill-opacity` and `stroke-opacity` multiply, and `opacity` fades the drawn shape as a whole, so a fill does not show through an overlapping stroke.

`(drawn real)` is the share of the shape's outline that is drawn, from the outline's start, as if by a pen: 0 draws no outline, 0.5 the first half of it, and 1 all of it. It changes the outline only: the fill is drawn whole whatever `drawn` is. A shape with no stroke has no outline to draw, and a text has none either, so `drawn` changes nothing on a text. It is read as `c.drawn` and moved like any attribute, so `(move c.drawn (from 0) (to 1) (duration 1))` draws the circle `c` on over a second. Where each outline starts, and which way it runs, in the scene's coordinates (y pointing up):

- **A circle and an ellipse** start at angle 0, the point to the right of the center, and run counterclockwise, as an arc does when its `to` is larger than its `from`.
- **An arc** runs from its `from` angle to its `to` angle.
- **A ring** with no angles is two circles, each drawn as a circle, both at once, from the ring's `from` angle. A ring over part of a turn has one outline, drawn along its outer edge from `from` to `to`, in to the inner edge (or to the center, when there is no hole), back along the inner edge, and out to where it started.
- **A rect** starts on its bottom side, at the left end of its straight part (its bottom left corner when it has no rounded corners), and runs counterclockwise: right along the bottom, up the right side, and so on. This is where SVG starts a rect's outline.
- **A line** runs from its `from` to its `to`; **a triangle** from `a` to `b` to `c` and back to `a`.
- **A polyline** and **a curve** run along their points in order, from the first to the last; **a polygon** too, and then back to its first point.

The outline drawn keeps its dashes: a dashed outline is drawn on dash by dash, with the pattern it has when whole. A head at the end (see "Heads" above) is drawn at the end of the part drawn, turned along the outline there, so it moves with the pen; a head at the start is drawn as soon as `drawn` is above 0. At 0, neither head is drawn. Each share is of the outline's length in the shape's own frame.

`halign` is one of `'start' 'middle' 'end'`; `valign` is one of `'top' 'middle' 'baseline' 'bottom'`, where `'baseline'` is the line the letters sit on and `'bottom'` is the bottom of the lowest letters.

A text shows its string as written, every space kept: `'   x'` is indented by three spaces, and `'a  b'` has two spaces between its letters. A text is one line, so a tab or a newline (`'\n'`) in its string is shown as one space.

Where each shape is placed by its position: a circle's, an ellipse's, an arc's and a ring's center, a rect's center, a text's anchor point (chosen by `halign` and `valign`). A line's position is its midpoint, a triangle's its centroid, a polyline's or a polygon's the mean of its points (`[0 0]` with none), and a curve's the mean of its ends and its controls. They are computed from the ends, corners or points, so these shapes are declared by them and never given `x`, `y` or `pos`; a writer that writes the position moves every end, corner or point together, and may only do so when they are free.

A scene's `transform` says how its own coordinates are drawn: `(scene s (transform (scale 1 -1)) …)` has y pointing down, as in an SVG. Everything in the scene is written, read and written to in the scene's own coordinates, a canvas's view box is given in them, and the pointer is converted back into them for drags and clicks. Everything follows the transform as drawn, texts included, and the anchor names `top` and `bottom` stay with y: `top` is toward larger y.

`(exists-when name bool)` is an item of a scene, group, `foreach` or motif body, recognized by its head; it is not a special form. It is written after the shape it names, which is declared `T|none`. While `bool` does not hold, the shape does not exist in the scene: no canvas draws it, the pointer does not reach it, and every read of it or of its attributes is `none`. When it is a container, its members do not exist either, so every member of a container declared `T|none` is `T|none` too. A shape takes one `exists-when` at most. A canvas's `when` is different: it shows or hides what exists.

### Containers

A group (a row and a column included) and a motif instance are **containers** (see the data model): they hold shapes and draw nothing themselves. So none has a `fill`, `stroke`, `stroke-width`, `opacity`, `fill-opacity`, `stroke-opacity`, `dash`, `line-cap`, `line-join` or `drawn` of its own.

- **They spread.** On a container, these attributes are read and written on each member, and on a group so are `x`, `y` and `pos`: reading one gives every member's, and writing one writes every member's, a member that gave its own value included. A container's `translate` and `transform` are its own, and are not spread (see "Coordinates").
- **Defaults.** A container's declaration gives these attributes to its members in `(defaults …)`: `(group labels (defaults (fill ink) (font note) (halign 'middle')) …)`. The defaults may also give the texts inside it their `font`, `halign` and `valign`; never `x`, `y` or `pos`, since a container is moved by its `translate`. A member that gives its own value keeps it, as a move's own `ease` wins over the defaults around it, and the nearest container's default wins over one further out.
- **Read from inside.** A group's members may read the group whole: by a position known only while drawing, `(or? verts[j].part 0)`, or as `(map verts …)`, `verts.part` or `(count verts)`. Such a read sees every member, those declared after the reader too, and the reader is recomputed when any of them changes. The group's members may not depend on it: `(foreach i (count g) …)` inside `g` is a compile error.
- **A text** takes no `stroke`, `stroke-width`, `dash`, `line-cap`, `line-join` or `drawn` from a container's defaults, since a stroke would outline its letters; it keeps its own.
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

Color and font variables are tokens: the page may restyle them with CSS, so no writer (control or listener) can write them (see the data model, "What changes, and what follows" and "On the page"). A color token may carry its own dark value, `(color ink (light-dark '#1f2a44' '#e8e4d8'))`, which the page's CSS variable then falls back to, the mode picked by the page's `color-scheme` (see "Colors" under "Functions").

### Formulas

A **formula** is typeset math, as the scene is geometry: `(formula name item…)`, declared at the top level, beside the scene, and shown on the page by a display (see "Components"). It holds its LaTeX, one TeX string fixed when compiling (see "TeX strings"), in which `\term{name}{…}` marks a **term**: a piece of the formula that is an object of its own, read and written as `formula.name`.

```
(formula bounds
  doc@'The squared stretch of the pair, bounded below and above.'
  tex'\term{gap}{\Big(1-\frac1b\Big)^2} P_h(p)
      \mathrel{\term{lo}{\le}} \frac{\mathbb E\,(d(x,A)-d(y,A))^2}{d(x,y)^2}
      \mathrel{\term{hi}{\le}} P_h(p) + \term{b2}{\frac1{b^2}}'
  (term gap (fill teal) (opacity (lit shown 'gap')) (background none) (padding 2) (rounding 3))
  (term b2 (fill coral) (opacity (lit shown 'b2'))))
```

- **Terms** are marked in the LaTeX, each name once, and may nest: `\term{all}{\frac{\term{top}{a}}{b}}` marks `all` and, inside it, `top`. A term's name is a name, as a variable's is. The runtime has MathJax read `\term` as its own `\class`, so the LaTeX goes to MathJax as written.
- **`(term name (attr value)…)`** gives a term's attributes, at most once for each term; a term with no such form has the defaults:

  | Attribute | Type | Default | Is |
  |---|---|---|---|
  | `fill` | color or `none` | `none` | the color of its glyphs; `none` takes the color of the page around the formula |
  | `opacity` | real from 0 to 1 | 1 | |
  | `background` | color or `none` | `none` | a box drawn behind it |
  | `outline` | color or `none` | `none` | a line drawn around it |
  | `outline-width` | real, at least 0 | 1 | the outline's width, in screen pixels |
  | `padding` | real, at least 0 | 0 | how far the box and the outline reach past its glyphs, in screen pixels |
  | `rounding` | real, at least 0 | 0 | the radius of the box's and the outline's corners, in screen pixels |
  | `tex` | string | its LaTeX | its content, in place of what the LaTeX marks |

  The box and the outline never move the glyphs around them. As any attribute, each may be given by an expression, which it then follows, or by a value that a writer may write and move: `(move bounds.gap.background (to wash) (duration 0.2))` fades a box in. `tex` is how values enter a formula: with `\term{v}{}` in the LaTeX, `(term v (tex $'{(* 2 q (- 1 q)):.3f}'))` shows the value, typeset again when it changes.
- **`(defaults (attr value)…)`**, an item of the formula, gives every term those attributes, the ones in the table above but `tex`: `(formula bounds (defaults (padding 3) (rounding 4)) tex'…' …)`. Each term gets its own copy, so a writer writing one term's padding leaves the others alone, and a term's own `(term …)` form wins over them. Once per formula.
- **`(term name (like t) …)`** starts from the arguments of `t`'s form, which comes before it, and its own win: `(term b2 (like gap) (fill coral))`. As everywhere, `(like …)` comes first.
- **`(exists-when name bool)`** says when a term exists: while it does not, it is not shown, and the formula closes up around it.
- **Variables** declared in a formula belong to it: what follows them in the formula reads them by their bare names, and outside it they are read and written by their full names, as `bounds.lit`.
- **Formulas and the scene never read each other.** A formula reads the globals and its own variables; the scene reads the globals and its own. One formula never reads another, and a formula, as the scene, never reads page access. What both follow, such as which piece of a formula the reader picked, is a global.
- **The rest of its look** comes from the page around it: its font, its size and the color of every glyph no term colors.

### Transitions and animations

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(transition name target)` | required; declared only at the top level | the target: a `name`, the variable or attribute it moves, or `none` for a pure transition | `(from v)`, `(to v)`, `(duration real)`, `(ease …)`, `(path …)`, `(like t)` | none |
| `(move target)` | none; written only inside an animation, a slider or a canvas | the target, as for `transition` | the same as `transition` | none |
| `(animation name)` | required, except when written inline as an item of a control or listener | none | `(defaults (duration real) (ease …))`, `(loop)`, `(loop n)` | moves, `at-once`, `in-order` and `step` forms, the names of animations and transitions, and uses of choreos |
| `(choreo name params)` | required; declared only at the top level | the parameter list | the same as `animation` | the same as `animation` |

A **transition** is a trajectory from `from` to `to`, along `path`, over `duration`, with `ease`, and the variable or attribute it moves, its target. Two forms make one: `(transition name target …)` declares a named one at the top level, and `(move target …)` writes one in place, with no name, inside an animation, a slider or a canvas. Every argument but the target may be left out, and is then none. A **pure** transition has `none` as its target and keeps only the trajectory. `(like t)` copies the arguments of the transition named `t`, and the form's own arguments win over them, wherever `(like …)` is written. A transition with no `from` starts from the value of what it moves; with no `to`, ends there.

The body of an animation holds moves, `(at-once …)` and `(in-order …)`, and the names of animations and transitions, which stand for what they name: `(move k (to 1) (duration 2))` moves `k`; `(at-once …)` runs what it holds together and `(in-order …)` one after another, and items written in a row run one after another; the name of an animation runs that animation there, and the name of a transition runs that transition. A move whose target is `none` writes nothing, so in an animation it may give only a duration: `(move none (duration 1))` waits a second, and `(wait 1)` is a shorter way to write it (`(wait)` waits the default duration). `(roll-dice s)` is short for `(move s (to (next-seed s)) (duration 0))`, and `(roll-dice)` rolls the file's only seed (see "Random values and seeds"). A `(foreach …)` in the body puts its moves where it is written, once for each item, as it puts declarations: together inside `at-once`, one after another inside `in-order` or in a row, so `(at-once (foreach b bubbles (move b.popped (to false))))` writes every bubble's at once.

A move reads its `from` and `to` at the instant it starts. What that means for moves that start together or one after another, and when two moves of one animation may move the same thing, is in "Concurrency".

An animation, `at-once` and `in-order` take the optional argument `(defaults (duration real) (ease …))`, either part may be left out, so that the moves inside them need not each give their own: a move's own `duration` or `ease` wins, and otherwise the nearest enclosing default applies.

An animation (not `at-once` or `in-order`) also takes `(loop n)`, which plays its body n times in a row, n an int of at least 1 known when compiling, or `(loop)`, which plays it forever; a round must take some time. Each round starts again from the start of the body: a move with no `from` starts from the value of what it moves then, so it carries on from where the last round left it, and one with a `from` jumps back to it. An animation that loops n times lasts n times as long as one round; one that loops forever has no `duration`, and reading it is a compile error.

**Steps.** The items of an animation's body are its steps: a play with `(buttons true)` shows one bar for each, and a stepper one dot (see "Controls"), and their `step` attribute counts them. When the body is a single `in-order`, its items are the steps. `(step 'name' item…)` makes one step of several items, run one after another as `in-order` does, and gives it a name, which a play shows while that step runs: `(animation (step 'Grow the balls' grow (wait 1)) (step 'Shrink them' shrink))`. The name is optional, `(step grow (wait 1))`, and is a string known when compiling, so a `(foreach …)` of steps may interpolate it: `$'stop {i}'`. A `step` is written only directly in an animation's body; anywhere else it is a compile error. A step with nothing in it is a compile error too. These steps are not the transitions `a.steps` lists, which are what each step is made of.

Eases: a function of a real from 0 to 1, `func[(real (>= 0) (<= 1)) real]`, or `(step n)`, which is built in. The usual eases are functions in the standard library's `ease` file: `(import ease cubic-in-out)` and `(ease cubic-in-out)`; see "The standard library". An ease is only called from 0 to 1, so a function defined only there fits, and so does one defined on every real, such as a `func[real real]`. `(step n)` is n equal jumps, each at the start of its interval: a 1 s `(step 4)` move from 0 to 4 shows 1 at once and reaches 4 at 0.75 s. A function's value may go past 1 or below 0: a number or a point moved by it goes past its ends, as a spring overshoots, and is still brought into its type's constraints; a color or a bool stops at them. A move with no ease moves in a straight line.

A bool, a string or a choice (section 5.d of the type system) cannot change smoothly, so its ease must be piecewise constant and take only the values 0 and 1: where it is 0 what moves holds its start value, where it is 1 its end value. Such eases are only built in, and for now there is one: `(step-ease p)`, with `p` from 0 to 1 known when compiling, which is 0 before progress `p` and 1 from `p` on (`(step-ease 0)` changes at the start, `(step-ease 1)` at the end). An illustrator cannot write one, since the compiler could not check it.

By default a bool, a string or a choice changes at the start of its move and holds its new value for the rest of the duration, so a move that is cancelled never leaves it in between. An enclosing default ease that is not such an ease does not apply to it.

A move may end, or start, at `none` only when what it moves is declared `T|none`: `(real|none m 2)` may be moved by `(move m (to none))`. A color mixes `none` as transparent, as everywhere. Anything else cannot move smoothly to or from `none`, so it changes as a bool does: at the start of its move, or where a `(step-ease p)` says, and a path is not used.

Paths: a straight line between the ends by default, or a function taking the two ends and the progress.

**A choreo** is a template of animations, as a motif is a template of shapes: `(choreo name params item…)` declares a kind of animation, with typed parameters written as a motif's or a function's are, each with an optional default. Its body holds what an animation's body holds, and its moves may move its parameters and their attributes.

    (choreo fade-in ((shape who) (real seconds 0.4))
      doc@'Fades a shape in.'
      (move who.opacity (to 1) (duration seconds)))
    (button show-both (fade-in d1))
    (play reveal (animation (fade-in d1) (fade-in d2 1)))

**A use** of a choreo, `(fade-in d1)`, gives its arguments in order, without their names, and may leave out trailing ones that have defaults. Each use declares an animation in place, the choreo's body with the arguments in place of the parameters, as an inline `(animation …)` does. A use is written where an animation is written:

- **As the animation of a control or a listener**, in place of `(animation …)`: `(button show-both (fade-in d1))` is `(button show-both (animation (fade-in d1)))`, and is the same as `(button show-both (animation (move d1.opacity (to 1) (duration 0.4))))`.
- **As an item of an animation's body**, as the name of an animation is, or of a choreo's body, so one choreo may use another, passing its own parameters on: `(choreo both ((shape a) (shape b)) (at-once (fade-in a) (fade-in b)))`.
- **A named animation** made from a use is an animation whose body holds that use: `(animation third (turn-to 120 'a third of a turn' 10))`.

A use anywhere else, such as at the top level, in the scene or in an expression, is a compile error, as is a form whose head is neither a choreo nor anything an animation holds.

**Arguments are known when compiling**: names of shapes, variables and attributes, literals, constants and eases. Each use is written out by the compiler as an ordinary animation, so the compiled file holds no choreo. A parameter given a name stands for what it names: given a shape, `who.opacity` is that shape's opacity; given a variable or an attribute, a move of the parameter moves it, `(move x (to 1))`, and reading the parameter reads its value when the move starts, as reading the variable itself does. A parameter given a value, such as 3, cannot be moved. An argument that needs the live model, such as `(* 2 k)`, is a compile error, as are a wrong number of arguments and an argument of the wrong type.

**A choreo uses only choreos declared before it**, so a choreo that uses itself, directly or through other choreos, is a compile error: `(choreo pulse ((shape a)) (fade-in a) (pulse a))` is refused. A choreo whose parameters all have defaults is compiled once without a use, so the errors in its body show even when nothing uses it.

**Steps.** A choreo's steps are the items of its body, as an animation's are. A use in an animation's body is one step of it, as the name of an animation is, whatever the choreo's body holds; a use written alone in an animation's body, or as the animation of a play or a stepper, gives that animation the choreo's steps, with their names.

`a.steps` is the list of transitions an animation plays, in the order it plays them: through `at-once` (in the order written), `in-order` and the animations it names, with each wait as a transition that moves nothing, and for an animation that loops, one round. Its length is known when compiling, so `(foreach t a.steps …)` works, and each step is read like any transition, `a.steps[0].duration`. A transition's `duration` can be read wherever a transition is, such as `(fn ((transition s)) s.duration)`; its `from` and `to` only on a step or a named transition, since their type depends on what it moves. A step does not know when it starts, since that depends on the steps before it: the sum of their durations, in an animation that plays them one after another.

### Components

A view, a control and a readout must have a name: a page places each by its name (see the data model, "On the page"), so one with no name could never be shown, and is a compile error. A listener has no name, and is written inside the body of the view it acts in (see "Listeners and controls in views").

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(canvas name)` | required | none | `(toggle-duration t)` and `(toggle-ease e)`, for toggling the shapes its items give, `(x real)` `(y real)` `(width real)` `(height real)`, `(transform transform)`, `(pan bool)`, `(zoom bool)` or `(zoom lo hi)` | bare names of shapes to show (the scene's name shows the whole scene), and expressions that give a shape, none, or a list of them, such as `(when bool name)`, `(when bool [a b])` or `(if bool a b)`, drawn in the order written, each on top of those before it; and its listeners: on its shapes, and its own `on-view`, `on-live`, `on-quiet` and `on-pointermove` |
| `(readout name value)` | required | the string (a number is shown by interpolating it: `$'{k:.2f}'`) | `(font font)`, a declared font variable, the only way to set its font | its `on-live` and `on-quiet` |
| `(display name formula)` | required | the formula it shows | `(kind k)`, known when compiling: `'block'` (the default) for a formula on its own line, or `'inline'` for one inside a paragraph | its listeners: `on-click`, `on-enter` and `on-leave` on the terms of its formula, and its own `on-live` and `on-quiet` |
| `(slider name move)` | required | a move, or the name of a transition, with a target, `from` and `to`, and no `duration` or `ease` | `(label string)` or `(label (tex string))`, `(step int)` (the number of positions its knob stops at, at least 2), `(active bool)`, `(in view…)`, `(exclusive)` | conditions |
| `(button name)` | required | none | `(animation …)`, `(label string)` or `(label (tex string))`, `(selected bool)`, `(active bool)`, `(in view…)`, `(exclusive)` | conditions |
| `(play name)` | required | none | `(animation …)`, `(label string)` or `(label (tex string))`, `(buttons bool)`, `(rest seconds)`, `(autoplay)`, `(autoplay name)`, `(active bool)`, `(in view…)`, `(exclusive)` | conditions |
| `(stepper name)` | required | none | `(animation …)` (required), `(label string)` or `(label (tex string))`, `(active bool)`, `(in view…)`, `(exclusive)` | conditions |
| `(toggle name target)` | required | the target: a `name`, the bool variable or attribute it writes | `(animation …)`, played after each flip, once the bool is written, `(label string)` or `(label (tex string))`, `(active bool)`, `(in view…)`, `(exclusive)` | conditions |
| `(on-drag shape target)` | none | the shape; the target: the shape's own `pos`, `x` or `y`, or `(move target (to expr))`, whose `expr` reads `pointer` | `(active bool)`, `(exclusive)` | conditions |
| `(on-click shape)` | none | the shape, or a term of a formula | `(animation …)`, `(active bool)`, `(stop-propagation bool)`, `(exclusive)` | conditions |
| `(on-release shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)`, `(exclusive)` | conditions |
| `(on-dragstart shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)`, `(exclusive)` | conditions |
| `(on-dragend shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)`, `(exclusive)` | conditions |
| `(on-view)` | none | none: it listens to the canvas whose body holds it | `(animation …)`, `(active bool)`, `(exclusive)` | conditions |
| `(on-live)` | none | none: it listens to the view whose body holds it, a canvas, a readout or a display | `(animation …)`, `(active bool)`, `(exclusive)` | conditions |
| `(on-quiet)` | none | none: it listens to the view whose body holds it, which has an `on-live` | `(animation …)`, `(active bool)`, `(exclusive)` | conditions |
| `(on-enter shape)` | none | the shape, or a term of a formula | `(animation …)`, `(active bool)`, `(exclusive)` | conditions |
| `(on-leave shape)` | none | the shape, or a term of a formula | `(animation …)`, `(active bool)`, `(exclusive)` | conditions |
| `(on-pointermove shape target)` or `(on-pointermove target)` | none | the shape, or none for one on the canvas whose body holds it; the target, a `name`, the point it writes | `(active bool)`, `(stop-propagation bool)`, `(exclusive)` | conditions |

Wherever a control or a listener takes `(animation …)`, a use of a choreo may stand in its place, among its optional arguments: `(button show (fade-in d1) (label 'Show'))` (see "Transitions and animations"). `(exclusive)`, which any listener or control takes, makes the writer refuse every other writer that would write one of its targets while it runs (see "Concurrency").

A canvas **toggles** the shapes its items give: when an item starts or stops giving a shape, as `(when show d)` does when `show` changes, or `(if show d c)` does by giving one shape for another, the canvas shows or hides that shape. A toggle takes the canvas's `(toggle-duration t)`, in seconds, 0 (at once) if left out, with its `(toggle-ease e)`, `'linear'` if left out, any ease an animation takes: over that time the items' opacity, as the canvas shows them, goes from 0 to 1 or back. A canvas takes no `move`. The canvas never writes the scene: the opacity is its own. "Toggle" is the word for a canvas showing or hiding one of its items.

#### Listeners and controls in views

Every listener is written inside the body of the view it acts in, after the view's optional arguments. Controls stay at the top level and name the views they belong to with `(in view…)`: one or more views (canvases, readouts, displays) declared before it, by name.

```
(canvas view-1 (pan false)
  space
  (on-drag car-1 car-1.pos)
  (on-click car-2 (animation (move speed (to 0) (duration 0.4))))
  (on-view (animation (move speed (to 1) (duration 2))))
  (on-pointermove aim))
(display law motion
  (on-enter motion.v (animation (move lit (to true) (duration 0))))
  (on-leave motion.v (animation (move lit (to false) (duration 0)))))
(readout says $'{speed:.1f} m/s'
  (on-live (animation (move speed (to 0) (duration 0.4)))))
(slider speed-knob (move speed (from 0) (to 5)) (in view-1 says))
```

- **A canvas** holds listeners on the shapes it may show (`on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, and `on-pointermove` on a shape) and its own: `on-view`, `on-live`, `on-quiet`, and `on-pointermove` with only a target, which follows the pointer anywhere over the canvas. **A display** holds listeners on the terms of its formula (`on-click`, `on-enter`, `on-leave`) and its own `on-live` and `on-quiet`. **A readout** holds its `on-live` and `on-quiet`.
- **A listener on its own view** names no view: `(on-view (animation …))` plays when the canvas whose body holds it first comes into view.
- **A listener hears the pointer only in its view.** In every other view that shows its shape, the shape does not react to it: no drag, no click, no release, no hover, no pointer moves, no pointer cursor, no wider touch target and no page kept from scrolling, as if the listener were not there, so a click there goes on up the scene tree as it would without it. A shape that reacts in two canvases has its listener written in both, and each is a listener of its own.
- **A foreach or a let** in a view's body may hold listeners, as it holds declarations elsewhere: `(canvas above shape corners (foreach c corners (on-drag c c.pos)))`. It holds nothing but listeners.
- **A control** with `(in …)` belongs to those views; one without it belongs to none. A control belonging only to views that are quiet is put away until one of them goes live (see "Quiet and live views").
- **While a view is quiet**, the listeners inside it hear nothing in it.
- **Errors:** a listener at the top level or with `(in …)`, each with a message that shows how to write it inside its view, and a listener inside a scene. A listener on a shape inside a readout or a display, or on a term inside a canvas or a display of another formula, since that view never shows what it listens to; one inside a canvas whose items all name shapes, none of which is the listener's shape or holds it. When a canvas has an item that gives a shape by an expression, such as `(when on c)`, the compiler cannot know what it may show, and allows it. An `on-view` or an `on-pointermove` inside a readout or a display, and anything but listeners in a foreach or a let of a view's body. For a control: naming something that is not a view, a name not declared before, the same view twice, or no view at all. A view takes no `(in …)`.

#### Quiet and live views

A view with an `on-live` has a **quiet mode**: it starts **quiet**, at rest, and the reader makes it **live** to use it, and puts it back to quiet when done. A view without one has no quiet mode, and is as it would be without this section.

```
(canvas view (width 600) (height 318)
  space
  (on-live (animation (move view.width (to 400) (duration 0.4))))
  (on-quiet (animation (defaults (duration 0.4)) (at-once (move view.width (to 600)) (move share (to 1))))))
(slider radius (move share (from 0) (to 1)) (in view))
```

- **The quiet look** is the figure as its starting values give it. **The live look** is wherever the `on-live`'s animation takes it: a move of a variable, of a shape's attribute, or of the view's own, such as a canvas's `width` to narrow its view box.
- **Going live:** in its top right corner a quiet view shows a hand, a button; a press on it, or Enter or Space with it focused, makes the view live and plays every `on-live` of the view whose `(active bool)` holds. The hand becomes a cross, which keeps the focus.
- **Going back:** a press on the cross, or Escape with the focus in the view, makes the view quiet again and plays every active `on-quiet` of the view. Nothing moves back by itself: what the `on-quiet` does not move stays where it is. The writers it starts meet the others as anywhere ("Concurrency"): `on-live` and `on-quiet` are the reader's doing.
- **Controls:** a control tied with `(in …)` to views is hidden while every one of them is quiet, and unfolds when one goes live: it grows to its height and fades in, and folds the other way when they are all quiet again, at once when the reader asks for reduced motion. A view without a quiet mode is never quiet, so a control tied to one is always shown, as is a control tied to none.
- **Listeners** inside a view hear nothing in it while it is quiet ("Listeners and controls in views"). `on-view` plays when its canvas first comes into view, quiet or not. In view means on screen and shown: while the canvas or an ancestor is fully transparent (opacity 0), hidden or not displayed, as a page may keep its content while it loads, the canvas is not yet in view, and `on-view` waits until it is shown.
- **Pan and zoom:** a quiet canvas neither pans nor zooms, whatever its `pan` and `zoom`: the wheel, a pinch, a drag on empty canvas and a double click do nothing to it, and a finger on it scrolls the page, so a reader scrolling past on a phone is not caught by it. Live, it pans and zooms as its `pan` and `zoom` allow. Going back to quiet drops what the reader panned and zoomed, back to the canvas's own view box.
- **Two views, two modes:** each view has its own mode, so two canvases of one scene may be one quiet and one live.
- **On the page:** a view with a quiet mode has `data-mtp-mode="quiet"` or `data-mtp-mode="live"`, for the page's CSS. A readout, and a display inside a paragraph, take the hand in the line, after their text. The hand and the cross are drawn 2rem across (1.5rem in the line) and take a press 44 pixels across. They are colored as the controls are ("The controls' look").
- **Errors:** an `on-quiet` inside a view with no `on-live`; an `on-live` or `on-quiet` outside a view's body.

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
| `drawn` | 1, the whole outline |
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

### Concurrency

These are the rules for several writers acting on the same variable or attribute, and for the moves of one animation that run at the same time. One principle decides between writers: whatever the reader is doing now, or did last, wins.

- **Newcomers and running writers.** A writer is a newcomer when it starts: a button's press, a play or a stepper starting, resuming, or being moved along its bar, dots or keys, a move of a slider's knob, a toggle's flip, the press that grabs a shape to drag it, each write of an `on-pointermove`, and any listener's animation starting. A writer is running while its animation plays; a drag is running from the grab to the release, and a slider while the reader holds its knob, from the press to the release. A paused play, and a stepper between two steps, write nothing, so they are not running.
- **Who wins.** When a newcomer would write a variable or an attribute that a running writer writes, who set each off, and whether the running writer is exclusive, decide:

  | The running writer | A newcomer the reader set off | Any other newcomer |
  |---|---|---|
  | set off by the reader, not exclusive | wins: the running writer is cancelled | is refused |
  | exclusive, whoever set it off | is refused | is refused |
  | not set off by the reader, not exclusive | wins: the running writer is cancelled | wins: the running writer is cancelled |

  A **cancelled** writer stops writing, and what it already wrote stays. A **refused** newcomer does not start at all: none of its moves happen, even those on variables and attributes no running writer writes. A refused slider's knob goes back to where it was, and a refused toggle's box stays as it was. A newcomer that meets several running writers is refused if any of them refuses it, and otherwise cancels them all. A newcomer cancels a paused play or a stepper between two steps that writes what it writes, since they are not running. A writer never refuses or cancels itself: a press on a button while its animation runs starts the animation again. Writers moving different variables and attributes go on together.
- **The reader's doing:** a button's press; a play's button, bar and keys; a stepper's buttons, dots and keys; a toggle's flip; a slider's knob; every pointer listener, on shapes and on terms: `on-click`, `on-release`, `on-drag`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave` and `on-pointermove`; `on-live` and `on-quiet`; and a play the reader started that is still running. **Not the reader's doing:** `on-view`, `(autoplay)` and `(autoplay name)`. A play that autoplay started becomes the reader's once the reader presses it, or acts on its bar or keys.
- **For example,** with `(play tour (animation (move k (to 5) (duration 4))))` and `(slider size (move k (from 0) (to 10)))`, moving the knob while `tour` plays stops `tour`, and `k` follows the knob from then on. A canvas's `(on-view (animation (move k (to 0) (duration 1))))` that starts while the reader's `tour` plays is refused, and `tour` plays on; one that starts before the reader presses `tour` is cancelled by the press.
- **`(exclusive)`:** any listener or control may take it, among its optional arguments: `(on-drag a a.pos (exclusive))`, `(button b (animation …) (exclusive))`. While an exclusive writer runs, it refuses every newcomer that would write any of its targets, whoever set the newcomer off, until it ends. So a button's exclusive animation refuses a second button's animation that moves one of the same targets, and lets one that moves only other targets start. The runtime honors `(exclusive)` on every writer, whatever its kind, its targets or its view, even for a write that takes no time: a slider's step, an `on-pointermove`'s write, a toggle's flip, a click's animation that takes no time, a key press on a play or a stepper. Each such write takes the lock on the writer's targets, writes, and then releases the lock, even when the lock is held for no time that can be measured and changes nothing that can be seen, and a newcomer arriving while the lock is held is refused. The lock is always released, even when the write fails. So exclusivity holds in every case, should anything happen between taking the lock and releasing it.
- **A drag** is a running writer from the grab to the release, set off by the reader. While the reader holds a shape, an `on-view` that would move it is refused. A newcomer the reader sets off wins as usual: an `on-enter` the pointer sets off by coming onto another shape, which moves the shape held, cancels the drag, and the shape stops following the pointer until the reader grabs it again. So does an `on-dragstart` or an `on-pointermove` that writes what the drag writes. The release still plays the drag's `on-dragend`. A drag with `(exclusive)` refuses both the `on-view` and the `on-enter`. A drag refused at the grab moves nothing.
- **A slider** is a running writer while the reader holds its knob, set off by the reader, as a drag is: an `on-view` that would move its target meanwhile is refused, and a newcomer the reader sets off cancels it, after which the knob writes nothing until the release. A step of the knob from the keyboard takes no time, and is a newcomer of its own.
- **Groups:** a writer whose target is a group's or a motif instance's attribute is, in every case, the same as one writer with one target per member, at any depth: there is no writing to a group's attribute, the group passes the writes on to its members. So the rules compare the shapes actually written, and apply shape by shape: a writer of `g.r` and a writer of `c.r`, for a member `c` of `g`, both write `c.r`, and the newcomer cancels the other or is refused, either way round. An exclusive writer of `c.r` refuses a newcomer writing `g.r`, so the newcomer writes no member's `r`. A shape's `pos` counts as its `x` and its `y`, so a writer of one meets a writer moving the other.
- **A cancelled play** keeps showing what it showed when it was cancelled: its bar shows how far it had played. A press on its button goes on from where it stopped, as a stepper goes on from its step. A move without `(from …)` starts from the current value, so the move that was cut off starts again from the value of its target as it is at the press, where a slider left `k`, say, and goes on to its `to` over what was left of its duration. The moves that had ended keep what they wrote, and those not yet started start when their time comes, as usual.
- **A cancelled stepper** keeps showing the step it was at, on its dots and its count, and its `step` stays as it was; "›" goes on from there.
- **Copies of a control** are two writers, and these rules decide between them as between any two: moving one cancels the other, which keeps showing what it showed, unless the other is exclusive and running, and then moving this one is refused. Only the copy of a play or stepper moved last writes its `step` and `playing`.
- **An inactive writer** cannot be triggered, but what it already set off goes on (see the data model, "Writers"): an animation that runs when its writer's `(active bool)` stops holding plays on, until it ends or another writer cancels it.
- **A slider follows its target:** when another writer changes it, the knob moves to match (see "Controls").
- **A canvas showing or hiding a shape** writes nothing in the model (see "Components"), so it cancels no writer, and no writer cancels it.
- **A move reads its `from` and `to` at the instant it starts**, not when the animation around it was triggered, and they stay fixed while it runs. Moves that start at the same instant, as the moves of an `at-once` do, all read the values as they were before any of them writes: `(at-once (move a (to b)) (move b (to a)))` swaps `a` and `b`. A move that starts after another has ended reads what that one left, and so does each step of an `in-order`, even when its steps take no time: `(in-order (defaults (duration 0)) (move a (to 5)) (move b (to a)))` sets `b` to 5. Each round of a loop starts its moves again, so a round reads what the reader changed during the last one, such as a slider.
- **Two moves of one animation at the same time:** two parts of one `at-once` that move the same variable or attribute at the same time are a compile error, as are a position and its `x` or `y`. They would start from the same values and undo each other, so one is written after the other with `in-order`. At different times they may, as `(at-once (move k (to 0) (duration 0)) (in-order (wait 2) (move k (to 1))))` does. A loop counts as moving what it moves for as long as it runs.

### Dragging

- **The press** hits the topmost shape under the pointer, then goes up the scene tree to the nearest shape with an `on-drag` that is active, its `(active bool)` holding. That shape is dragged.
- **The target** is the shape's own position, written as a name, or anything else a writer may write, written as a move: `(on-drag tip (move theta (to expr)))`.
- **A target that is the shape's own `x`, `y` or `pos`** follows the pointer's motion, keeping the offset the pointer had from the shape at the press: the shape does not jump to center itself under the pointer. A target of `x` alone or `y` alone follows the pointer along that axis only. `(on-drag p p.pos)` is short for `(on-drag p (move p.pos (to pointer)))`, and `p.x` and `p.y` likewise.
- **A move** takes its target and its `to`, and nothing else: no `from`, `duration`, `ease`, `path` or `(like …)`. At every move of the pointer, the drag writes the value of `to`, which reads the name `pointer`: where the pointer has moved the shape's position to, keeping the offset of the press, in the frame that position lives in (for a fixed-size group, its `translate`'s). The illustrator says how the pointer gives the target; nothing is searched for. An angle, for a handle at `(polar 1.1 theta)`: `(on-drag tip (move theta (to (let ((q (or? (to-polar pointer) [0 theta]))) q[1]))))`. A point a turned copy of the shape reads: `(on-drag copy (move start (to pointer)))`, since the pointer arrives already turned back. Inside the move, `pointer` hides any variable of that name; outside a drag it means nothing.
- **A group** moves every member by the pointer's motion, and a group with `(fixed-size true)` its `translate` (see "Containers").
- **What `to` gives** is written as any write is: brought into the target's constraints, and limited by the listener's conditions. A name that is not the shape's own position, written without a move, is a compile error that shows the move to write. examples/arcs.mtp drags an angle this way.
- **By taps, on a touch screen:** every drag can also be done with two taps, for readers who cannot drag (WCAG 2.2, 2.5.7). A tap (a press and a release with the finger moved less than 8 pixels) on a draggable shape selects it, and the shape shows a ring in the color for what the reader acts on. The next tap on the same canvas moves it there: the drag runs as if the shape had been dragged from where the first tap pressed it to where the second tap is, so its move and its conditions apply, and its `on-dragend` plays. Then the selection ends. Tapping the selected shape again, or tapping anywhere off the canvas, ends the selection without moving it, and so does any press that is not a tap, such as a drag. The tap that moves the shape does whatever else a tap there does, but it selects nothing. A tap on a shape with both an `on-click` and an `on-drag` plays the click and selects the shape.
- **A finger drags** once it has moved 8 pixels from where it pressed, so that a tap does not move the shape a little.

### Panning and zooming

- **Pan:** dragging where no draggable shape is moves what the canvas shows with the pointer. Zoomed in, what is shown stays inside the view box: the reader never sees past what the illustrator framed. Zoomed out past the view box (see Zoom), the view box stays inside what is shown.
- **Zoom:** the wheel, or a pinch on a trackpad or with two fingers, zooms about the pointer. While the pointer is over a canvas that zooms, the wheel does not scroll the page. It zooms between bounds: `(zoom lo hi)`, two reals known when compiling with 0 < lo ≤ hi, from lo times closer than the view box to hi times; by default from 1, the view box itself, to 10. A lo below 1 lets the reader zoom out past the view box: `(zoom 0.5 4)` shows up to twice its width and height.
- **A double click** goes back to the view box the illustrator gave.
- **Neither writes anything:** they are the canvas's own state, like its toggles, so stroke widths and font sizes stay the same on screen. `(pan false)` or `(zoom false)` turns either off.

### Controls

- **Copies of a control:** a page may show one control in two places, as when a block holding it is pinned beside the text. The copies are two writers (see "Concurrency").
- **Label:** a control's label is plain text, `(label 'size')`, or LaTeX, `(label (tex $'C_{k}'))`, the form a term of a formula takes. Plain text is shown as written. LaTeX is typeset as a formula is, and a screen reader hears the LaTeX itself. Either may be an expression that reads the model, and the label follows it. A play and a stepper show no label: theirs only names them for a screen reader.
- **Slider:** it shows its move's path as a track, and the reader scrubs along it: its knob runs from 0 to 1, its `position`, and the target lies that far along the path from `from` to `to`. Clicking the track jumps there; dragging the knob gives the speed. So the move must give a target, `from` and `to`, neither of which may be `none`, and may give a `path`, but no `duration` and no `ease`. With `(step n)` the knob stops at n evenly spaced positions.
- **A slider follows its target:** when another writer changes the variable or attribute its move writes, the knob goes to the position whose value is closest to its new value. Its starting position is found the same way.
- **Button:** a press plays its animation from the start, over time; a press while it runs starts it again. A button that also says which state is the current one, as one of a row choosing a value, takes `(selected bool)`: while it holds the button is filled with `--mtp-control-active`, and a screen reader hears it as pressed. `(button #'forbid-{k}' (animation (move w (to (+ k 2)) (duration 0.6))) (selected (= (round w) (+ k 2))))`. A button that only plays an animation takes none. Only a button takes `selected`.
- **Play:** a play is a round button, then a bar, and the reader acts on both. A press on the button plays the animation, and the button shows a pause sign while it runs. A press while it runs pauses it, and the next resumes it; after another writer cancelled it, a press goes on from where it stopped (see "Concurrency"); after the end, a press plays it again from the start. The play's `label` is the button's name for a screen reader; the button shows no text.
- **A play's bar:** the bar shows how far the animation has played. With `(buttons true)` it is split into one bar per step of the animation (see "Transitions and animations", "Steps"), each as wide as its step's duration, filling while its step plays; under the bars a line says which step is playing, as `2 / 4 · Grow the balls` when the step has a name or `2 / 4` when it has none, or how many there are, `4 steps`, before the play has started. Without it, the default, the bar is one piece for the whole animation and there is no line under it. The reader drags along the bar to scrub through the animation, as a slider scrubs its move, and taps a step's bar to jump to the start of that step, every step before it done. A drag or a tap, like a press, is a newcomer that cancels the writers moving what the play moves, or is refused by them (see "Concurrency"). A drag that starts while the play runs pauses it, and it plays on from where the drag ends; a tap keeps it playing or paused as it was, from the start of the step tapped. Then a press on the button resumes from there. For an animation that loops, the bar shows one round.
- **A play's rest:** `(rest t)`, `t` a number of seconds known when compiling, pauses the play `t` seconds between each pair of steps that follow each other, not before the first or after the last, so the illustrator need not end each step with a `(wait t)`; in an animation that loops, it rests between the steps of each round. While it rests, the step just played keeps its bar full and the next one's waits empty, and the line under the bars still names the step just played. A step's bar is as wide as the step alone, the rest not counted, and the bar is scrubbed over the steps only: a tap on a step's bar goes to the start of the step itself, after the rest before it. Only a play takes a rest.
- **A play's keys:** the play button and the bar each take the keyboard's focus, and show it with a ring. With either focused, Space plays and pauses, the right arrow goes to the next stop, and the left arrow back one. The stops are the start of each step and the end of the animation (the start and the end only, without `(buttons true)`), so the arrows pass over a rest. The left arrow goes back to the start of the step playing, or, within half a second of that start, to the start of the step before, so pressing it twice goes back two while the play runs. Before the play has started, the right arrow goes to the first step's start. Going to a stop keeps the play playing or paused as it was. On a page with only one play or stepper, the keys work from anywhere on the page, so a presenter can drive it without first clicking it, except while what has focus takes keys of its own: a text field, a button, a slider, a toggle.
- **Stepper:** `(stepper name (animation …))` is a play with no clock: the reader moves through the animation's steps one at a time. Its steps are a play's (see "Transitions and animations", "Steps"). It is a round "‹" button, a dot for each step, a round "›" button, drawn as a play's button, and a count after them: the step and the number of steps, as `2 / 3`, and `0 / 3` before the first step. It starts before the first step, at step 0, with nothing of the animation done. "›" plays the next step over time, from where the step before it ended, and stops at that step's end. "‹" jumps at once to the end of the step before, with no animation back; from the first step it goes back to step 0, before anything is done. A tap on a step's dot jumps at once to that step's end, every step before it done and none after it begun. "›" while a step plays ends that step at once and plays the next, so each press moves on by one step. The dots of the steps passed are solid, the current one's is solid with a ring, and those still to come are pale. "‹" is turned off at step 0 and "›" at the last step. Its `step` attribute is the step it is at, or is playing, from 0 to the number of steps, and `playing` holds while a step plays. Any move of the stepper, like a play's, is a newcomer that cancels the writers moving what it moves, or is refused by them (see "Concurrency"). A stepper takes no `(buttons …)`, `(rest …)` or `(autoplay …)`: it stops after each step, and the reader moves it. For a screen reader, the buttons are "previous step" and "next step", and the dots are a group named by the label and the step, as `hints: step 2 of 3`, or `hints: 3 steps` before the first, with the current step's dot marked as the current step.
- **A stepper's keys:** with any part of it focused, the right arrow goes to the next step, as "›" does, and the left arrow to the one before, as "‹" does. Each part takes the keyboard's focus and shows it with a ring. On a page with only one play or stepper, the keys work from anywhere on the page, except while what has focus takes keys of its own, as a play's do.
- **Autoplay:** with `(autoplay)` a play starts by itself when the page loads, in view or not; with `(autoplay name)`, `name` a view or a control declared before it, it starts the first time that comes into view on the page.
- **Toggle:** a checkbox writing its target, a bool variable or attribute: `(bool grid-shown true) (toggle grid grid-shown)`. A toggle holds no bool of its own, so its target is never `none`, `(toggle t none)` is a compile error, and the bool's start is given where the bool is declared. A flip is a writer the reader sets off, decided like any other (see "Concurrency"). On a group's attribute it writes every member, reads true only when every member's is true, and shows a mixed state when the members differ; a click on a mixed toggle sets every member to true. A toggle's value, `grid.value`, reads its target, like any other attribute.
- **On-click:** a click on the shape plays its animation, as a button does. As JavaScript's `click`, a press and a release make a click on the nearest shape that is or holds both the shape pressed and the one released over, whatever the pointer did between (a drag or a pan too).
- **On-release:** like JavaScript's `pointerup`, the pointer released over the shape plays its animation, wherever the press began.
- **On-dragstart:** like JavaScript's `dragstart`, a drag of the shape that starts plays its animation. A drag starts at the first move of the pointer after the press, so a press and release with no move between starts none, and hovering starts none. The shape is the one whose `on-drag` the drag follows. The animation starts before the drag's first write, so a drag may first reset what it then reads, as `(on-dragstart p (animation (move o (to 0) (duration 0))))` with `(on-drag p (move y (to (+ pointer.y o))))`.
- **On-dragend:** like JavaScript's `dragend`, a drag of the shape that ends plays its animation. A drag starts only once the pointer moves, so a press and release with no move between ends none. The shape is the one whose `on-drag` the drag follows.
- **Order:** a release sets off, in this order, the `on-release` of the shape under the pointer, the `on-dragend` of the shape dragged, and the `on-click`: JavaScript sends `pointerup` before `click`, and `on-dragend` comes between them. The move that starts a drag sets off, in this order, the `on-enter`, `on-leave` and `on-pointermove` it causes, the `on-dragstart` of the shape dragged, and then the drag's first write: JavaScript sends `pointermove` before `dragstart`.
- **Bubbling:** as in the DOM, a click, a release, the start and the end of a drag and a pointer move go up the scene tree from the shape they happen on, and set off every listener of their kind on that shape and on each container holding it whose `(active bool)` holds, innermost first; a pointer move then reaches the canvas's `on-pointermove`. A listener with `(stop-propagation bool)`, while the bool holds, stops the event at its shape, as JavaScript's `stopPropagation()`: the other listeners on that shape still run, and none further up. `on-enter` and `on-leave` take no `stop-propagation`, since JavaScript's `pointerenter` and `pointerleave` do not bubble, and neither does `on-drag`, since a press drags one shape only.
- **On-view:** the first time the canvas comes into view on the page, it plays its animation, as a button does; it never plays again.
- **On-live and on-quiet:** when the reader makes the view live, every `on-live` of it plays its animation, as a button does, and when the reader puts it back to quiet every `on-quiet` of it does (see "Quiet and live views").
- **On-enter and on-leave:** like JavaScript's `pointerenter` and `pointerleave`, the pointer coming onto the shape plays the `on-enter`'s animation, and the pointer going off it, or off the canvas, plays the `on-leave`'s. As in JavaScript, the pointer is over every shape up the scene tree from the one under it: a group is entered from any of its members, and left only when the pointer is off all of them. Each shape plays its own listener, the first of its kind whose `(active bool)` holds; when the pointer moves from one shape to another, the leaves come first, the innermost first, and then the enters, the outermost first.
- **On-pointermove:** like JavaScript's `pointermove`, while the pointer is over the shape, or anywhere over the canvas, each move writes the pointer's position to the target, a point variable or attribute, in the scene's coordinates. When the target is a shape's own `pos`, it is written in the frame the shape's `x` and `y` live in, so the shape sits under the pointer, and a condition may limit either, as `(on-pointermove lens.pos (<= lens.x 5))` inside the canvas. A group, a fixed-size one too, follows the pointer by its `translate`, written in the frame of the group's container; a group's `pos` is a compile error, since writing it would put every member at the pointer, and so is a target inside a fixed-size group.
- **Touch screens:** a finger has no hover, so a tap stands for it. A tap on a shape enters it, playing its `on-enter` and its containers', and it stays entered after the finger lifts; it is left, playing its `on-leave`, only when the reader taps or presses somewhere else: another shape, which is then entered, empty canvas, or anywhere else on the page. While a finger is down and moving, the figure follows it: shapes are entered and left as it passes over them, and `on-pointermove` writes where it is. Lifting the finger keeps the last shape entered and the last position written. When the browser takes the finger away from the figure, to scroll or zoom the page, what the press and the moves did stays: the shapes entered stay entered and the last position written stays, but the release does nothing, so no `on-release`, `on-click` or `on-dragend` plays, a drag stops where it is, and a selection for the tap alternative to a drag ends. `on-pointermove` writes only while a finger is down, and a tap writes where it was. A pen that does not hover counts as a finger; the mouse, and a pen that hovers, work as described above.
- **Touch targets:** a finger press that lands on no shape the reader can act on (one with an `on-drag`, `on-click`, `on-release`, `on-enter`, `on-leave` or `on-pointermove`, its own or a container's) but within 22 pixels of one counts as a press on the nearest, measured to the box around what is drawn. So every such shape takes a finger over an area at least 44 pixels across. The mouse stays exact.
- **Page scrolling:** a finger on a shape the reader can act on, or within 22 pixels of one, does not scroll the page; elsewhere on the canvas it does. A canvas that pans or zooms, or that an `on-pointermove` of its own listens to, keeps the page from scrolling anywhere on it; a quiet canvas does not pan or zoom (see "Quiet and live views").
- **Guidance:** these touch rules follow WCAG 2.2 (success criteria 2.5.7, Dragging Movements, and 1.4.13, Content on Hover or Focus), the WARP design system's guidance for interaction with data graphics, Microsoft's touch guidance, and the UW Interactive Data Lab's study of interaction with data graphics on phones (EuroVis 2024).

### The controls' look

The controls are drawn with BRAIID, the design system of RSM documents, and read its CSS tokens, so a page that shows controls loads `braiid.css`; their accent is BRAIID's `--primary-700` (`--primary-600` for a toggle's box). A control has two states: at rest, and in use, while the reader presses it, drags it, or has given it the keyboard's focus, and for a play, while it plays. A page may give each state its own color with two CSS custom properties, set anywhere above the controls, such as on `:root`:

| Property | What it colors | When the page sets none |
|---|---|---|
| `--mtp-control-rest` | a control at rest: a button's text, a slider's knob and the track up to it, a toggle's box, a play's filled bars, a stepper's dots | `--primary-700` (`--primary-600` for a toggle) |
| `--mtp-control-active` | the same, while in use; and a play's and a stepper's round buttons, always, since they are what the reader presses first and a gray there would look turned off | the same as the rest color |

The hand and the cross of a view with a quiet mode take the same two colors: the rest color, and the in-use color under the pointer, while pressed and while focused. So a page that sets neither looks as BRAIID draws it. A page that wants its controls gray at rest and ink while used sets, for example, `--mtp-control-rest: #8a8f98; --mtp-control-active: #1f2a44`. The track a play's bars lie on is the page's text color, faint, in both states.

### Recording mode

For recording a vertical short while a play runs, the page `mtp build` writes, and the dev page, show a figure alone when their address ends in `?record`: `build_golden-tour/index.html?record`. The page then holds only a 9:16 frame, as large as fits the window, on a slightly darker ground so its edges can be found when cropping. In the frame are the figure's first canvas and, under it, its first play's bars and the line naming the step, without the play button, since a viewer cannot press it, and without the canvas's hand when it has a quiet mode; the play shows whether the canvas is quiet or not. Nothing else of the page shows, and the pointer is hidden over the whole window. `&canvas=name` and `&play=name` choose another canvas or play: `?record&canvas=view&play=tour`. The play is driven with its keys (see "A play's keys"), which work from anywhere, since the page holds one play. The frame is sized in CSS pixels to fit the window, not drawn at a fixed 1080 by 1920 and scaled down: a canvas draws its strokes and text in screen pixels, so it looks in the frame as it does on a phone of that width. The screen's pixel density, or the browser's zoom, sets how sharp the recording is.

## Rounding

One rule, the same in the compiler and the runtime, wherever a number is rounded: `round`, a write into an int, and a format spec such as `{x:.2f}`. **Halves round away from zero:** 2.5 gives 3, −2.5 gives −3, and 0.125 to two decimal places gives 0.13. Rounding works on the number's shortest exact decimal form, not its binary value, so 2.675 to two decimal places gives 2.68.

## Special forms

| Form | Evaluates |
|---|---|
| `(if c a b)` | `c`, then only `a` or `b`; when `c` is known when compiling, only the branch it takes is compiled, so a `foreach` copy can start a chain: `(x (if (= k 0) 1 (* 2 (. (name $'d-{(- k 1)}') x))))` |
| `(when c x)` | `c`, then `x` while it holds; otherwise none. It is `(if c x none)`, and takes one value: several go in a list, `(when c [a b])` |
| `(cond (c1 v1) (c2 v2) … (else v))` | the tests in order, then only the value of the first that holds |
| `(and a b …)` | left to right, stopping at the first false |
| `(or a b …)` | left to right, stopping at the first true |
| `(let ((n1 v1) (n2 v2) …) body)` | each value, in order (each may use the names before it), then the body, a single expression; in a scene, group, foreach or motif body, its body holds declarations instead, as that body does, and each value is worked out where the `let` is written, once, however many declarations read its name (in a `foreach` or a motif, once in each copy or instance). Each value is worked out once each time the `let` is, however often its name is read, so `(let ((s (walk (- k 1)))) [(+ s.x s.y) (- s.x s.y)])` calls `walk` once |
| `(fn params body)` | nothing until called; binds its parameters in its body. A single parameter may be a bare name, typed by where the function is used; several must all be typed |
| `(. X Y)` | `X`, and `Y` unless it is an attribute name |
| `(name s)` | `s`, a string, which becomes a name; `#'dot-{k}'` is short for `(name $'dot-{k}')`, and parts may follow it: `#'dot-{k}'.pos` |
| `(as T literal)` | nothing: the literal, with the type `T`, for a literal where nothing else gives it one, as in `(as color 'gold')` or `(as point [0 0])`; anything but a literal is a compile error |
| `(type-of x)` | nothing while drawing: `x`, any one expression, is compiled only for its type, and the form gives that type as a string, for debugging. The string is known when compiling, even when `x` is not, and is the type as a type expression writes it: `'int'`, `'ratio'`, `'real'`, `'real\|none'`, `'list[int]'`, `'func[real real]'`, `'circle'`, `'group'`, `'slider'`; a named type, motif or variant by its name (`'unit'`, `'dial'`); a narrowed type with the constraints it was declared with, `'(real (>= 0))'` for `(real k 1 (>= 0))`. A range the compiler proves is not shown: `(type-of (sind k))` is `'real'`. A compile error in `x` is still an error, and a type is not an expression, so `(type-of int)` is an error |
| `(foreach i n decl…)`, `(foreach x xs decl…)`, `(foreach ((i n) (x xs) …) decl…)` | when compiling: the declarations once for each `i` from 0 to n−1, or once for each item `x` of the list `xs` (`g.pos`, the list of every member's position, too; `(foreach i n …)` is `(foreach i (range n) …)`), or each member of a group `g`; the count, or the list's length, must be known when compiling, while the items may be known only while drawing. A count known only while drawing is allowed when it has an upper bound, `(int n 5 (>= 0) (<= 12))`: the `foreach` makes as many copies as it can be at most, and the shapes of copy `k` exist only while `k` is below the count, as if each had an `exists-when`; reading one that does not exist gives `none`. Without an upper bound it is a compile error. With several names, written as `let` writes its names, the declarations once for every combination, the last name changing fastest, as `foreach` nested in that order would give: `(foreach ((i 2) (j 3)) …)` goes through (0, 0), (0, 1), (0, 2), (1, 0) and on; each source may use the names before it, so `(foreach ((i 4) (j (range i))) …)` goes through the pairs with `j` below `i` |

## Operators

| Function | Takes | Gives | Undefined |
|---|---|---|---|
| `+` `-` `*` | numbers, any count (`-` with one argument negates); points and lists of numbers of equal known length, item by item; `*` also takes real numbers among them, which multiply each item | the broadest input type | a result too large for a real |
| `/` | two numbers | an int over an int gives a ratio; otherwise the broadest input type | dividing by 0 |
| `^` | two numbers | an int to a non-negative int power gives an int, to a negative int power a ratio; a complex input gives a complex; otherwise a real | 0 to a negative power; a negative base to a power that is not an int; a result too large for a real |
| `mod` | two numbers | number, with the sign of the divisor: `(mod -1 360)` is 359 | by 0 |
| `abs` | a number | the same type; a complex gives a real | never |
| `sign` | real | int: -1 below 0, 0 at 0, 1 above 0, so `(* (sign v) 5)` lies from -5 to 5 | never |
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
| `rand` | none (0 to 1), or `lo hi`, and optionally `(seed s)` | a real from `lo` up to `hi`, drawn from a seed (see "Random values and seeds") | never |
| `rand-int` | `lo hi`, and optionally `(seed s)` | an int from `lo` to `hi`, both included, drawn from a seed | never |
| `next-seed` | a seed | the seed a roll of the dice writes after it | never |

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
| `light-dark` | a color for a light page, then one for a dark page | color |

A color literal is any CSS color: a name (`'crimson'`), `'#rrggbb'`, `'#rrggbbaa'`.

**Light and dark pages.** `(light-dark '#1f2a44' '#e8e4d8')` is one color, drawn as its first value where the page around the figure is light and as its second where it is dark, as CSS's `light-dark()` does: the mode is the CSS `color-scheme` of the place the figure is drawn, so a figure in a page that switches to dark switches with it. It is a color, written wherever one is: a color variable `(color ink (light-dark '#1f2a44' '#e8e4d8'))`, a palette member, a colormap's list, a fill, a stroke, `(defaults …)`. The rules (the author, 2026-11-08, mtp-m34w.1):

- **A color with no dark value is the same in both modes.** Nothing is inverted for the reader.
- **A color computed from light-dark colors is worked out for each mode on its own:** `mix`, `lighten`, `darken`, a colormap and a move between two colors mix the light values together and the dark values together, so `(mix ink paper 0.5)` is halfway between the two light values on a light page and between the two dark ones on a dark page. A plain color mixed with a light-dark one is mixed into both.
- **Either argument may itself be a light-dark color:** the first gives its light value and the second its dark one, so `(light-dark ink '#ffffff')` is `ink` on a light page and white on a dark one.
- **One value for both is one color:** `(light-dark 'red' '#ff0000')` is `'red'`, and so is a mix whose two modes come out the same.
- **The figure itself never knows the mode;** only its drawing does. So two colors are equal when both of their modes are, a light-dark color shown as text, `$'{c}'` or a readout, reads as its CSS, `light-dark(#1f2a44ff, #e8e4d8ff)`, and its channels, `c.r`, `c.g`, `c.b` and `c.a`, are its light value's.
- **A token keeps its CSS variable:** a light-dark token `ink` is drawn as `var(--mtp-ink, light-dark(#1f2a44ff, #e8e4d8ff))`, so a page that sets `--mtp-ink` still restyles it, in one mode or, with `light-dark()` of its own, in both.

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
| `shuffle` | a list, and optionally `(seed s)` | the same items in an order drawn from a seed | never |
| `pick` | a list, and optionally `(seed s)` | one item, drawn from a seed | the list is empty |
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

### rand

The standard seed: `(import rand)`, and every random value that names no seed follows `rand.seed`, a `rand-seed` starting at 0; `(roll-dice)` rolls it. `(import rand seed)` gives it as `seed`. See "Random values and seeds".

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

## TeX strings

`tex'…'` holds LaTeX as written, for MathJax to typeset: `tex'\Big(1-\frac1b\Big)^2'`. In an ordinary string a backslash starts an escape, so `'\frac'` is an error and `'\neq'` is a line break and `eq`; in a TeX string a backslash means nothing, and `\\` stays two backslashes, LaTeX's line break. The one escape is `\'`, a quote, for primes: `tex'f\'(x)'` is the LaTeX `f'(x)`. A TeX string is a string, and goes wherever one does; no values are filled into it.
