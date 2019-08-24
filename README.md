# Polyblocks


## Syntax

Polyblock works in two modes: the _embedded mode_, where the block syntax
is embedded in a language's syntax, and the _standalone mode_, where the 
file is encoded primarily with the Polyblock syntax.

In standalone mode, the parsing is done line by line, using indentation
to determine where the content belongs:

- Block declarations all start with an unindented `@` followed by the 
  block name and some optional data.
- Block content all start with an indented value (by default, one tab).
- Comments are unindented and start with a `#`.

In embedded mode, the parsing is also done on a line-by-line basis, with
the following differences:

- Block declarations all start with a customizable language-specific prefix (`#` for shell-like,
  `*` for C-Like languages) followed by the `@`, like in the standalone mode.
- Block content must follow directly after the block declaration.
- Host language code is included as a verbatim block.

## Block types

```
@texto
```  

```
@h2 Section title
```  

```
@javascript {hidden}
```

```
@component controls/logger <- input <- log
```
```
@component controls/input -> value -> name
```





https://thepaciellogroup.github.io/cupper/patterns/coding/color-palettes/
