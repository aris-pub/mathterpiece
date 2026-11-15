```{include} ../mtpc.md
```

:::{admonition} Code differs
:class: note
A real is finite ({numref}`number-types`), so no .mtpc holds `"infty"` or `"-infty"`, and the row
for `int` and `real` of "Values" above, which allows them, is wrong. The compiler writes them
(mathterpiece/mtpc.py, line 500), and the runtime reads them (web/src/runtime.ts, lines 932 and
933). Bead mtp-ydd4.7.33 removes them from the compiler, the runtime, docs/mtpc.md and the schema.
:::
