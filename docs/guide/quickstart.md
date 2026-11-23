# Quickstart

This page takes you from nothing to a live figure on your own web page, in four steps.

## 1. Install mtp

You need [uv](https://docs.astral.sh/uv/), which installs Python for you if you do not have it.

```sh
uv tool install mathterpiece
```

This gives you the `mtp` command. With pip instead, `pip install mathterpiece` does the same, and
needs Python 3.13 or later.

## 2. Write a figure

Save this as `circle.mtp` in a folder of your own:

```{mtp-example}
; a point on the unit circle, with cos in red and sin in green
(real theta 40 (wrap 0 360))
(scene s
  (circle rim (r 1) (fill none) (stroke #'gray'))
  (line cos (from [0 0]) (to [(cosd theta) 0]) (stroke #'crimson') (stroke-width 4))
  (line sin (from [(cosd theta) 0]) (to (polar 1 theta)) (stroke #'seagreen') (stroke-width 4))
  (circle p (r 0.07) (pos (polar 1 theta)) (fill #'slateblue')))
(canvas v (x -1.25) (y -1.25) (width 2.5) (height 2.5) s
  (on-drag p (move theta (to (. (or? (to-polar pointer) [1 theta]) 1)))))
(slider turn theta (from 0) (to 360) (label 'θ'))
```

The figure above is live: drag the point or move the slider. The file declares one variable,
`theta`, an angle that wraps around at 360. The scene draws a circle, a point at angle `theta`,
and the two lines whose lengths are its cosine and its sine. The canvas `v` shows the scene, and
dragging the point moves `theta`. The slider `turn` moves `theta` too.

## 3. Check and compile it

```sh
mtp check circle.mtp
mtp compile circle.mtp
```

`mtp check` reports the first error, with its line and column, and writes nothing. When the
figure is right, `mtp compile` writes `circle.mtpc`, the compiled figure.

To see the figure while you edit it, run `mtp serve circle.mtp` and open the address that it
prints. The page reloads each time you save the file.

## 4. Put it on a page

Copy `circle.mtpc` into the folder of your page, and write:

```html
<script type="module" src="https://cdn.jsdelivr.net/npm/mathterpiece@0.1.0/dist/mathterpiece.js"></script>

<mtp-model id="circle" src="circle.mtpc"></mtp-model>
<mtp-canvas model="circle" name="v"></mtp-canvas>
<p>Turn the point: <mtp-slider model="circle" name="turn"></mtp-slider></p>
```

The first line loads the runtime, which draws figures, from the npm package `mathterpiece`.
`<mtp-model>` loads the figure. `<mtp-canvas>` and `<mtp-slider>` place its canvas and its
slider anywhere in the text, by the names that the source gives them.

The browser reads `circle.mtpc` over HTTP, so open the page through a web server, not as a file.
For a quick test, run `uv run --no-project python -m http.server` in the page's folder and open
<http://localhost:8000>.
