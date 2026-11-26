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
| `ts2` | 0 | 18 | a supertype's type arguments (#9, case 24): a class's `extends Array<Node>` (whose arguments tree-sitter keeps apart from the name) beside another module's `Node`, a type parameter `T` beside a class `T`, an interface's `extends Map<string, Item[]>`, `implements Cmp<Sub>` naming the class itself, an object type over several lines; project aliases named like containers (`Provider`, `Vector`, `Iterator`, case 25). Before the fix: 8 agreed, 9 misses |
| `ts3` | 1 | 79 | a review's probe of the TypeScript parser (#9): comments and strings inside types, quoted property names, accessors, constructor parameter properties, overloads, tuple rest elements, mixin supertypes, `typeof`, each beside a project type of the name. At f5e007a: 79 agreed, no mismatch |

Known limits (mismatches that stay):

- none

Known limits of declared relations (mismatches that stay):

- none
