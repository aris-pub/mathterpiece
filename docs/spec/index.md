# Specification

This is the draft of version 1 of the specification ({numref}`spec-version`).

The specification defines the mtp language: its syntax, what a world model means, and how an open page
behaves. It is written for the people and agents who build mtp or implement it again. Every
rule is stated once, here, and everything else links to it.

The first drafts left questions open: {doc}`open-questions` groups them by principle.

```{toctree}
:caption: Introduction
:numbered:
:maxdepth: 2

one-page
overview
compiler-runtime
```

```{toctree}
:caption: Syntax
:numbered:
:maxdepth: 2

lexical
grammar
core
heads
```

```{toctree}
:caption: Data and types
:numbered:
:maxdepth: 2

data-model
world-model
scope
imports
types
```

```{toctree}
:caption: Meaning of expressions
:numbered:
:maxdepth: 2

evaluation
binding-time
well-formedness
```

```{toctree}
:caption: Execution
:numbered:
:maxdepth: 2

reactivity
time
concurrency
lifecycle
```

```{toctree}
:caption: The page
:numbered:
:maxdepth: 2

page-interface
controls
accessibility
```

```{toctree}
:caption: Reference
:numbered:
:maxdepth: 2

compiled-format
errors
stdlib
```

```{toctree}
:caption: Appendices
:maxdepth: 1

glossary
rules
open-questions
```
