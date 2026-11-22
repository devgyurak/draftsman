# Query capture protocol

A language is `queries/<lang>.scm` plus a small `LanguageSpec` in
`scripts/draftsman/langs/<lang>.py` (`LanguageSpec.extra_queries` adds files for what only
one grammar has: TSX's JSX in `queries/tsx.scm`). The extractor runs the query over each file and
interprets **matches** (not individual captures) by capture name. Captures starting with
`_` are free for predicates (`(#eq? @_ctor "constructor")`).

## File scope

| capture | meaning |
|---|---|
| `@package` | namespace of the whole file (Java `package`, C# file-scoped namespace) |
| `@namespace` + `@namespace.name` | a namespace *block*; types inside get its name prepended |
| `@import` (+ `@import.alias`) | an import of one type by full path |
| `@import.wildcard` | a namespace whose members all become visible (`a.b.*`, `using X;`) |
| `@import.static` | with `@import` or `@import.wildcard`: a Java `import static`, of a type's members (`a.B.N`, `a.B.*`) |
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
| `@annotation` + `@annotation.target` | – | an annotation/decorator/attribute and the declaration it applies to (its name in `annotations`) |
| `@annotation.ref` + `.name`, `.args`, `.target` | yes | an annotation on a declaration or a parameter, for its relations: `.name` the annotation type as written, `.args` its arguments, `.target` the declaration when it does not enclose the annotation (Python `decorated_definition`, TS `export @Dec() class`) |
| `@param` + `@param.name`, `@param.type`, `@param.declarator`, `@param.varargs` | yes | a parameter |
| `@throws` | yes | a type a method declares it throws (a dependency, not shown) |

## Bodies

Names written in bodies become relations marked `evidence: "body"`. The captures say where
a body is, which names it writes, and what may hide them there.

| capture | match root? | meaning |
|---|---|---|
| `@body.region` | – | a body: a method or constructor body, a field initializer, an enum constant's arguments and body. A name is read only at or below one (a TypeScript field initializer may be the name itself: `X = Kind.A`), so a signature's `List<Foo>` is not |
| `@body.init` (+ `@body.init.name`) | – | a body of no listed member, `via` `.name` when given (a record's compact constructor), else its text before `{` plus `{}` (initializer blocks: `static {}`, `{}`). Only a named type's own count |
| `@body.ref.type` / `@body.ref.receiver` | yes | a name written in a body: `.type` where only a type can stand (every type name: `new Foo()`, a cast, `X.class`, `X.this`), `.receiver` where a variable can too (`Foo.bar()`; in TypeScript every value: `new Foo()`, `typeof Foo`, `<Foo />`). A receiver is a dotted name: every node of it one of `LanguageSpec.receiver_part_nodes` (not `this.x`, `new Foo(x).m`). A capture whose parent is captured too is part of that name and dropped (`Foo` in `p.Foo`), and so is one captured as `@body.type` (`T` in `<T extends Foo>`). The name is its identifiers joined by `.`, leaving out annotations, comments and `LanguageSpec.type_argument_nodes` (`Outer<T>.Inner` is `Outer.Inner`, and `T` a name of its own); each part keeps its line and column, in UTF-16 code units as javac counts them |
| `@body.unread` | – | a type node that is no name of the scope, never recorded: looked up in the type of an expression (Java `o.new Inner()`), or no name at all (`X.super` in `X.super::m`, where `X` is) |
| `@body.blind` | – | a class body whose inherited members are not known (the anonymous class of Java `o.new Inner() { }`), or a node whose names are read elsewhere or not at all (TypeScript decorators, TSX closing tags): no name in it is recorded |
| `@body.var` | – | a variable declared in a member: parameters, locals, lambda, catch, for and pattern variables, resources, fields of local classes, local functions and destructured names (TypeScript) |
| `@body.type` | – | a type name declared in a member: local classes, type parameters |
| `@body.class` + `@body.class.super` | – | the body of an anonymous or local class and one supertype it names; the members it inherits are in scope inside it. Not for `o.new Inner() { }`, whose supertype is a member of o's type |

A `@body.ref.*` belongs to the nearest enclosing named type, across opaque nodes (a name
in a lambda or an anonymous class is the named type's), `via` the member or initializer
around it; with several declarators (`static A X = .., Y = ..;`), the one written last
before the name. One in an annotation's arguments is dropped, also inside a body.
`@body.var` and `@body.type` are collected per member, wherever in it they stand: a name
the member declares anywhere may hide a type of that name anywhere in it, which drops a
reference at worst. `@body.class` lists the anonymous and local classes around a
reference, innermost first.

How a recorded name resolves follows the language's scoping, set in its `LanguageSpec`:
`fields_in_scope` (whether a field hides a receiver; not in TypeScript, where a field is
`this.x`), `nested_types_in_scope` (whether a type sees its own nested types by simple
name), `type_only_kinds` (kinds that are no value, so a receiver of their name draws
nothing: TypeScript interfaces) and `receiver_package_heads` (whether a dotted receiver
whose head is no type is a package, as in Java, or goes through what the file imports, as
TypeScript's `ns.Foo.m()`).

## Ownership

Captures are attached to declarations by position in the tree, not by the query:

- a member or supertype belongs to the **nearest enclosing `@type.*` node** — searched
  from `LanguageSpec.ownership_start` (Python moves `self.x` assignments up to the class of
  their `__init__`);
- a `@param` belongs to the nearest enclosing method/constructor (dropped if a type is
  reached first);
- a `@tparam` belongs to the nearest type or method, unless `@tparam.target` says otherwise;
- an `@annotation.ref` belongs to its `.target` when that is a type, else to the nearest
  enclosing type: the type itself for its own annotations, the enclosing type for those on
  members and parameters. Its `.args` are walked by `LanguageSpec.annotation_arg`, which
  says which nodes name a type (`annotation_type_args`: `X.class`, `typeof(X)`) and which
  may name a type or a value (`annotation_value_args`: `E.V`, `Model`); argument names
  (`using = `) and nested `@annotation.ref` nodes are skipped.
  `LanguageSpec.annotation_type_names` maps the written name to the types it may stand
  for (C# `[Obsolete]` → `ObsoleteAttribute`).

If an **opaque node** (`LanguageSpec.is_opaque`: method bodies, lambdas, anonymous class
expressions, inline object types, …) lies on the way up, the capture is dropped. The same
rule skips local and anonymous types. Crossing a **static scope** node (Kotlin companion
object) makes the member static, unless the node is itself a `@type.*` (a companion with
supertypes); its name in a qualified type name (`static_scope_names`: `X.Companion.Inner`)
is skipped, since the types declared in it are recorded as `X`'s. `LanguageSpec.type_name` names a type whose `@name` capture is not its name
(`companion` → `Companion`), and `LanguageSpec.member_name` the name a member is listed
under (Kotlin's primary constructor is `constructor`). `LanguageSpec.is_import` drops an
`@import*` capture that does not import (C++ `using` in a class body), and
`LanguageSpec.alias_target` reads what an `@alias.type` names (C `typedef struct S {…} T;`
names `S`; None when the declaration is the type itself).

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
