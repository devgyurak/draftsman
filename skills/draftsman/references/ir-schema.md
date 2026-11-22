# ir.json

Produced by `scripts/extract.py`; never edited by hand. Lists are sorted, so the same
sources always give byte-identical output.

```jsonc
{
  "version": 1,
  "root": "path/given/to/extract",
  "languages": ["java"],          // java csharp kotlin typescript tsx python cpp
  "files": 11,
  "types": [Type],
  "relations": [Relation],
  "externals": [External],
  "unresolved": [Unresolved],
  "diagnostics": [Diagnostic]
}
```

## Type

| field | notes |
|---|---|
| `id` | qualified name, unique in the IR. Separator is the language's own: `com.shop.Order.Status` (Java, C#, Kotlin), `shop::pay::Receipt` (C++), `src.shop.order.models.Order` (Python module path), `src/order/order.Order` (TypeScript file path without extension) |
| `name` | simple name (`Status`) |
| `qualified_name` | same as `id` for now; kept separate for languages that need disambiguation |
| `kind` | `class` `interface` `abstract_class` `enum` `record` `struct` `union` `object` `trait` `mixin` `annotation` |
| `language` | `java`, ... |
| `namespace` | package / namespace / module, or `null` |
| `outer` | id of the enclosing type for nested types, else `null` |
| `modifiers` | keywords as written (`public`, `abstract`, `sealed`, ...) |
| `annotations` | annotation/decorator names as written (`Entity`, `ChannelHandler.Sharable`) — useful for grouping and noise; the project ones are also relations (below) |
| `generics` | type parameter names (`["T"]`) |
| `location` | `{file, line}`, file relative to `root` |
| `members` | list of Member, source order |

Declarations of the same qualified name in several files are merged (C# `partial`, C++
header/source).

## Member

