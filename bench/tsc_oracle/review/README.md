# Review sets: TypeScript sources written by hand

Each directory is a set of sources a review wrote to put the extractor and tsc side by side
on forms the end-to-end repositories lack. `oracle.py review` compiles each (its `.ts` and
`.tsx` files together, the compiler's default options, strict) and compares the body
relations the extractor draws from it, and its declared relations (issues #7, #9), with
tsc's answers (bench/review_sets.py); it fails on a mismatch not listed below as a known
limit, and on fewer body names drawn or declared names agreed than the table says.

| Set | Body names drawn | Declared names agreed | What it holds |
|---|---|---|---|
| `ts1` | 2 | 39 | types the type parser read no name from (#9, cases 29-32): a union with a leading `\|`, intersections, object type literals, function types with optional parameters, indexed access, conditional types, aliases of these, type predicates, destructured parameters, supertypes that are aliases of several types, of an object type, of `Omit<...> & {...}`. Beside each a project type named like what is no type name there: property and parameter names, tuple labels, string and template literal types, an alias's type parameters, `infer U`, a mapped type's key, an index signature's key, `typeof value` beside a type alias `value`, `keyof`, `this`, `import("./other").Foo` beside another module's `Foo`, a constructor type, a default type argument. Before the fix: 8 agreed, 1 mismatch (an alias's own `T` drawn as the class `T`), 1 drawn where tsc has no name (`typeof value`), 30 misses |

Known limits (mismatches that stay):

- none

Known limits of declared relations (mismatches that stay):

- none
