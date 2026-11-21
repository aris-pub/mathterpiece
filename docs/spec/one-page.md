# mtp in one page

This page lists the main words of mtp, with their meanings, diagrams and one example. It holds no
rules: each word links to the page that defines it.

## What mtp is

mtp is a language for interactive mathematical illustrations. A source describes shapes, formulas
and the variables that they depend on. A reader changes the variables with sliders, buttons,
drags and clicks, and everything that depends on them follows.

## People

| Person | What they do |
|---|---|
| {term}`illustrator` | writes a {term}`world model` as an `.mtp` source file |
| {term}`author` | writes a web page and places components of the world model in it |
| {term}`reader` | opens the page and acts on the components |

One person may be both the illustrator and the author.

## Programs and files

The {term}`compiler` turns an `.mtp` source into a `.mtpc` file, on the illustrator's machine. The
{term}`runtime`, `mathterpiece.js`, runs in the reader's browser. It reads the `.mtpc` and keeps
one {term}`live model` for it, and it draws the components that the page places
({doc}`compiler-runtime`).

<figure class="mtp-diagram">
<svg viewBox="0 0 480 480" role="img" aria-labelledby="mtp-d-title"><title id="mtp-d-title">The illustrator writes the .mtp, which the compiler compiles into the .mtpc. The author writes the page. The .mtpc, the runtime script and the page make the open page in the reader’s browser, where the runtime holds one live model for each .mtpc and serves the components, which the reader sees and acts on.</title><defs><marker id="mtp-d-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="mtp-d-headpath" d="M0 0 L10 5 L0 10 z"/></marker></defs><rect class="mtp-d-person" x="15.0" y="16" width="140" height="36" rx="18.0"/><text class="mtp-d-name" x="85.0" y="39.0" text-anchor="middle">illustrator</text><rect class="mtp-d-person" x="325.0" y="16" width="140" height="36" rx="18.0"/><text class="mtp-d-name" x="395.0" y="39.0" text-anchor="middle">author</text><line class="mtp-d-arrow" x1="85" y1="52" x2="85" y2="94" marker-end="url(#mtp-d-head)"/><text class="mtp-d-label" x="93" y="78" text-anchor="start">writes</text><line class="mtp-d-arrow" x1="395" y1="52" x2="395" y2="94" marker-end="url(#mtp-d-head)"/><text class="mtp-d-label" x="403" y="78" text-anchor="start">writes</text><rect class="mtp-d-file" x="15.0" y="96" width="140" height="36" rx="6"/><text class="mtp-d-code" x="85.0" y="119.0" text-anchor="middle">.mtp</text><rect class="mtp-d-file" x="325.0" y="96" width="140" height="36" rx="6"/><text class="mtp-d-name" x="395.0" y="119.0" text-anchor="middle">page</text><line class="mtp-d-arrow" x1="85" y1="132" x2="85" y2="178" marker-end="url(#mtp-d-head)"/><text class="mtp-d-label" x="93" y="152" text-anchor="start">the compiler</text><text class="mtp-d-label" x="93" y="166" text-anchor="start">compiles it</text><rect class="mtp-d-file" x="15.0" y="180" width="140" height="48" rx="6"/><text class="mtp-d-code" x="85.0" y="209.0" text-anchor="middle">.mtpc</text><rect class="mtp-d-file" x="175.0" y="180" width="140" height="48" rx="6"/><text class="mtp-d-name" x="245.0" y="200.5" text-anchor="middle">runtime script</text><text class="mtp-d-code" x="245.0" y="217.5" text-anchor="middle">mathterpiece.js</text><line class="mtp-d-arrow" x1="85" y1="228" x2="85" y2="268" marker-end="url(#mtp-d-head)"/><line class="mtp-d-arrow" x1="245" y1="228" x2="245" y2="268" marker-end="url(#mtp-d-head)"/><line class="mtp-d-arrow" x1="395" y1="132" x2="395" y2="268" marker-end="url(#mtp-d-head)"/><rect class="mtp-d-live" x="15" y="270" width="450" height="112" rx="10"/><text class="mtp-d-livename" x="31" y="292">open page, in the reader’s browser</text><rect class="mtp-d-part" x="35" y="306" width="190" height="58" rx="6"/><text class="mtp-d-name" x="130.0" y="331.5" text-anchor="middle">runtime</text><text class="mtp-d-sub" x="130.0" y="348.5" text-anchor="middle">one live model for each .mtpc</text><rect class="mtp-d-part" x="255" y="306" width="190" height="58" rx="6"/><text class="mtp-d-name" x="350.0" y="331.5" text-anchor="middle">components</text><text class="mtp-d-sub" x="350.0" y="348.5" text-anchor="middle">views, controls, listeners</text><line class="mtp-d-arrow" x1="225" y1="335" x2="253" y2="335" marker-end="url(#mtp-d-head)"/><line class="mtp-d-arrow" x1="350" y1="364" x2="350" y2="428" marker-start="url(#mtp-d-head)" marker-end="url(#mtp-d-head)"/><text class="mtp-d-label" x="358" y="402" text-anchor="start">sees, acts on</text><rect class="mtp-d-person" x="280.0" y="430" width="140" height="36" rx="18.0"/><text class="mtp-d-name" x="350.0" y="453.0" text-anchor="middle">reader</text></svg>
</figure>

## An example

```{mtp-example}
; a point on a segment, and a slider and a drag that move it
(scene s
  (real a 1 (>= 0) (<= 4))
  (line track (from [0 0]) (to [4 0]) (stroke #'gray'))
  (circle p (pos [a 0]) (r 0.15) (fill #'crimson')))

(canvas v (x -0.5) (y -0.5) (width 5) (height 1) s
  (on-drag p (move a (to pointer.x))))
(slider push (move a (from 0) (to 4)) (label 'a'))
(readout r f'a = {a:.2f}')
```

- `a` is a free variable: it holds 1 when the page opens, and a writer may change it.
- The circle `p` is a shape. Its `pos` is bound to `[a 0]`, so the circle moves whenever `a`
  changes.
- The canvas `v` is a view: it draws the scene `s`. The slider `push` is a control, and
  `on-drag` is a listener. Both write `a` with a movement, `(move a …)`.
- The readout `r` is a view that shows `a` as text.

## Expressions

A source is a list of expressions. Before anything else, every piece of syntactic sugar is
rewritten into its full form, for example:

| Written | Means |
|---|---|
| `[0 1]` | `(list-of 0 1)` |
| `p.pos.x` | `(. (. p pos) x)` |
| `real\|none` | `(type-union real none)` |
| `list[int]` | `(type-apply list int)` |
| `r@1` | `(r 1)` |
| `@'dot-{k}'` | `(name f'dot-{k}')` |

After that, each expression is a {term}`literal`, a {term}`name` or a {term}`form`. A form is
written in parentheses, and its first item is its {term}`head`. The head decides whether the form
is a {term}`compound`, a declaration or a {term}`clause` ({doc}`grammar`, {doc}`heads`).

<figure class="mtp-diagram" style="max-width: 35rem">
<svg viewBox="0 0 560 386" role="img" aria-labelledby="mtp-items-title"><title id="mtp-items-title">Five kinds of expression that the parser produces, one under the other: literals, names, compounds, declarations and clauses. All five are expressions. Compounds, declarations and clauses are forms. A literal gives a primitive, a name gives what it refers to, a compound gives a value or a type, a declaration creates a variable, a type or an object, and a clause gives nothing and is part of the form around it.</title><text class="mtp-d-label" x="305.0" y="18" text-anchor="middle">what the parser produces</text><rect class="mtp-d-file" x="120" y="30" width="370" height="62" rx="6"/><text class="mtp-d-name" x="134" y="55" text-anchor="start">literals</text><text class="mtp-d-code" x="134" y="76" text-anchor="start">3  'hi'  #'red'  true</text><text class="mtp-d-sub" x="478" y="65.0" text-anchor="end">gives a primitive</text><rect class="mtp-d-file" x="120" y="102" width="370" height="62" rx="6"/><text class="mtp-d-name" x="134" y="127" text-anchor="start">names</text><text class="mtp-d-code" x="134" y="148" text-anchor="start">a  real  circle</text><text class="mtp-d-sub" x="478" y="129.0" text-anchor="end">gives what it</text><text class="mtp-d-sub" x="478" y="145.0" text-anchor="end">refers to</text><rect class="mtp-d-file" x="120" y="174" width="370" height="62" rx="6"/><text class="mtp-d-name" x="134" y="199" text-anchor="start">compounds</text><text class="mtp-d-code" x="134" y="220" text-anchor="start">(+ 1 2)  (list-of 1 2)</text><text class="mtp-d-sub" x="478" y="201.0" text-anchor="end">gives a value</text><text class="mtp-d-sub" x="478" y="217.0" text-anchor="end">or a type</text><rect class="mtp-d-file" x="120" y="246" width="370" height="62" rx="6"/><text class="mtp-d-name" x="134" y="271" text-anchor="start">declarations</text><text class="mtp-d-code" x="134" y="292" text-anchor="start">(real a 1)  (circle c …)</text><text class="mtp-d-sub" x="478" y="273.0" text-anchor="end">creates a variable,</text><text class="mtp-d-sub" x="478" y="289.0" text-anchor="end">a type or an object</text><rect class="mtp-d-file" x="120" y="318" width="370" height="62" rx="6"/><text class="mtp-d-name" x="134" y="343" text-anchor="start">clauses</text><text class="mtp-d-code" x="134" y="364" text-anchor="start">(r 1)  (else 0)</text><text class="mtp-d-sub" x="478" y="337.0" text-anchor="end">gives nothing, and is</text><text class="mtp-d-sub" x="478" y="353.0" text-anchor="end">part of the form</text><text class="mtp-d-sub" x="478" y="369.0" text-anchor="end">around it</text><path class="mtp-d-arrow" fill="none" d="M114 34 H104 V376 H114"/><text class="mtp-d-label" x="98" y="209" text-anchor="end">expressions</text><path class="mtp-d-arrow" fill="none" d="M496 178 H506 V376 H496"/><text class="mtp-d-label" x="512" y="281.0" text-anchor="start">forms</text></svg>
</figure>

## Values, containers and types

A {term}`value` is a {term}`primitive` or an {term}`object`. A primitive, such as `3`, `'hi'` or
`[0 1]`, never changes and has no identity. An object, such as a circle, has an identity and
attributes.

A {term}`container` is a variable or an attribute, and holds one value. Each container is one of
these:

| Kind | Example | What it holds |
|---|---|---|
| free | `(real a 1)` | 1 when the page opens, until a writer writes a new value |
| bound | `(real b (* 2 a))` | the value of its expression at all times, so `b` follows `a` |
| const | `(real c 3 (const))` | 3, always. A writer of `c` is a compile error |

A {term}`type` is a set of values, known when compiling, such as `real`, `(real (>= 0))`,
`circle` or `real|none` ({doc}`types`).

<figure class="mtp-diagram" style="max-width: 37rem">
<svg viewBox="0 0 590 508" role="img" aria-labelledby="mtp-dm-title"><title id="mtp-dm-title">Three columns: text in the source, values in the compiler or runtime, and containers in the compiler or runtime. Literals and some compounds give primitives. Declarations and other compounds give objects. Type declarations and names of types give types, which are held in the compiler only. A primitive never changes and has no identity. An object has an identity and attributes, each a container. A type is a set of values, known when compiling. A container is a variable or an attribute, holds one value, and is free, bound or const.</title><defs><marker id="mtp-dm-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="mtp-d-headpath" d="M0 0 L10 5 L0 10 z"/></marker></defs><text class="mtp-d-label" x="105" y="16" text-anchor="middle">text in the source</text><text class="mtp-d-label" x="315" y="16" text-anchor="middle">values in the</text><text class="mtp-d-label" x="315" y="30" text-anchor="middle">compiler or runtime</text><text class="mtp-d-label" x="500" y="16" text-anchor="middle">containers in the</text><text class="mtp-d-label" x="500" y="30" text-anchor="middle">compiler or runtime</text><g transform="translate(0,16)"><rect class="mtp-d-file" x="15" y="34" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="58" text-anchor="middle">literals</text><text class="mtp-d-code" x="105" y="80" text-anchor="middle">3  'hi'  #'red'</text><line class="mtp-d-arrow" x1="195" y1="69" x2="243" y2="69" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="118" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="142" text-anchor="middle">compounds</text><text class="mtp-d-code" x="105" y="164" text-anchor="middle">(+ 1 2)  [1 2]</text><line class="mtp-d-arrow" x1="195" y1="153" x2="243" y2="153" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="222" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="246" text-anchor="middle">declarations</text><text class="mtp-d-code" x="105" y="268" text-anchor="middle">(circle c …)</text><text class="mtp-d-code" x="105" y="284" text-anchor="middle">(func f …)</text><line class="mtp-d-arrow" x1="195" y1="257" x2="243" y2="257" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="306" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="330" text-anchor="middle">compounds</text><text class="mtp-d-code" x="105" y="352" text-anchor="middle">(if f a b)</text><text class="mtp-d-code" x="105" y="368" text-anchor="middle">(fn …)  (rec …)</text><line class="mtp-d-arrow" x1="195" y1="341" x2="243" y2="341" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-file" x="15" y="410" width="180" height="70" rx="6"/><text class="mtp-d-name" x="105" y="434" text-anchor="middle">types</text><text class="mtp-d-code" x="105" y="456" text-anchor="middle">(type t …)</text><text class="mtp-d-code" x="105" y="472" text-anchor="middle">real|none</text><line class="mtp-d-arrow" x1="195" y1="445" x2="243" y2="445" marker-end="url(#mtp-dm-head)"/><rect class="mtp-d-part" x="245" y="34" width="140" height="154" rx="6"/><text class="mtp-d-name" x="315" y="96" text-anchor="middle">primitive</text><text class="mtp-d-sub" x="315" y="118" text-anchor="middle">never changes,</text><text class="mtp-d-sub" x="315" y="134" text-anchor="middle">has no identity</text><rect class="mtp-d-part" x="245" y="222" width="140" height="154" rx="6"/><text class="mtp-d-name" x="315" y="276" text-anchor="middle">object</text><text class="mtp-d-sub" x="315" y="298" text-anchor="middle">has an identity</text><text class="mtp-d-sub" x="315" y="314" text-anchor="middle">and attributes,</text><text class="mtp-d-sub" x="315" y="330" text-anchor="middle">each a container</text><text class="mtp-d-label" x="315" y="402" text-anchor="middle">types in the compiler</text><rect class="mtp-d-part" x="245" y="410" width="140" height="70" rx="6"/><text class="mtp-d-name" x="315" y="434" text-anchor="middle">type</text><text class="mtp-d-sub" x="315" y="454" text-anchor="middle">a set of values,</text><text class="mtp-d-sub" x="315" y="470" text-anchor="middle">known when compiling</text><rect class="mtp-d-part" x="425" y="155" width="150" height="104" rx="6"/><text class="mtp-d-name" x="500" y="179" text-anchor="middle">container</text><text class="mtp-d-sub" x="500" y="199" text-anchor="middle">a variable or</text><text class="mtp-d-sub" x="500" y="215" text-anchor="middle">an attribute</text><text class="mtp-d-sub" x="500" y="242" text-anchor="middle">free, bound or const</text><line class="mtp-d-arrow" x1="425" y1="182" x2="387" y2="140" marker-end="url(#mtp-dm-head)"/><line class="mtp-d-arrow" x1="425" y1="228" x2="387" y2="270" marker-end="url(#mtp-dm-head)"/><text class="mtp-d-label" x="500" y="145" text-anchor="middle">holds one</text></g></svg>
</figure>

## Objects

| Object | What the runtime does with it |
|---|---|
| the scene and its shapes | draws them |
| formulas and their terms | typesets them |
| views: canvas, readout, display | lays them out on the page |
| controls: slider, button, play, stepper, toggle | the reader acts on them, and they set off movements |
| listeners, such as `on-drag` and `on-click` | the reader acts on a shape or a term, and they set off movements |
| movements: `move`, `score`, a use of an animation | writes their targets over time |
| functions | calls them |
| records | holds their attributes |

A {term}`collection` holds other objects, its members: a group, a row or a column holds shapes,
and a score holds movements. A motif is a type of shape that the illustrator declares, and an
animation is a type of movement ({doc}`data-model`).
