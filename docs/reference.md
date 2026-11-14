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
| `(move target)` | none; written only inside an animation, a slider or a canvas, or in place of the animation of a control or a listener | the target, as for `transition` | the same as `transition` | none |
| `(animation name)` | required, except when written inline as an item of a control or listener | none | `(defaults (duration real) (ease …))`, `(loop)`, `(loop n)` | moves, `at-once` and `in-order` forms, the names of animations and transitions, and uses of choreos |
| `(choreo name params)` | required; declared only at the top level | the parameter list | the same as `animation` | the same as `animation` |

A **transition** is a trajectory from `from` to `to`, along `path`, over `duration`, with `ease`, and the variable or attribute it moves, its target. Two forms make one: `(transition name target …)` declares a named one at the top level, and `(move target …)` writes one in place, with no name, inside an animation, a slider or a canvas. Every argument but the target may be left out, and is then none. A **pure** transition has `none` as its target and keeps only the trajectory. `(like t)` copies the arguments of the transition named `t`, and the form's own arguments win over them, wherever `(like …)` is written. A transition with no `from` starts from the value of what it moves; with no `to`, ends there.

The body of an animation holds moves, `(at-once …)` and `(in-order …)`, and the names of animations and transitions, which stand for what they name: `(move k (to 1) (duration 2))` moves `k`; `(at-once …)` runs what it holds together and `(in-order …)` one after another, and items written in a row run one after another; the name of an animation runs that animation there, and the name of a transition runs that transition. A move whose target is `none` writes nothing, so in an animation it may give only a duration: `(move none (duration 1))` waits a second, and `(wait 1)` is a shorter way to write it (`(wait)` waits the default duration). `(roll-dice s)` is short for `(move s (to (next-seed s)) (duration 0))`, and `(roll-dice)` rolls the file's only seed (see "Random values and seeds"). A `(foreach …)` in the body puts its moves where it is written, once for each item, as it puts declarations: together inside `at-once`, one after another inside `in-order` or in a row, so `(at-once (foreach b bubbles (move b.popped (to false))))` writes every bubble's at once.

A move reads its `from` and `to` at the instant it starts. What that means for moves that start together or one after another, and when two moves of one animation may move the same thing, is in "Concurrency".

An animation, `at-once` and `in-order` take the optional argument `(defaults (duration real) (ease …))`, either part may be left out, so that the moves inside them need not each give their own: a move's own `duration` or `ease` wins, and otherwise the nearest enclosing default applies.

An animation (not `at-once` or `in-order`) also takes `(loop n)`, which plays its body n times in a row, n an int of at least 1 known when compiling, or `(loop)`, which plays it forever; a round must take some time. Each round starts again from the start of the body: a move with no `from` starts from the value of what it moves then, so it carries on from where the last round left it, and one with a `from` jumps back to it. An animation that loops n times lasts n times as long as one round; one that loops forever has no `duration`, and reading it is a compile error.

**Steps.** The items of an animation's body are its steps, and in an animation that loops, the items of one round: a play with `(buttons true)` shows one bar for each, and a stepper one dot (see "Controls"), and their `step` attribute counts them. Several items make one step when they are written in an `(in-order …)`: `(animation (in-order grow (wait 1)) shrink)` has two steps. When the body is a single item, an `(in-order …)`, the name of an animation or a use of a choreo, the steps are that item's own items. A play names its steps with `(labels …)` (see "Controls"). `(step …)` is gone: written in an animation, it is a compile error. These steps are not the transitions `a.steps` lists, which are what each step is made of.

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

**Arguments are known when compiling**: names of shapes, variables and attributes, literals, constants and eases. Each use is written out by the compiler as an ordinary animation, so the compiled file holds no choreo. A parameter given a name stands for what it names: given a shape, `who.opacity` is that shape's opacity; given a variable or an attribute, a move of the parameter moves it, `(move x (to 1))`, and reading the parameter reads its value when the move starts, as reading the variable itself does. A parameter given a value, such as 3, cannot be moved. An argument that needs the live model, such as `(* 2 k)`, is a compile error, as are a wrong number of arguments and an argument of the wrong type. A parameter declared `T` also accepts an argument that may be none, as a function's parameter does: given `(circle|none gone …)`, `(fade-in gone)` is `(move gone.opacity (to 1) (duration 0.4))`, which compiles and plays as written inline, and an argument that may be none is a compile error only where the body uses it in a place that does not accept none, as in `(duration seconds)`.

**A choreo uses only choreos declared before it**, so a choreo that uses itself, directly or through other choreos, is a compile error: `(choreo pulse ((shape a)) (fade-in a) (pulse a))` is refused. A choreo whose parameters all have defaults is compiled once without a use, so the errors in its body show even when nothing uses it.

**Steps.** A choreo's steps are the items of its body, as an animation's are. A use in an animation's body is one step of it, as the name of an animation is, whatever the choreo's body holds. A use written alone in an animation's body, or as the animation of a play or a stepper, gives that animation the choreo's steps.

`a.steps` is the list of transitions an animation plays, in the order it plays them: through `at-once` (in the order written), `in-order` and the animations it names, with each wait as a transition that moves nothing, and for an animation that loops, one round. Its length is known when compiling, so `(foreach t a.steps …)` works, and each step is read like any transition, `a.steps[0].duration`. A transition's `duration` can be read wherever a transition is, such as `(fn ((transition s)) s.duration)`; its `from` and `to` only on a step or a named transition, since their type depends on what it moves. A step does not know when it starts, since that depends on the steps before it: the sum of their durations, in an animation that plays them one after another.

### Components

A view, a control and a readout must have a name: a page places each by its name (see the data model, "On the page"), so one with no name could never be shown, and is a compile error. A listener has no name, and is written inside the body of the view it acts in (see "Listeners and controls in views").

