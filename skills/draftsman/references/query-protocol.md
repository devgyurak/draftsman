# Query capture protocol

A language is `queries/<lang>.scm` plus a small `LanguageSpec` in
`scripts/draftsman/langs/<lang>.py`. The extractor runs the query over each file and
interprets **matches** (not individual captures) by capture name. Captures starting with
`_` are free for predicates (`(#eq? @_ctor "constructor")`).

## File scope

| capture | meaning |
|---|---|
| `@package` | namespace of the whole file (Java `package`, C# file-scoped namespace) |
| `@namespace` + `@namespace.name` | a namespace *block*; types inside get its name prepended |
| `@import` (+ `@import.alias`) | an import of one type by full path |
| `@import.wildcard` | a namespace whose members all become visible (`a.b.*`, `using X;`) |
| `@import.from` + `@import.name` (+ `@import.alias`) | `from module import Name` style; the module text goes through `LanguageSpec.module_id` |
| `@import.module` (+ `@import.alias`) | a whole module bound to a local name (`import * as pay`, `import typing as t`) |
| `@alias` (+ `@alias.type`) | a type alias declaration and the type it names; references to it are drawn as references to that type |
| `@typevar` | a file-wide type parameter (Python `T = TypeVar("T")`) |

## Declarations

| capture | match root? | meaning |
|---|---|---|
| `@type.<kind>` | yes | a type declaration; `<kind>` is an IR type kind. When several patterns match one node, a specific kind beats `class` |
| `@member.<kind>` | yes | `field`, `method`, `property`, `constructor`, `enum_constant` |
| `@name` | in type/member | declared name (may be qualified for C++ out-of-class nested types) |
| `@receiver` | in member | receiver type of a member extension function (Kotlin `fun Grammar.plus()`) |
| `@type` | in member | field type or return type |
| `@declarator` | in member | C-style declarator; `LanguageSpec.declarator` returns name, `*`/`&`/`[]` suffix and whether it declares a function (turning a `field` into a `method`) |
| `@modifiers` | in type/member | modifier node(s); leaves are keywords, `annotation_nodes` are annotations |
| `@body` | in member | present ⇒ the method has a body (for implicit `abstract`) |
| `@abstract` | in member | marker text handed to `is_abstract` (C++ `= 0`) |
| `@value` | in member | initialiser text (Python `self.x = param`) |
| `@super.extends` / `.implements` / `.inherits` | – | a supertype; `inherits` = decide by the target's kind |
| `@tparam` (+ `@tparam.target`) | – | a type parameter; `target` names the declaration when it is not an ancestor (C++ `template<>` wraps the class) |
| `@annotation` + `@annotation.target` | – | an annotation/decorator/attribute and the declaration it applies to |
| `@param` + `@param.name`, `@param.type`, `@param.declarator`, `@param.varargs` | yes | a parameter |
| `@throws` | yes | a type a method declares it throws (a dependency, not shown) |

## Ownership

Captures are attached to declarations by position in the tree, not by the query:

- a member or supertype belongs to the **nearest enclosing `@type.*` node** — searched
  from `LanguageSpec.ownership_start` (Python moves `self.x` assignments up to the class of
  their `__init__`);
- a `@param` belongs to the nearest enclosing method/constructor (dropped if a type is
  reached first);
- a `@tparam` belongs to the nearest type or method, unless `@tparam.target` says otherwise.

If an **opaque node** (`LanguageSpec.is_opaque`: method bodies, lambdas, anonymous class
expressions, inline object types, …) lies on the way up, the capture is dropped. The same
rule skips local and anonymous types. Crossing a **static scope** node (Kotlin companion
object) makes the member static, unless the node is itself a `@type.*` (a companion with
supertypes). `LanguageSpec.type_name` names a type whose `@name` capture is not its name
(`companion` → `Companion`), and `LanguageSpec.member_name` the name a member is listed
under (Kotlin's primary constructor is `constructor`).

## Adding a language

1. Write `queries/<lang>.scm` using the captures above.
2. Add `langs/<lang>.py`: extensions, opaque nodes, builtins, visibility rules, and
   whatever hooks the language needs (`file_namespace`/`module_id` for module-based
   languages, `preprocess`, `finalize_type`, `external_super_kind`). Register it in
   `langs/__init__.py`.
3. Set the scope flags: `parent_namespace_lookup` (enclosing namespaces are visible),
   `import_suffix_match` (import paths matched by unique suffix) and
   `inherited_member_types` (a supertype's nested types are in scope by simple name).
4. Add a fixture under `tests/fixtures/<lang>/shop/` mirroring the others, add the language
   to `tests/test_languages.py`, and a pitfalls test for its quirks.
5. Give the language a witness in every row of `SCOPE_RULES` in `tests/test_languages.py`:
   a relation in its shop fixture that only that name-resolution rule produces, or `None`
   with the reason the rule does not exist there. The same goes the other way: a change
   to `resolve.py` adds a row (or a witness) for every language, so one language's fix
   cannot silently change another's resolution.
