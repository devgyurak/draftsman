---
description: Draw a UML class diagram of this codebase (facts from a parser, not guesses)
argument-hint: "[ClassName | path] [mermaid|svg|html] [members|public|no-members]"
---

Use the `draftsman` skill to draw a class diagram.

Arguments: $ARGUMENTS

- A word that looks like a class name is the `focus` (hops 2).
- A path is the source directory to extract (default: the current repository).
- `mermaid`, `svg` or `html` selects the output; otherwise choose by the skill's rules.
- `members`, `public` or `no-members` sets the view's `members` to `all`, `public` or
  `none`; otherwise choose by the skill's rules.

Follow the skill's workflow and hard rules: extract, survey, write view.json, render,
validate, then answer with the diagram, the scope you chose and the unresolved references.
