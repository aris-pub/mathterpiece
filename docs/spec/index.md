# Specification

This is the draft of version 1 of the specification ({numref}`spec-version`).

The specification defines the mtp language: its syntax, what a world model means, and how an open page
behaves. It is written for the people and agents who build mtp or implement it again. Every
rule is stated once, here, and everything else links to it.

The first drafts left questions open: {doc}`open-questions` groups them by principle.

```{toctree}
:numbered:
:maxdepth: 2

overview
compiler-runtime
lexical
grammar
core
scope
imports
types
binding-time
well-formedness
world-model
evaluation
reaction
time
concurrency
lifecycle
page-interface
accessibility
compiled-format
errors
stdlib
```

```{toctree}
:hidden:

glossary
rules
open-questions
```