| field | notes |
|---|---|
| `name`, `kind` | kind: `field` `method` `property` `constructor` `enum_constant` |
| `visibility` | `public` `protected` `package` `internal` `private`, with the language's default applied |
| `type_ref` | the type as written (field type / return type), or `null` |
| `static`, `abstract` | language rules applied (interface methods without body are abstract, interface fields static, ...) |
| `params` | methods and constructors: `[{name, type_ref}]` |
| `modifiers`, `annotations` | omitted when empty (Python decorators and C# attributes are annotations) |
| `file` | only when the member is declared in another file than the type (C# partial classes, Kotlin expect/actual) |
| `receiver` | Kotlin member extensions only: the receiver type of `fun Grammar.unaryPlus()` |
| `line` | 1-based |

## Relation

| field | notes |
|---|---|
| `from`, `to` | type ids; `to` may be an `externals` id for `extends`/`implements` |
| `kind` | see below |
| `multiplicity` | associations only: `"1"`, `"0..1"`, `"*"` |
| `ownership` | C++ associations only: `owned` (value, `unique_ptr`) or `shared` (pointer, `shared_ptr`) |
| `via` | member that produced it (field name for associations, method name for dependencies), or the annotation, as `@Name`, for a dependency an annotation produced |
| `evidence` | `"body"` for a relation read from a name written in a body (`new Foo()`, `Foo.bar()`); absent for one read from a declaration |
| `source_location` | `{file, line}` of the declaration that produced it |

How each kind is derived:

- **extends / implements** — the type's own supertype clauses.
- **association** — an instance field (or property) whose type, after unwrapping
  containers from `config/wrappers.yaml` and `T[]`/`T?`/`T | None`, names a project type.
  One relation per field; `multiplicity` comes from the unwrapping. When that type is a
  generic that is not a container (`Repository<User>`, `Type<Factory>`), the field also
  gets a **dependency** on each project type among its arguments, and so do the container
  arguments a wrapper rule does not follow (the key of `Map<K, V>`). A function type
  (`Config.() -> Unit`, `(req: Req) => Res`, `Callable[[Event], Result]`) is no
  association: the field depends on every project type it names.
- **dependency** — a project type mentioned anywhere in a method or constructor signature
  (parameters, return type, type arguments), or in the type of a **static** field
  (constants and singletons are not instance structure). One relation per member, never
  to the type itself. The renderer collapses these to one arrow per pair and drops them
  where an association or inheritance already connects the pair.
- **dependency from an annotation** — an annotation, attribute or decorator on the type,
  one of its members or one of their parameters, `via` `@Name` as written:
  - on the annotation type, when it is a project type (`@Sharable` imported from
    `ChannelHandler`, C# `[Marker]` naming `MarkerAttribute`); framework annotations stay
    names in `annotations`, and one is unresolved only when the project declares an
    annotation of that name it may mean;
  - on each project type its arguments name: a class literal (`X.class`, `X::class`,
    `typeof(X)`, unresolved like a signature type when it names nothing known), and a name
    that may be a type or a value (`Include.NON_NULL` → `Include`, `nameof(Order)`, a class
    passed to a decorator, `@Module({imports: [UsersModule]})`), drawn only when it is a
    project type and never unresolved. A nested annotation (`@A(@B(X.class))`) is an
    entry of its own.
  Annotations inside bodies (locals, lambdas) are not part of the declaration.
- **dependency from a body** (Java; `evidence` `"body"`) — a project type named in a
  method or constructor body, an initializer, a field's initial value or an enum
  constant's arguments and body: in type position (`new Foo()`, a cast, `instanceof`, a
  local variable's type, `X.class`, type arguments, a local or anonymous class's header and
  members) or as a receiver (`Foo.bar()`, `Foo.X`, `Foo::bar`). `via` the member or
  initializer (`static {}`, `{}`) the body belongs to, `source_location` the line of the
  first such name; one relation per member, never to the type itself. A name that may mean
  something else draws nothing and is never unresolved: a variable of the name in scope
  for a receiver, a type of the name the member declares, a nested type a supertype passes
  on (lang-notes.md has the rules and what is not known). What a call on a value reaches
  (`order.total()`) is not read.

Composition vs. aggregation is not inferred (except C++ `ownership`), and nothing else from
method bodies is used.

A nested type is a type of its own with its own relations; nesting itself is no relation
(`outer` records it). A focus diagram folds nested types into their outer type (see
`view-schema.md`), which is a drawing decision: ir.json always keeps the nested type.

Type aliases (`type X = ...`, `typedef`, `typealias`, `using X = ...`) are not types in
the IR; a reference to one is drawn as a reference to the project types the alias names
(`x: X` with `type X = A | B` is an association to `A` and to `B`). Module-level Python
assignments may be values and draw nothing. Tuples (`[A, B]`, `(A a, B b)`, `tuple[A,
B]`, `std::pair<A, B>`) relate to each element with multiplicity `1`. Names read this way
(`Tuple`, `tuple`, `ValueTuple`, `std::pair`, Python `Literal[...]`, and the containers of
`config/wrappers.yaml`) mean the project's class when the project defines one: a Java
`Tuple<A, B>` class is an association to `Tuple`. A TypeScript `typeof x` is a relation
when `x` is a class and is otherwise a value: never unresolved.

## External

`{id, name}` — a type outside the sources that a project type extends or implements, e.g.
`org.springframework.data.repository.CrudRepository` or `RuntimeException`. Field and
signature references to external types produce no relation.

## Unresolved

A type reference that is neither a project type, a type alias, a builtin, nor an
explicitly imported external. These are the only names `inferred_edges` may introduce.
Fully qualified names into unknown namespaces (`stripe::Client`, `java.util.Date`) and
names imported from packages (`import { X } from 'lib'`) are externals, not unresolved.

| field | notes |
|---|---|
| `from` | type containing the reference |
| `raw_type` | the name as written |
| `via` | member it appeared in, if any |
| `candidates` | project types with the same simple name that the reference could mean (not linked automatically). A nested type is one only where its simple name reaches it, inside its outer type; elsewhere the hint names it instead (`project nested type of the name, out of scope here: a.Outer.Entry`) |
| `hint` | where the name may come from: `may come from wildcard import com.stripe.*` (packages outside the sources by name, then a count of those the project also declares), `may be the default import java.lang.Class`, `may be a nested type inherited from android.widget.FrameLayout` |
| `reason` | why it stays unresolved, from what is left after the candidates above: `ambiguous` (there are `candidates`), `outside` (no candidates, and only something outside the sources explains it: a wildcard, project-wide or default import, a nested type of an external supertype), `unexplained` (anything else: a nested type the project type lacks, a relative import that reaches no class, no hint at all) |
| `location` | `{file, line}` |

`extract.py` prints the count by reason: `931 unresolved (72 ambiguous, 859 outside the
sources)`. Files written before `reason` existed lack it; readers treat it as absent.

## Diagnostic

`{file, line, message, end_line?}` — one per syntax-error span: every ERROR/MISSING region
tree-sitter found, merged when adjacent; `end_line` is present when the span covers more
than one line. Declarations inside a span may be missing or partial; the rest of the file
is reliable. At most 20 spans per file; a 21st diagnostic counts the remainder.
