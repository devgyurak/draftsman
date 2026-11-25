# Review sets: C++ sources written by hand

Each directory is a set of sources a review wrote to put the extractor and Clang side by
side on forms the end-to-end repositories lack. `oracle.py review` compiles each (every
`.cc` file a translation unit, C++17, the directory as include path, and each header no
unit includes a unit of its own) and compares the body relations the extractor draws from
it with Clang's answers; it fails on a mismatch not listed below as a known limit, and on
fewer names drawn than the table says. The sets compile without errors: a wrong candidate
has a real rival, so that a wrong draw is a mismatch.

| Set | Names drawn | What it holds |
|---|---|---|
| `cpp1` | 0 | the pre-check's probe of name lookup: `using namespace` (a namespace's own name is nearer), a block's `using a::B;`, a namespace alias, a call `Make(s)` that is the type (no argument-dependent lookup past a type) and `Tag(s)` that is a function of an argument's namespace, a vexing parse. Every body in it is a free function's, which draws nothing: it checks the key, not the extractor |
| `cpp2` | 32 | the first review of the extractor: members defined out of the class (the class's namespace before the one around the definition, not a base's namespace), a base's member type and field, a class's typedef and field, an elaborated `struct Channel`, a typedef-named definition `Ord::look()`, an enumerator of the class (`sizeof(Paid)`), a local variable declared after a use, a dependent base (`Vec : TBase<T>`: its member type and field are not looked into) beside `Fixed : TBase<int>`, template parameters named like types, an anonymous namespace's member defined out of the class, block-scope `using namespace`, `using a::C;` and namespace aliases, a file-scope namespace alias, a lambda's parameter, local classes. No mismatch |
| `cpp3` | 10 | includes: another directory's type of the name (`one/util.h`, not included: `::Util`), a chain of includes, `"../sub/deep.h"`, a declaration `struct Fwd;` of a type whose file is not included (the name is that type), a header with no include of its own, an include below a use |
| `cpp4` | 47 | macros (a string `STR(Money::Zero)`, `ID(...)`, `DECL(Money, d)`, `NEWOF(Money)`, `SIZE(Money)`), the vexing parse with a field, an enumerator of the namespace and a type (`Lock l2(Paid)`, `Lock l3(Money)`), `sizeof` and `typeid` of an enumerator, a function of a type's name beside the global type, aliases (`FeedPtr`, `Cash`, `Chan` through an alias template, `Channel::Ptr`), an inline namespace, `::Tag`, types of `#if` branches taken and not taken, casts, a lambda, a pointer to member, `decltype`, `static_assert`, `alignof`, `offsetof`, `noexcept`, a friend, default arguments and member initializers |
| `cpp5` | 23 | the second review, each rule with a rival type: bases of a base (`Leaf : ViaPtr<int>`, `ViaPtr<T> : TBase<T*>`) and dependent ones of several forms, namespace aliases beside a namespace and a class of the name, a header included at the end of the one that defines its types, template and enum forward declarations, a class's forward declaration, an include a macro makes, an `#if` condition over two lines, a macro defined after the include, a function of an `#if` branch, enumerators of a class, a base, a namespace and the global one beside types |
| `cpp6` | 19 | the second review's rules again, with rivals of other forms: bases of a dependent base's own base (`Mid<T> : TBase<T>`), dependent bases of a class around, a member template, a rooted alias `::fs::D` and `fs::D::Sub`, forward declarations with an export macro and a default template argument, a friend declaration, a function of an `#if` branch beside a static method, enumerators of a class around, of an enclosing namespace and of a nested one beside types and a thrown `Error("x")` |
| `cpp7` | 15 | a namespace's using declaration (`namespace app { using lib::Money; }`) in the header and in files including it, an alias of the namespace (`using Thing = lib::Item;`), `typedef struct Node0 {...} Node0;`, an enum in a member's body, an anonymous namespace's type in a `.cc` file beside a global one, `try`/`catch` and a range `for`, a type of the `#if` branch not taken beside the global one |

Known limits (mismatches that stay):

- `cpp3/app/use.cc:20:13` a name used above the `#include` of its file in the same file
  (`app/late.h` comes below): the extractor reads a file's includes as a whole
- `cpp3/deep/use.cc:7:5` an include path matched by its suffix: `"sub/deep.h"` from
  `deep/` is taken for `one/sub/deep.h` too (the compiler's include path, `-I/src`, makes
  it `sub/deep.h` only)
- `cpp4/shop/a.cc:26:25` a qualified name in a macro's argument the macro makes a string
  (`STR(Money::Zero)`): the parser sees an expression
- `cpp4/shop/a.cc:27:31` the same (`STR(shop::Money)`)
- `cpp5/shop/cond.cc:12:13` an `#ifdef` of a macro the file defines after its include
  (`LATE`): the header's branch of the same condition is not compiled, but its condition
  reads the same

Names Clang finds that are not drawn (misses, no failure):

- `cpp2/shop/order.cc:13:10` an elaborated name (`struct Channel c`)
- `cpp2/shop/order.cc:29:3`, `29:13` a member defined out of a class named by a typedef
  (`int Ord::look()`)
- `cpp2/shop/order.cc:38:3`, `cpp2/shop/lookup.cc:37:28` a local variable or class hides
  its name in the whole member, also above its declaration
- `cpp2/shop/lookup.cc:27:9` a namespace alias of a block (`namespace al = a::inner;`); one
  of the file's scope is read (`fs::D`)
- `cpp2/shop/lookup.cc:57:27` a `using namespace` in a function is taken for the file's,
  so `D` has two candidates there
- `cpp3/app/impl.h:4:15` a header with no include of its own, used by a file that includes
  what it needs first
- `cpp4/shop/a.cc:29:10`, `30:22`, `31:36` a macro's argument that is an identifier alone
  (`DECL(Money, d)`, `NEWOF(Money)`, `SIZE(Money)`): the parser sees no type there
- `cpp4/shop/a.cc:56:5` a type of an `#if` branch used outside every branch of its
  condition (`Gate`, taken): another type of the name may be meant
- `cpp4/shop/a.cc:57:5` the same, of a branch not taken (`Opt`, where `::Opt` is meant):
  the extractor does not know which branches a build takes; also `cpp5/shop/cond.cc:9:13`
  (`Gate2` in a branch whose condition differs in its second line), and
  `cpp7/app/cond.cc:7:13` (`Sel` in the `#ifdef WIDE` branch, used in the `#else` one,
  where `::Sel` is meant)
- `cpp6/shop/enums.h:9:29` an enumerator of a class around (`Outer`'s `enum { Tag }`) is
  taken to hide a nested class's member type (`Outer::In::Tag`, nearer)
- `cpp5/app/foo_inl.h:3:25`, `4:37` a type a file including the body's file defines
  (`foo.h` includes `foo_inl.h` at its end): which one is meant is not known
- `cpp5/app/macro.cc:6:13` the same in a file with an include a macro makes
  (`#include APP_UTIL`)
- `cpp5/app/fwduse.cc:7:23` a class's forward declaration of a nested type (`struct Pim {
  struct Impl; }`, defined in a file not included)
- `cpp5/shop/alias.cc:15:17` a namespace alias of a namespace (`namespace al = a::inner;`
  inside `shop`); one of the file's scope is read
