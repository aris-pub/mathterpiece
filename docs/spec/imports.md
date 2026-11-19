(imports)=
# Imports

This page defines how a file uses the declarations of another `.mtp` file: how an `import` is
written, which file it reads, what that file may hold, and which {term}`names <name>` the import
gives. Two rules about imports are on other pages, next to rules of the same kind: where an
`import` may be written is in {doc}`grammar`, and which imported declarations the {term}`.mtpc`
holds is in {numref}`mtpc-imported-declarations`. The {term}`compiler` reads no
file other than the source and the files that it imports ({numref}`compiler-reads-files`).

The rewrite step reads every imported file ({numref}`compile-steps`), so a source that breaks a
rule of this page is rejected in the rewrite step. This page specifies the language.

## How an import is written

```{rule} import-form
An import is `(import F)` or `(import F N1 N2…)`, with `F` and each `Ni` a name of one
{term}`name part` ({numref}`name-characters`). `(import F)` imports the file `F.mtp` whole, and
`(import F N1 N2…)` imports the names `N1`, `N2` and so on from `F.mtp`. Any other `import` is a
{term}`compile error`, "import is (import file name…)", and so is an `Ni` that `F.mtp` does not
give ({numref}`import-files`), "F.mtp gives no 'Ni'".
```

So `(import colors)`, `(import math dot clamp)` and `(import house ink)` are imports, and
`(import)`, `(import 'colors')`, `(import colors.okabe-ito)` and `(import math (dot))` are compile
errors. A name given twice, as in `(import math dot dot)`, is a compile error by
{numref}`one-declaration-per-scope`.

:::{admonition} Code differs
:class: note
The error for an `Ni` that `F.mtp` does not give reads "F.mtp declares no 'Ni'". mtp-ydd4.7.62.
:::

## Which file an import reads

```{rule} import-file-name
`(import F …)` reads the file whose name is `F` followed by `.mtp`, looked for in the folders that
{numref}`compiler-reads-files` gives, in that order. A file is found only when its name is `F.mtp`
character for character, upper and lower case included, on every file system. When neither folder
holds such a file, the import is a compile error, "no F.mtp next to S.mtp or in the standard
library", with `S.mtp` the importing file.
```

So `(import Colors)` finds no file when the only file of that name is colors.mtp, also on a file
system that does not tell upper and lower case apart. A source next to a file colors.mtp of its own
reads that file with `(import colors)`, and never the file colors.mtp of the
{term}`standard library`.

:::{admonition} Code differs
:class: note
`compiler.py:7163` (`_find`) asks the file system whether `F.mtp` exists, so on a Mac, where the
file system does not tell upper and lower case apart, `(import Colors)` reads colors.mtp and the
source compiles, while on Linux the same source is a compile error. Bead mtp-ydd4.7.57.
:::

```{rule} import-same-file
Two imports read the same file when the two paths name one file on disk, links followed. A file
imported several times, directly or through other files, is put in once ({numref}`import-puts-in`).
Two different files of the same name imported into one source, directly or through other files,
are a compile error, "two different files named F.mtp are imported". A file that imports itself,
directly or through the files that it imports, is a compile error, "F.mtp imports itself, through
the files it imports".
```

So when a file of the standard library writes `(import colors …)`, a source next to a file
colors.mtp of its own that imports both is a compile error: the file of the standard library reads
colors.mtp of the standard library, its own folder, and the source then holds two different files
named colors.mtp.

## What a file to import holds

```{rule} import-file-holds
A {term}`file to import` holds at its top level only `import`, `let`, `foreach`, and declarations of
colors, fonts, functions, motifs, variants, types, interfaces, records, palettes, colormaps,
animations, {term}`seeds <seed>` (`rand-seed`) and variables that are `const`. A file of the standard
library also holds `(primitive …)` ({numref}`primitive-form`). Any other form there is a compile error at that form, in every
source that imports the file.
```

```{rule} import-proves-whole-file
The compiler proves every declaration of an imported file, whether the source uses it or not. A
declaration that breaks a rule of the spec is a compile error in every source that imports the
file, and the error gives the line and column in the imported file.
```

So whether a file to import is correct never depends on the source that imports it.

:::{admonition} Code differs
:class: note
- For a form that a file to import may not hold, the error is "F.mtp holds X: a file to import
  holds only declarations of colors, fonts, functions, motifs, variants, types and const
  variables" (`compiler.py:799`). The list leaves out namespaces, palettes, colormaps,
  interfaces, choreos and seeds, which a file to import may hold. Bead mtp-ydd4.7.58.
- An imported file that the source uses only in part is compiled a second time on its own, to
  check the declarations that nothing uses (`compiler.py:815-823`) (mtp-08wd.6).
:::

## The names that an import gives

```{rule} import-puts-in
`(import F)` puts the top-level declarations of `F.mtp` into the source, after the rewrites of
`F.mtp`, each under the name `F.N`, where `N` is its name in `F.mtp`. Each `F.N` and each `(. F N)`
in the source is a use of that declaration. `(import F N1 N2…)` does the same, and each `Ni` in the
source is also a use of `F.Ni`. A file imported several times, directly or through other files, is
put in once.
```

:::{admonition} Code differs
:class: note
`_through` (compiler.py:7280-7290) reads only a name with several name parts, so after
`(import lib)`, `lib.k` is accepted, and `(. lib k)` is a compile error, "unknown name 'lib'"
(compiler.py:6056) (mtp-ydd4.7.47).
:::

```{rule} import-files
An imported file has a {term}`file scope` of its own: its forms use only the names that it
declares, binds and imports, and never a name of a file that imports it. A file gives a file
that imports it its own top-level declarations and the names that it imports by name, with
`(import G N…)`, and never the name of a file that it imports whole.
```

So inside house.mtp, a function reads the color `ink` of house.mtp by its bare name, and a
`let` name `ink` in it hides that color, by {numref}`name-lookup`. With `(import house ink)` in a
source and `(import colors red)` in house.mtp, the source may also write `(import house red)`.
With `(import colors)` in house.mtp, `(import house colors)` is a compile error by
{numref}`import-form`. The names of the standard library are ordinary declarations of its files,
and a source brings them in as it brings in the names of any other file. Among them are the
random functions, which the file rand declares with `(primitive …)` ({numref}`primitive-form`).

```{rule} import-declares-names
An `(import …)` gives its names at its place in the file.
```

By {numref}`declare-before-use`, a name that an import gives is then used only after the import.
An import need not come before the forms that do not use its names. So
`(scene s (circle c (fill colors.tab10-named.red))) (import colors)` is an error, and the same
two forms in the other order are allowed. The names that an import gives share the file scope with
the file's own declarations, so by {numref}`one-declaration-per-scope`, `(import house ink)`
followed by `(color ink 'red')` is a compile error.

:::{admonition} Code differs
:class: note
`compiler.py:745` (`imports`) reads every import of a file before any other form, so an import may
come after the forms that use its names. Bead mtp-ydd4.7.12 makes such a use an error.
:::