| Form | Name | Positional | Optional arguments | Body |
|---|---|---|---|---|
| `(canvas name)` | required | none | `(toggle-duration t)` and `(toggle-ease e)`, for toggling the shapes its items give, `(x real)` `(y real)` `(width real)` `(height real)`, `(transform transform)`, `(pan bool)`, `(zoom bool)` or `(zoom lo hi)` | bare names of shapes to show (the scene's name shows the whole scene), and expressions that give a shape, none, or a list of them, such as `(when bool name)`, `(when bool [a b])` or `(if bool a b)`, drawn in the order written, each on top of those before it, each shape given by one item at most, and its listeners: on its shapes, `on-show` and `on-hide` included, and its own `on-view`, `on-ready`, `on-live`, `on-quiet` and `on-pointermove` |
| `(readout name value)` | required | the string (a number is shown by interpolating it: `$'{k:.2f}'`) | `(font font)`, a declared font variable, the only way to set its font | its `on-live` and `on-quiet` |
| `(display name formula)` | required | the formula it shows | `(kind k)`, known when compiling: `'block'` (the default) for a formula on its own line, or `'inline'` for one inside a paragraph | its listeners: `on-click`, `on-enter` and `on-leave` on the terms of its formula, and its own `on-live` and `on-quiet` |
| `(slider name move)` | required | a move, or the name of a transition, with a target, `from` and `to`, and no `duration` or `ease` | `(label string)` or `(label (tex string))`, `(step int)` (the number of positions its knob stops at, at least 2), `(active bool)`, `(in view…)`, `(priority n)` | conditions |
| `(button name)` | required | none | `(animation …)`, `(label string)` or `(label (tex string))`, `(selected bool)`, `(active bool)`, `(in view…)`, `(priority n)` | conditions |
| `(play name)` | required | none | `(animation …)`, `(label string)` or `(label (tex string))`, `(buttons bool)`, `(rest seconds)`, `(labels string…)`, one string known when compiling for each step, `(active bool)`, `(in view…)`, `(priority n)` | conditions |
| `(stepper name)` | required | none | `(animation …)` (required), `(label string)` or `(label (tex string))`, `(active bool)`, `(in view…)`, `(priority n)` | conditions |
| `(toggle name target)` | required | the target: a `name`, the bool variable or attribute it writes | `(animation …)`, played after each flip, once the bool is written, `(label string)` or `(label (tex string))`, `(active bool)`, `(in view…)`, `(priority n)` | conditions |
| `(on-drag shape target)` | none | the shape; the target: the shape's own `pos`, `x` or `y`, or `(move target (to expr))`, whose `expr` reads `pointer` | `(active bool)`, `(priority n)` | conditions |
| `(on-click shape)` | none | the shape, or a term of a formula | `(animation …)`, `(active bool)`, `(stop-propagation bool)`, `(priority n)` | conditions |
| `(on-release shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)`, `(priority n)` | conditions |
| `(on-dragstart shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)`, `(priority n)` | conditions |
| `(on-dragend shape)` | none | the shape | `(animation …)`, `(active bool)`, `(stop-propagation bool)`, `(priority n)` | conditions |
| `(on-view)` | none | none: it listens to the canvas whose body holds it | `(animation …)`, `(active bool)`, `(priority n)` | conditions |
| `(on-ready)` | none | none: it listens to the canvas whose body holds it | `(animation …)`, `(active bool)`, `(priority n)` | conditions |
| `(on-live)` | none | none: it listens to the view whose body holds it, a canvas, a readout or a display | `(animation …)`, `(active bool)`, `(priority n)` | conditions |
| `(on-quiet)` | none | none: it listens to the view whose body holds it, which has an `on-live` | `(animation …)`, `(active bool)`, `(priority n)` | conditions |
| `(on-enter shape)` | none | the shape, or a term of a formula | `(animation …)`, `(active bool)`, `(priority n)` | conditions |
| `(on-leave shape)` | none | the shape, or a term of a formula | `(animation …)`, `(active bool)`, `(priority n)` | conditions |
| `(on-show shape)` | none | the shape; written only inside a canvas | `(animation …)`, required, which moves the shape's `drawn` and `opacity` (see "Showing and hiding") | none |
| `(on-hide shape)` | none | the shape; written only inside a canvas | `(animation …)`, required, as for `on-show` | none |
| `(on-pointermove shape target)` or `(on-pointermove target)` | none | the shape, or none for one on the canvas whose body holds it; the target, a `name`, the point it writes | `(active bool)`, `(stop-propagation bool)`, `(priority n)` | conditions |

Wherever a control or a listener takes `(animation …)`, a use of a choreo may stand in its place, among its optional arguments: `(button show (fade-in d1) (label 'Show'))` (see "Transitions and animations"). So may a single `(move …)`, with no change in behavior: `(button b (move k (to 2) (duration 0.4)))` is `(button b (animation (move k (to 2) (duration 0.4))))`. Giving both a move and an animation is a compile error. `(priority n)`, which any control and any listener but `on-show` and `on-hide` takes, gives the writer its priority, an int from 1 to 1000 (see "Concurrency").

A canvas **toggles** the shapes its items give: when an item starts or stops giving a shape, as `(when show d)` does when `show` changes, or `(if show d c)` does by giving one shape for another, the canvas shows or hides that shape. A toggle takes the canvas's `(toggle-duration t)`, in seconds, 0 (at once) if left out, with its `(toggle-ease e)`, `'linear'` if left out, any ease an animation takes: over that time the items' opacity, as the canvas shows them, goes from 0 to 1 or back. A canvas takes no `move`. The canvas never writes the scene: the opacity is its own. "Toggle" is the word for a canvas showing or hiding one of its items. A shape with an `on-show` or an `on-hide` in the canvas is not faded so: those listeners show and hide it (see "Showing and hiding"). A canvas gives a shape from one item at most, so `(when a d1) (when b d1)` is a compile error, written instead as one `when` with one condition, `(when (or a b) d1)`; the same holds for a shape named bare and in a `when`, in a list or in a branch of an `if`.

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

- **A canvas** holds listeners on the shapes it may show (`on-drag`, `on-click`, `on-release`, `on-dragstart`, `on-dragend`, `on-enter`, `on-leave`, `on-show`, `on-hide`, and `on-pointermove` on a shape) and its own: `on-view`, `on-ready`, `on-live`, `on-quiet`, and `on-pointermove` with only a target, which follows the pointer anywhere over the canvas. **A display** holds listeners on the terms of its formula (`on-click`, `on-enter`, `on-leave`) and its own `on-live` and `on-quiet`. **A readout** holds its `on-live` and `on-quiet`.
- **A listener on its own view** names no view: `(on-view (animation …))` plays when a copy of the canvas whose body holds it first comes into view, and `(on-ready (animation …))` when a copy is ready (see "On-view and on-ready" under "Controls").
- **A listener hears the pointer only in its view.** In every other view that shows its shape, the shape does not react to it: no drag, no click, no release, no hover, no pointer moves, no pointer cursor, no wider touch target and no page kept from scrolling, as if the listener were not there, so a click there goes on up the scene tree as it would without it. A shape that reacts in two canvases has its listener written in both, and each is a listener of its own.
- **A foreach or a let** in a view's body may hold listeners, as it holds declarations elsewhere: `(canvas above shape corners (foreach c corners (on-drag c c.pos)))`. It holds nothing but listeners.
- **A control** with `(in …)` belongs to those views; one without it belongs to none. A control belonging only to views that are quiet is put away until one of them goes live (see "Quiet and live views").
- **While a view is quiet**, the listeners inside it hear nothing in it.
- **Errors:** a listener at the top level or with `(in …)`, each with a message that shows how to write it inside its view, and a listener inside a scene. A listener on a shape inside a readout or a display, or on a term inside a canvas or a display of another formula, since that view never shows what it listens to, and one inside a canvas whose items all name shapes, none of which is the listener's shape or holds it. When a canvas has an item that gives a shape by an expression, such as `(when on c)`, the compiler cannot know what it may show, and allows it. An `on-view`, an `on-ready` or an `on-pointermove` inside a readout or a display, and anything but listeners in a foreach or a let of a view's body. For a control: naming something that is not a view, a name not declared before, the same view twice, or no view at all. A view takes no `(in …)`.

#### Showing and hiding

`(on-show shape animation)` and `(on-hide shape animation)` are listeners written inside a canvas's body. The animation is an inline `(animation …)`, a use of a choreo, or a single `(move …)`, which is the same as `(animation (move …))`, as for every listener (see "Components"). A single move moves only one attribute, so it leaves `drawn` or `opacity` unmoved, which is a compile error (see "Hidden" below). `on-show` plays when the canvas starts showing the shape, as when an item's `when` turns true. `on-hide` plays when the canvas stops showing the shape, and the canvas stops drawing it only when the animation ends.

```
(choreo draw-on ((shape who) (real seconds 1))
  (at-once (move who.opacity (to 1) (duration 0)) (move who.drawn (to 1) (duration seconds))))
(choreo fade-out ((shape who) (real seconds 0.4))
  (in-order (move who.opacity (to 0) (duration seconds)) (move who.drawn (to 0) (duration 0))))
(bool show false)
(bool named false)
(scene plane
  (circle orbit (r 3) (stroke ink) (fill none))
  (text name 'orbit' (y -4)))
(canvas view (when show orbit) (when named name)
  (on-show orbit (draw-on orbit 2))
  (on-hide orbit (fade-out orbit))
  (on-show name (animation (at-once (move name.drawn (to 1) (duration 0))
                                    (move name.opacity (to 1) (duration 1))
                                    (move name.y (from -6) (duration 1))))))
(toggle show-orbit show)
(toggle show-name named)
```

When `show` turns true, the canvas draws the orbit on over two seconds, and when it turns false, the orbit fades out. When `named` turns true, the label fades in and rises from a `y` of −6 to its own, −4.

- **A stand-in.** While `on-show` or `on-hide` plays, the canvas draws a stand-in in place of the shape: a copy that only this canvas has, which no other view, no writer and not the scene sees, hears or reads. The animation moves the stand-in. When the animation ends, the canvas draws the original again (after `on-show`) or stops drawing the shape (after `on-hide`), and drops the stand-in. The scene never changes: the original keeps every attribute throughout. Each canvas makes its own stand-ins, and so does each copy of a canvas on the page: every copy plays its own `on-show` and `on-hide`, at the same time, each on its own stand-ins. The pointer passes through a stand-in, as through a shape with `(pointer-events false)`.
- **The shape named is the stand-in.** Inside `on-show` and `on-hide`, `(move orbit.drawn …)`, `(move orbit.opacity …)` and `(move name.y …)` move the stand-in's attributes. Since nothing writes the scene, a move may move an attribute the scene binds, such as an `x` given by an expression. The animation moves nothing else: a move of a variable or of another shape is a compile error.
- **The stand-in follows the original.** Each attribute of the stand-in is the original's, as the scene changes it. An attribute that a move moves, other than `drawn`, is the original's value plus an offset. When the move starts, its `from` and `to` are values of the attribute, and they become an offset from the original's value at that instant; only the offset moves after that. A move with no `to` ends at the original's value, at offset 0, so the canvas draws the original in place of the stand-in without a jump, even when a writer moves the original meanwhile. In the example, if a writer moves `name.y` while the label rises, the stand-in rises toward the new `y` and ends exactly on it. For a color, the stand-in's color is a blend from the move's value to the original's color as it is now, in place of the offset. `drawn` is moved as it is, not as an offset.
- **Hidden** is `drawn` 0 and `opacity` 0. An `on-show` starts from the shape hidden, so its animation must move both `drawn` and `opacity` to 1, and an `on-hide` must move both to 0; one that changes at once takes a move of duration 0, as `draw-on` does with `opacity`. An animation that leaves either unmoved is a compile error naming what is missing.
- **Not at the start.** `on-show` and `on-hide` are not part of the start of a canvas, which is its `on-view`, then state 0, then its `on-ready` (see "On-view and on-ready" under "Controls"). Neither plays before state 0: a shape that state 0 shows is drawn as it is, so it is in the still picture captured when the canvas is ready, and a shape that the `on-view` shows or hides appears or disappears at once. They play only when the canvas starts or stops showing a shape after state 0, as when the `on-ready` or a toggle changes what an item gives. To play one animation both at the first view and at a later show, write it once as a choreo and use it in the `on-view` and in the `on-show`.
- **Setting a state.** When a play or a stepper sets a state, as each of its inputs does before it plays steps, and a press in explore mode does with state 0 (see "States and explore mode"), and while the reader drags a play's bars, the shapes that start or stop being shown appear and disappear at once, with no `on-show` or `on-hide`. Each `on-show` and `on-hide` that is playing then ends at once, even for a shape that stays shown or hidden: its stand-in ends where its animation would end, so the canvas draws the original after an `on-show` and nothing after an `on-hide`. So a state looks the same however it was reached. `on-show` and `on-hide` play only for other changes, such as a press of a button, a flip of a toggle, or a play's steps as they play after the state is set.
- **Turning back midway.** If the canvas starts showing the shape again while `on-hide` plays, or stops while `on-show` plays, the newcomer starts from the stand-in as it is drawn then, half drawn or half faded, and the one playing stops. A move with no `from` starts from there.
- **A shape that stops existing** (its `exists-when` no longer holds) while the canvas shows it plays its `on-hide` on a stand-in that keeps the original's last values, since there is nothing left to follow.
- **Groups.** An `on-show` or `on-hide` for a group passes to every shape in it, and a shape's own wins over its group's: the most specific wins. A move of the group's attribute moves the stand-in of each of its shapes that the group's listener plays for, each from its own value, and the animation must move `drawn` and `opacity` on every shape in the group, through the group or through the shape itself.
- **A shape with no `on-show` or `on-hide`** is shown and hidden as before, with the canvas's `toggle-duration`; a shape that has either is not faded by `toggle-duration`.
- **Errors:** an `on-show` or `on-hide` outside a canvas, two of one kind for one shape in one canvas, one with no animation, one with anything besides its shape and its animation, an animation that leaves `drawn` or `opacity` unmoved on a shape, and an animation that moves anything other than the shape's stand-in.

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
- **Listeners** inside a view hear nothing in it while it is quiet ("Listeners and controls in views"). A copy's `on-view` plays when that copy first comes into view, quiet or not (see "On-view and on-ready"). In view means on screen and shown: while the canvas or an ancestor is fully transparent (opacity 0), hidden or not displayed, as a page may keep its content while it loads, the canvas is not yet in view, and `on-view` waits until it is shown.
- **Pan and zoom:** a quiet canvas neither pans nor zooms, whatever its `pan` and `zoom`: the wheel, a pinch, a drag on empty canvas and a double click do nothing to it, and a finger on it scrolls the page, so a reader scrolling past on a phone is not caught by it. Live, it pans and zooms as its `pan` and `zoom` allow. Going back to quiet drops what the reader panned and zoomed, back to the canvas's own view box.
- **Two views, two modes:** each view has its own mode, so two canvases of one scene may be one quiet and one live.
- **On the page:** a view with a quiet mode has `data-mtp-mode="quiet"` or `data-mtp-mode="live"`, for the page's CSS, and fires `mtp-state` when it changes. The hand, which becomes the cross, is the view's input `switch` (see the data model, "On the page"). A readout, and a display inside a paragraph, take the hand in the line, after their text. The hand and the cross are drawn 2rem across (1.5rem in the line) and take a press 44 pixels across. They are colored as the controls are ("The controls' look").
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

These are the rules for several writers acting on the same values, and for the moves of one animation that run at the same time (the author, 2026-11-13, docs/concurrency-model.md). One rule decides every write.

- **Writers.** The controls and the listeners are the writers. A writer has a trigger and an effect. The effect is an animation, known ahead: a button's press, a play, a stepper, a toggle's flip and its animation, and every listener's animation. Or it is a gesture: an `on-drag`, a slider's knob while the reader holds it, and an `on-pointermove`, which write as the pointer moves. A writer that writes is running, until its effect ends, the reader lets go of it, or it is cancelled. A paused play, and a stepper between two steps, write nothing, so they are not running.
- **Values.** A write is decided on each free value it changes, each on its own. A write of a group's or a motif instance's attribute is a write of each member's, at any depth. A shape's `pos` is its `x` and its `y`. The `x`, `y` and `pos` of a line, a triangle, a polyline, a polygon or a curve are neither free nor bound: a write of one is a write of the ends, corners, points or controls the position is worked out from, each point's `x` for an `x`, its `y` for a `y`, and both for `pos`. A point's `x` and its `y` are two values. So a writer of a polyline's `x` meets a writer of its `points` on each point's `x`, and never meets a writer of its `y`, and a writer of `g.r` meets a writer of `c.r`, for a member `c` of `g`, on `c.r` only.
- **Priority.** Every writer has a priority, an int from 1 to 1000, which it may give with `(priority n)`: `(button b (animation …) (priority 800))`. One that gives none has its kind's: 1000 for `on-view`, 300 for `on-ready`, 700 for a gesture, and 500 for the rest, which the reader triggers.
- **Owners.** Each value has at most one owner: the running writer whose write of it was last accepted. A writer owns a value from its first accepted write, whether or not that write changes the value, until it stops running.
- **The rule.** A write by a writer A of a value that another writer B owns is accepted when A's priority is higher than B's, or the same and A was triggered after B. Otherwise it is rejected. A write of a value no other writer owns is accepted. An accepted write is brought into the value's constraints, and A owns the value; if B owned it, B is cancelled. A writer's own conditions bring each write into them before it is made, as always.
- **Cancelled and rejected.** A cancelled writer stops writing every value, and what it already wrote stays. A rejected write cancels nothing, and its writer writes that value no more for the rest of its effect, while it goes on writing its other values. A writer triggered again, a button pressed again say, starts a new effect, and writes every value again. A writer never cancels itself: a press on a button while its animation runs starts the animation again.
- **For example,** with `(play tour (animation (move k (to 5) (duration 4))))` and `(slider size (move k (from 0) (to 10)))`, moving the knob while `tour` plays cancels `tour`, and `k` follows the knob from then on. While the reader holds the knob, a button pressed to move `k` is rejected on `k`, being of a lower priority, and writes its other values. A canvas's `(on-view (animation (move k (to 0) (duration 1))))` that starts while the reader's `tour` plays is rejected on `k`, and `tour` plays on. One that started before the reader presses `tour` is cancelled by the press. A toggle flipped after a play was pressed was triggered later, so it wins the toggle's bool.
- **A drag** writes from its first move to the release. A grab that moves nothing writes nothing, so it owns nothing, and a play that runs plays on. While the reader holds a shape, an `on-view`, an `on-enter` or an `on-dragstart` that would move it is rejected on the values the drag owns, and writes its other values: the shape keeps following the pointer. The release still plays the drag's `on-dragend`.
- **A slider:** a press on its track or its knob, through the release, is one gesture, of priority 700, triggered by the press. Its first write jumps to the point pressed, and it writes as the pointer moves, until the release, as a drag does. A press that changes nothing writes nothing. An arrow key on a slider is a trigger of the reader's, of priority 500, whose effect is an animation of one move that takes no time.
- **A toggle's flip** is one effect: a move of the bool to `(not target)` that takes no time, then the toggle's animation. So the toggle owns its bool until its animation ends.
- **A play's or a stepper's step** is read from the scene's values (see "States and explore mode"), so it is not decided by this rule. Each of its inputs is a writer like any other. Unless the control gives its own `(priority n)`, a press of a play's button, a tap on a bar, a stepper's dots, "‹" and "›", and the keys are of priority 500, and a drag along a play's bars is a gesture, of priority 700.
- **Copies of a control** are two writers of the same priority: the one moved last wins. Only the copy of a play or stepper moved last writes its `step` and `playing` into the scene.
- **An inactive writer** cannot be triggered, but what it already set off goes on (see the data model, "Writers"): an animation that runs when its writer's `(active bool)` stops holding plays on, until it ends or another writer cancels it.
- **A slider follows its target:** when another writer changes it, the knob moves to match (see "Controls").
- **A canvas showing or hiding a shape** writes nothing in the model (see "Components"), so it cancels no writer, and no writer cancels it.
- **`on-show` and `on-hide`** are writers whose values are the attributes of a canvas's stand-ins (see "Showing and hiding"). What triggers one is a change in what an item gives, not the reader. No other writer writes a stand-in, and they write nothing else, so they never meet another writer on a value: no other writer rejects their writes or cancels them, and they reject and cancel no other writer. They take no `(priority n)`, since they meet only each other. Between them, the rule decides as between two writers of one priority: on a stand-in, the write of the one triggered later is accepted and the other is cancelled, so an `on-show` that starts while the shape's `on-hide` plays cancels it, and the reverse. A group's `on-show` or `on-hide` counts as one writer for each shape that it plays for, so it is cancelled shape by shape (see "Groups" in "Showing and hiding").
- **A move reads its `from` and `to` at the instant it starts**, not when the animation around it was triggered, and they stay fixed while it runs. Moves that start at the same instant, as the moves of an `at-once` do, all read the values as they were before any of them writes: `(at-once (move a (to b)) (move b (to a)))` swaps `a` and `b`. A move that starts after another has ended reads what that one left, and so does each step of an `in-order`, even when its steps take no time: `(in-order (defaults (duration 0)) (move a (to 5)) (move b (to a)))` sets `b` to 5. Each round of a loop starts its moves again, so a round reads what the reader changed during the last one, such as a slider.
- **Two moves of one animation at the same time:** two parts of one `at-once` that move the same variable or attribute at the same time are a compile error, as are a position and its `x` or `y`, and a line's, a triangle's, a polyline's, a polygon's or a curve's `x`, `y` or `pos` and the ends, corners, points or controls that the position is worked out from, and a group's or a motif instance's attribute and the same attribute of one of its members, at any depth (see "Values" above). They would start from the same values and undo each other, so one is written after the other with `in-order`. For a polyline `pl`, `(at-once (move pl.x (to 3)) (move pl.points (to [[0 0] [2 0]])))` is an error, and `(at-once (move pl.x (to 3)) (move pl.y (to 3)))` is not. For a circle `c` in a group `g`, `(at-once (move g.r (to 2)) (move c.r (to 3)))` is an error, and so is `g.x` with the `points` of a polyline in `g`, but `(at-once (move g.translate (to [1 1])) (move c.x (to 3)))` is not, since a container's `translate` and `transform` are not spread. At different times they may, as `(at-once (move k (to 0) (duration 0)) (in-order (wait 2) (move k (to 1))))` does. A loop counts as moving what it moves for as long as it runs.

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

- **Copies:** a page may show any view or control in more than one place, as when a block holding it is pinned beside the text. Each copy has its own page state (see the data model, "On the page"), and only the scene is shared. Two copies of a control are two writers (see "Concurrency").
- **Label:** a control's label is plain text, `(label 'size')`, or LaTeX, `(label (tex $'C_{k}'))`, the form a term of a formula takes. Plain text is shown as written. LaTeX is typeset as a formula is, and a screen reader hears the LaTeX itself. Either may be an expression that reads the model, and the label follows it. A play and a stepper show no label: theirs only names them for a screen reader.
- **Slider:** it shows its move's path as a track, and the reader scrubs along it: its knob runs from 0 to 1, its `position`, and the target lies that far along the path from `from` to `to`. Clicking the track jumps there; dragging the knob gives the speed. So the move must give a target, `from` and `to`, neither of which may be `none`, and may give a `path`, but no `duration` and no `ease`. With `(step n)` the knob stops at n evenly spaced positions.
- **A slider follows its target:** when another writer changes the variable or attribute its move writes, the knob goes to the position whose value is closest to its new value. Its starting position is found the same way.
- **Button:** a press plays its animation from the start, over time; a press while it runs starts it again. A button that also says which state is the current one, as one of a row choosing a value, takes `(selected bool)`: while it holds the button is filled with `--mtp-control-active`, and a screen reader hears it as pressed. `(button #'forbid-{k}' (animation (move w (to (+ k 2)) (duration 0.6))) (selected (= (round w) (+ k 2))))`. A button that only plays an animation takes none. Only a button takes `selected`.
- **Play:** a play is one row, no taller than its round button: the button, then the bars, and with `(buttons true)` the step count after them. The reader acts on the button, the bars and the keys, and each of them is a listener (see "States and explore mode"). The button has Tabler's icons: a play icon, a pause icon while the play runs, and a replay icon, a circular arrow, at the last step. A press while the play runs pauses it, and a press while it is paused partway through a step resumes it. Otherwise, at step k, a press sets state k and plays the steps after it, and at the last step it sets state 0 and plays every step again. The play's `label` is the button's name for a screen reader, and the button shows no text. Its `step` attribute is its step, from 1 to the number of steps, whether or not the bar is split, and 0 in explore mode, and `playing` holds while it runs. Each is read in an expression as any attribute is, as `tour.step`. A play has no `time`: reading `tour.time` is a compile error.
- **A play's bars:** the bars show how far the animation has played. With `(buttons true)` there is one bar per step of the animation (see "Transitions and animations", "Steps"), each as wide as its step's duration, filling while its step plays, and the step count after them, as `2 / 4`, with the step's label when the play has `(labels …)`, which reads `– / 4` in explore mode. Without it, the default, there is one bar for the whole animation and no count. A knob like the slider's sits where the fill ends. In explore mode the bars are dimmed, the knob is an empty ring at the left end, and a filled pill reading "Exploring" sits on the middle of the bars. Nothing is drawn under the bars. A tap on step i's bar sets state i - 1 and plays steps i to the last, and a tap on the one bar of a play without `(buttons true)` sets state 0 and plays every step. A press on the bars pauses a play that runs: a tap then plays from the start of the step tapped, and a drag leaves the play paused where the drag ends. A drag along the bars is a gesture: at each point it sets state i - 1, for the step i under the pointer, then each move of step i at its value at that point. Then a press on the button resumes from there. For an animation that loops, the bar shows one round.
- **A play's labels:** `(labels 'Grow' 'Shrink')` names the steps of a play, one string known when compiling for each step. A count of labels other than the count of steps is a compile error, and only a play takes `labels`. With `(buttons true)` the name of the step sits after the bars, next to the count, as `2 / 4 · A third of a turn`, and in explore mode the count reads `– / 4` with no name (the author, 2026-11-13). The room after the bars is as wide as the longest name with its count in every state, so the row never changes length. A screen reader hears the same text in the value of the bars, as `1 / 2 · Grow`. Without `(buttons true)` there is no count, and no name is shown.
- **A play's rest:** `(rest t)`, `t` a number of seconds known when compiling, pauses the play `t` seconds between each pair of steps that follow each other, not before the first or after the last, so the illustrator need not end each step with a `(wait t)`. In an animation that loops, it rests between the steps of each round. While it rests, the step just played keeps its bar full and the next one's waits empty, and the play's `step` stays the step just played. A step's bar is as wide as the step alone, the rest not counted, and the bar is scrubbed over the steps only: a tap on a step's bar plays the step from its own start, after the rest before it. Only a play takes a rest.
- **A play's keys:** the play button and the bars each take the keyboard's focus, and show it with a ring. With any part of the play focused, Space is the button. With `(buttons true)`, at step k the right arrow is a tap on bar k + 1, and the left arrow a tap on bar k, which plays step k again. A left arrow pressed less than 300 milliseconds after step k started playing is a tap on bar k - 1 instead, as a music player's back button goes to the previous track when pressed just after a track starts, so quick presses go back one step each. Step k started playing at the press that started it, or, for a play running on from an earlier step, in the frame in which the play reached step k. At step 1 a quick left arrow plays step 1 again (the author, 2026-11-13). The right arrow does nothing at the last step, and the left arrow nothing at step 0. Without `(buttons true)` there are no arrow keys. On a page with only one play or stepper, the keys work from anywhere on the page, so a presenter can drive it without first clicking it, except while what has focus takes keys of its own: a text field, a button, a slider, a toggle.
- **Stepper:** `(stepper name (animation …))` is a play with no clock: the reader moves through the animation's steps one at a time. Its steps are a play's (see "Transitions and animations", "Steps"). It is a round "‹" button, a dot for each step, a round "›" button, drawn as a play's button with Tabler's chevrons, and a count after them, the step and the number of steps, as `2 / 3`, or `– / 3` in explore mode. Each of its inputs is a listener whose effect sets a state and plays a step (see "States and explore mode"). A tap on step i's dot sets state i - 1, plays step i over time, and stops at its end. At step k, "›" is the dot of step k + 1, and "‹" the dot of step k, so it plays step k again. "‹" pressed less than 300 milliseconds after step k started playing is the dot of step k - 1 instead, as a play's left arrow is, and at step 1 it plays step 1 again (the author, 2026-11-13). "›" while a step plays sets the state at that step's end and plays the next, so each press moves on by one step. "›" is turned off at the last step, and "‹" at step 0. The dots of the steps passed are solid, the current one's is solid with a ring, and those still to come are pale. In explore mode the dots are dimmed, none is current, and a pill reading "Exploring" sits on them, as on a play's bars. The dots are never narrower than the pill: when there are few, they are spread to its width, so the stepper has the same width in every state (the author, 2026-11-13). Its `step` attribute is its step, from 1 to the number of steps, and 0 in explore mode, as a play's, and `playing` holds while a step plays. A stepper takes no `(buttons …)`, `(rest …)` or `(labels …)`: it stops after each step, and the reader moves it. For a screen reader, the buttons are "previous step" and "next step", and the dots are a group named by the label and the step, as `hints: step 2 of 3`, or `hints: 3 steps` in explore mode, with the current step's dot marked as the current step.
- **A stepper's keys:** with any part of it focused, the right arrow is "›" and the left arrow is "‹", and each does nothing where its button is turned off. Each part takes the keyboard's focus and shows it with a ring. On a page with only one play or stepper, the keys work from anywhere on the page, except while what has focus takes keys of its own, as a play's do.
- **Autoplay is gone:** `(autoplay)` on a play or a stepper is a compile error, whose message names `on-ready`. A canvas's `(on-ready (animation …))` plays when a copy of the canvas is ready (see "On-view and on-ready").
- **Toggle:** a checkbox writing its target, a bool variable or attribute: `(bool grid-shown true) (toggle grid grid-shown)`. A toggle holds no bool of its own, so its target is never `none`, `(toggle t none)` is a compile error, and the bool's start is given where the bool is declared. A flip is a writer the reader sets off, decided like any other. Its effect is a move of the bool to `(not target)` that takes no time, then the toggle's animation: one effect, so the toggle owns its bool until its animation ends (see "Concurrency"). On a group's attribute it writes every member, reads true only when every member's is true, and shows a mixed state when the members differ. A click on a mixed toggle sets every member to true. A toggle's value, `grid.value`, reads its target, like any other attribute.
- **On-click:** a click on the shape plays its animation, as a button does. As JavaScript's `click`, a press and a release make a click on the nearest shape that is or holds both the shape pressed and the one released over, whatever the pointer did between (a drag or a pan too).
- **On-release:** like JavaScript's `pointerup`, the pointer released over the shape plays its animation, wherever the press began.
- **On-dragstart:** like JavaScript's `dragstart`, a drag of the shape that starts plays its animation. A drag starts at the first move of the pointer after the press, so a press and release with no move between starts none, and hovering starts none. The shape is the one whose `on-drag` the drag follows. The animation starts before the drag's first write, so a drag may first reset what it then reads, as `(on-dragstart p (animation (move o (to 0) (duration 0))))` with `(on-drag p (move y (to (+ pointer.y o))))`.
- **On-dragend:** like JavaScript's `dragend`, a drag of the shape that ends plays its animation. A drag starts only once the pointer moves, so a press and release with no move between ends none. The shape is the one whose `on-drag` the drag follows.
- **Order:** a release sets off, in this order, the `on-release` of the shape under the pointer, the `on-dragend` of the shape dragged, and the `on-click`: JavaScript sends `pointerup` before `click`, and `on-dragend` comes between them. The move that starts a drag sets off, in this order, the `on-enter`, `on-leave` and `on-pointermove` it causes, the `on-dragstart` of the shape dragged, and then the drag's first write: JavaScript sends `pointermove` before `dragstart`.
- **Bubbling:** as in the DOM, a click, a release, the start and the end of a drag and a pointer move go up the scene tree from the shape they happen on, and set off every listener of their kind on that shape and on each container holding it whose `(active bool)` holds, innermost first; a pointer move then reaches the canvas's `on-pointermove`. A listener with `(stop-propagation bool)`, while the bool holds, stops the event at its shape, as JavaScript's `stopPropagation()`: the other listeners on that shape still run, and none further up. `on-enter` and `on-leave` take no `stop-propagation`, since JavaScript's `pointerenter` and `pointerleave` do not bubble, and neither does `on-drag`, since a press drags one shape only.
- **On-view and on-ready:** a canvas has a lifecycle, the same in every copy of it on the page (the author, 2026-11-13, docs/canvas-lifecycle.md). The page is static: no view or control is added to it or removed from it after it loads.
  - **On-view:** a copy's `on-view` plays its animation, at priority 1000, when that copy first comes into view, and only if the values its `on-view` moves still have their values at page load. It never plays again in that copy. So a copy that comes into view after another copy's `on-view` has moved those values plays none of its own. Nothing the reader does cuts an `on-view` short, since no writer gives itself a priority above 1000.
  - **State 0 of a canvas** is the values once its `on-view`s have played from the values at page load. It is not a play's state 0 (see "States and explore mode").
  - **Ready:** a canvas is ready, in every copy at once, from the first moment the `on-view` of one of its copies has ended, or from page load when it has no `on-view`. It stays ready from then on. Ready is a moment, not a comparison of values: nothing the reader or any writer does later changes it. A copy whose `on-view` is not triggered, because its values had already changed, is ready because its canvas is.
  - **Inputs wait for ready:** until a canvas is ready, every input that belongs to it is disabled, drawn disabled and taking no input, and it is enabled once the canvas is ready. An input belongs to a canvas when it is a listener inside the canvas's body, the canvas's hand, or a control that writes a value that some shape the canvas shows depends on. The compiler works out which canvases each control belongs to. A control waits only for the canvases that have a copy on the page.
  - **On-ready:** a canvas's `on-ready` plays its animation once, at priority 300, when the canvas becomes ready. A canvas with no `on-view` is ready from the start, and its `on-ready` plays when the page loads, seen or not. An `on-ready` may play any animation, one that loops forever included, and it is an ordinary writer: its `to` expressions may depend on the values its moves write.
  - **The page is ready** once every canvas, display and readout on it is ready. Controls do not count. A display and a readout have no `on-view`, so they are ready from the start. A page that captures still images captures each canvas at the moment it becomes ready: mtp itself captures none.
  - **Compile errors:** an `on-view` that loops forever (a `(loop n)` with a count is allowed), and a move in an `on-view` whose `to` expression depends on the value its move writes.
  - **On the page**, each copy has `data-mtp-seen` once it has come into view and `data-mtp-ready` once its canvas is ready, and `<mtp-model>` has `data-mtp-ready` once the page is ready (see the data model, "On the page").
  - **Not decided:** when a copy comes into view and its `on-view` is not triggered, while no `on-view` of its canvas has played in any copy, the runtime makes the canvas ready then.
- **On-live and on-quiet:** when the reader makes the view live, every `on-live` of it plays its animation, as a button does, and when the reader puts it back to quiet every `on-quiet` of it does (see "Quiet and live views").
- **On-enter and on-leave:** like JavaScript's `pointerenter` and `pointerleave`, the pointer coming onto the shape plays the `on-enter`'s animation, and the pointer going off it, or off the canvas, plays the `on-leave`'s. As in JavaScript, the pointer is over every shape up the scene tree from the one under it: a group is entered from any of its members, and left only when the pointer is off all of them. Each shape plays its own listener, the first of its kind whose `(active bool)` holds; when the pointer moves from one shape to another, the leaves come first, the innermost first, and then the enters, the outermost first.
- **On-pointermove:** like JavaScript's `pointermove`, while the pointer is over the shape, or anywhere over the canvas, each move writes the pointer's position to the target, a point variable or attribute, in the scene's coordinates. When the target is a shape's own `pos`, it is written in the frame the shape's `x` and `y` live in, so the shape sits under the pointer, and a condition may limit either, as `(on-pointermove lens.pos (<= lens.x 5))` inside the canvas. A group, a fixed-size one too, follows the pointer by its `translate`, written in the frame of the group's container; a group's `pos` is a compile error, since writing it would put every member at the pointer, and so is a target inside a fixed-size group.
- **Touch screens:** a finger has no hover, so a tap stands for it. A tap on a shape enters it, playing its `on-enter` and its containers', and it stays entered after the finger lifts; it is left, playing its `on-leave`, only when the reader taps or presses somewhere else: another shape, which is then entered, empty canvas, or anywhere else on the page. While a finger is down and moving, the figure follows it: shapes are entered and left as it passes over them, and `on-pointermove` writes where it is. Lifting the finger keeps the last shape entered and the last position written. When the browser takes the finger away from the figure, to scroll or zoom the page, what the press and the moves did stays: the shapes entered stay entered and the last position written stays, but the release does nothing, so no `on-release`, `on-click` or `on-dragend` plays, a drag stops where it is, and a selection for the tap alternative to a drag ends. `on-pointermove` writes only while a finger is down, and a tap writes where it was. A pen that does not hover counts as a finger; the mouse, and a pen that hovers, work as described above.
- **Touch targets:** a finger press that lands on no shape the reader can act on (one with an `on-drag`, `on-click`, `on-release`, `on-enter`, `on-leave` or `on-pointermove`, its own or a container's) but within 22 pixels of one counts as a press on the nearest, measured to the box around what is drawn. So every such shape takes a finger over an area at least 44 pixels across. The mouse stays exact.
- **Page scrolling:** a finger on a shape the reader can act on, or within 22 pixels of one, does not scroll the page; elsewhere on the canvas it does. A canvas that pans or zooms, or that an `on-pointermove` of its own listens to, keeps the page from scrolling anywhere on it; a quiet canvas does not pan or zoom (see "Quiet and live views").
- **Guidance:** these touch rules follow WCAG 2.2 (success criteria 2.5.7, Dragging Movements, and 1.4.13, Content on Hover or Focus), the WARP design system's guidance for interaction with data graphics, Microsoft's touch guidance, and the UW Interactive Data Lab's study of interaction with data graphics on phones (EuroVis 2024).

### States and explore mode

The author, 2026-11-13. These terms are used wherever this reference speaks of plays and steppers. A canvas's state 0 is another thing (see "On-view and on-ready" under "Controls").

- **States.** A play or a stepper whose animation has N steps has the states 0 to N. **State 0** is the values as they are, except those that a move of step 1 gives with `(from …)`, which are at that `from`. **State k**, for k from 1 to N, fixes only the values that steps 1 to k move: each is at the last `to` written for it in steps 1 to k, that `to` read at the time the state is set or checked, and brought into the control's conditions and the value's constraints, as a write of it would be. A move with no `to` fixes nothing.
- **The step is read from the scene.** The `step` of a play or a stepper is the highest k from 1 to N whose state the scene is in. Which writer wrote the values does not matter: a button that writes the values of state 2 puts the play at step 2. When the scene is in none of the states 1 to N, the step is 0, and the control is in **explore mode**. While step k plays, or the play is paused partway through step k, the step is k.
- **Matching.** A real matches when it is within about a millionth of its size, a point or a list when each of its numbers matches, and a bool, a string, a choice or a color only when it is exactly the same.
- **A compile error:** a move in a play or a stepper whose `to` expression depends on the value its move writes, directly or through bound variables, as `(play p (move k (to (+ k 1)) (duration 1)))`, since the step could not be read from the scene. A button's move may read what it moves.
- **Explore mode** has no step: `step` is 0 and `playing` is false. A play's bars and a stepper's dots are dimmed, a play's knob is an empty ring at the left end, a pill reading "Exploring" sits on a play's bars and on a stepper's dots, and the count reads `– / N` (see "Controls"). The element has `data-mtp-exploring` (see the data model, "On the page").
- **Every input is a listener** whose effect is: set state j, then play steps j + 1 to m. Setting the state is part of the effect, so its writes are decided as any writer's are (see "Concurrency"). At step k:

  | Input | Effect |
  |---|---|
  | a play's button, while the play runs | pause it |
  | a play's button, while the play is paused partway through a step | resume it |
  | a play's button, k below N | set state k, then play steps k + 1 to N |
  | a play's button, k equal to N | set state 0, then play steps 1 to N |
  | a tap on a play's bar i | set state i - 1, then play steps i to N |
  | a tap on the one bar of a play without `(buttons true)`, named `bar-1` | set state 0, then play steps 1 to N |
  | a drag along a play's bars, a gesture | at each point, set state i - 1 for the step i under the pointer, then each move of step i at its value at that point. On the release the play is paused there, and its button resumes it |
  | Space, on a play | the play's button |
  | the right arrow, on a play with `(buttons true)` | a tap on bar k + 1 |
  | the left arrow, on a play with `(buttons true)` | a tap on bar k, which plays step k again, or, less than 300 milliseconds after step k started playing and with k above 1, a tap on bar k - 1 |
  | a stepper's dot i | set state i - 1, then play step i, and stop at its end |
  | a stepper's "›", or the right arrow | dot k + 1 |
  | a stepper's "‹", or the left arrow | dot k, which plays step k again, or, less than 300 milliseconds after step k started playing and with k above 1, dot k - 1 |

- **An input whose effect names a step that does not exist does nothing:** "›" and a play's right arrow at step N, and "‹" and a play's left arrow at step 0. A stepper's "›" and "‹" are turned off then.
- **A pause:** a paused play writes nothing, so it owns nothing (see "Concurrency"). Its pause ends at another writer's accepted write of a value the play moves: its step is then read from the scene again, and its button plays from that step. Which writes end a pause is not decided yet: for now the runtime ends it on any such write.

### The controls' look

The controls are drawn with BRAIID, the design system of RSM documents, and read its CSS tokens, so a page that shows controls loads `braiid.css`; their accent is BRAIID's `--primary-700` (`--primary-600` for a toggle's box). A control has two states: at rest, and in use, while the reader presses it, drags it, or has given it the keyboard's focus, and for a play, while it plays. A page may give each state its own color with two CSS custom properties, set anywhere above the controls, such as on `:root`:

| Property | What it colors | When the page sets none |
|---|---|---|
| `--mtp-control-rest` | a control at rest: a button's text, a slider's knob and the track up to it, a toggle's box, a play's filled bars, a stepper's dots | `--primary-700` (`--primary-600` for a toggle) |
| `--mtp-control-active` | the same, while in use; and a play's and a stepper's round buttons, always, since they are what the reader presses first and a gray there would look turned off | the same as the rest color |

The hand and the cross of a view with a quiet mode take the same two colors: the rest color, and the in-use color under the pointer, while pressed and while focused. So a page that sets neither looks as BRAIID draws it. A page that wants its controls gray at rest and ink while used sets, for example, `--mtp-control-rest: #8a8f98; --mtp-control-active: #1f2a44`. The track a play's bars lie on is the page's text color, faint, in both states.

### Recording mode

For recording a vertical short while a play runs, the page `mtp build` writes, and the dev page, show a figure alone when their address ends in `?record`: `build_golden-tour/index.html?record`. The page then holds only a 9:16 frame, as large as fits the window, on a slightly darker ground so its edges can be found when cropping. In the frame are the figure's first canvas and, under it, its first play's bars and, with `(buttons true)`, its step count, without the play button, since a viewer cannot press it, and without the canvas's hand when it has a quiet mode. The play shows whether the canvas is quiet or not. Nothing else of the page shows, and the pointer is hidden over the whole window. `&canvas=name` and `&play=name` choose another canvas or play: `?record&canvas=view&play=tour`. The play is driven with its keys (see "A play's keys"), which work from anywhere, since the page holds one play. The frame is sized in CSS pixels to fit the window, not drawn at a fixed 1080 by 1920 and scaled down: a canvas draws its strokes and text in screen pixels, so it looks in the frame as it does on a phone of that width. The screen's pixel density, or the browser's zoom, sets how sharp the recording is.

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
