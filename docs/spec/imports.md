(imports)=
# Imports

This page defines how a file uses the declarations of another `.mtp` file: how an `import` is
written, which file it reads, what that file may hold, and which {term}`names <name>` the import
makes usable. Two rules about imports are on other pages, next to rules of the same kind: where an
`import` may be written is in {doc}`grammar`, and which imported declarations the {term}`.mtpc`
holds is in {numref}`mtpc-imported-declarations`. The {term}`compiler` reads no
file other than the source and the files that it imports ({numref}`compiler-reads-files`).

The rewrite step reads every imported file ({numref}`compile-steps`), so a source that breaks a
rule of this page is rejected in the rewrite step.

## How an import is written

This rule exists to fix the two ways of writing an import, so that the compiler rejects every other way.

```{rule} import-form
An import is `(import F)`, which imports the file `F.mtp` whole, or `(import F N1 N2…)`, which imports
those names from it, with `F` and each `Ni` a name of one {term}`name part`. Any other `import` is a
{term}`compile error`, "import is (import file name…)", and so is an `Ni` that `F.mtp` does not have
({numref}`import-files`), "F.mtp has no name 'Ni'".
```

So `(import colors)`, `(import math dot clamp)` and `(import house ink)` are imports, and
`(import)`, `(import 'colors')`, `(import colors.okabe-ito)` and `(import math (dot))` are compile
errors. A name given twice, as in `(import math dot dot)`, is a compile error by
{numref}`one-declaration-per-scope`.

:::{admonition} Code differs
:class: note
The error for an `Ni` that is not a name of `F.mtp` reads "F.mtp declares no 'Ni'". mtp-ydd4.7.62.
:::

## Which file an import reads

This rule exists so that an import finds the same file on every file system.

```{rule} import-file-name
`(import F …)` reads the file `F.mtp`, looked for in the folders of {numref}`compiler-reads-files`, in
order, and found only when its name matches character for character, case included, on every file
system. When no folder holds it, the import is a compile error, "no F.mtp next to S.mtp or in the
standard library", with `S.mtp` the importing file.
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

This rule exists so that a file imported several times is put in once, and its declarations are not declared twice.

```{rule} import-same-file
Two imports read the same file when they find the same file on disk, through a symbolic link or not.
A file imported several times, directly or not, is put in once ({numref}`import-puts-in`). Two
different files of the same name imported into one source are a compile error, "two different files
named F.mtp are imported", and so is a file that imports itself, directly or not, "F.mtp imports
itself, through the files it imports".
```

So when a file of the standard library writes `(import colors …)`, a source next to a file
colors.mtp of its own that imports both is a compile error: the file of the standard library reads
colors.mtp of the standard library, its own folder, and the source then holds two different files
named colors.mtp.

## What a file to import holds

This rule exists so that importing a file adds nothing to the page that the source did not declare itself.

```{rule} import-file-holds
At its top level, a {term}`file to import` may hold only `import`, `let`, `foreach`, and declarations of
types, functions, records, {term}`seeds <seed>` and variables that are not free. Anything else there is a
compile error.
```

This rule exists so that an error in an imported file is found whether or not a source uses the part that holds it.

```{rule} import-checks-whole-file
The compiler checks every declaration of an imported file, whether the source uses it or not.
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

## The names that an import makes usable

This rule exists to specify the names under which a source may use what it imports.

```{rule} import-puts-in
`(import F)` makes each name `N` of `F.mtp` usable as the {term}`qualified name` `F.N`, and
`(import F N1 N2…)` also makes each `Ni` usable on its own.
```

:::{admonition} Code differs
:class: note
`_through` (compiler.py:7280-7290) reads only a name with several name parts, so after
`(import lib)`, `lib.k` is accepted, and `(. lib 'k')` is a compile error, "unknown name 'lib'"
(compiler.py:6056) (mtp-ydd4.7.47).
:::

This rule exists so that a file means the same thing whichever file imports it.

```{rule} import-files
An imported file has a {term}`file scope` of its own, and may use only the names that it declares,
binds and imports, never one of a file that imports it. Its names are its top-level declarations and
the names that it imports with `(import G N…)`, not the name of a file that it imports whole.
```

So with `(import colors red)` in house.mtp, a source may write `(import house red)`, and with
`(import colors)` in house.mtp, `(import house colors)` is a compile error. The files of the
{term}`standard library` are imported like any other file ({doc}`stdlib`).

This rule exists so that an imported name follows the same order as every other name (declare before use).

```{rule} import-declares-names
An `(import …)` makes its names usable from its place in the file on.
```

So `(scene s (circle c (fill colors.tab10-named.red))) (import colors)` is a compile error, and the same two
forms in the other order are allowed.

:::{admonition} Code differs
:class: note
`compiler.py:745` (`imports`) reads every import of a file before any other form, so an import may
come after the forms that use its names. Bead mtp-ydd4.7.12 makes such a use an error.
:::
