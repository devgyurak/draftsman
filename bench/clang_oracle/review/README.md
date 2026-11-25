# Review sets: C++ sources written by hand

Each directory is a set of sources a review wrote to put the extractor and Clang side by
side on forms the end-to-end repositories lack. `oracle.py review` compiles each (every
`.cc` file a translation unit, C++17, the directory as include path, and each header no
unit includes a unit of its own) and compares the body relations the extractor draws from
it, and its declared relations (issue #7), with Clang's answers; it fails on a mismatch
not listed below as a known limit, and on fewer body names drawn than the table says. The sets compile without errors: a wrong candidate
has a real rival, so that a wrong draw is a mismatch.

| Set | Body names drawn | Declared names agreed | What it holds |
|---|---|---|---|
| `cpp1` | 0 | 2 | the pre-check's probe of name lookup: `using namespace` (a namespace's own name is nearer), a block's `using a::B;`, a namespace alias, a call `Make(s)` that is the type (no argument-dependent lookup past a type) and `Tag(s)` that is a function of an argument's namespace, a vexing parse. Every body in it is a free function's, which draws nothing: it checks the key, not the extractor |
| `cpp2` | 32 | 6 | the first review of the extractor: members defined out of the class (the class's namespace before the one around the definition, not a base's namespace), a base's member type and field, a class's typedef and field, an elaborated `struct Channel`, a typedef-named definition `Ord::look()`, an enumerator of the class (`sizeof(Paid)`), a local variable declared after a use, a dependent base (`Vec : TBase<T>`: its member type and field are not looked into) beside `Fixed : TBase<int>`, template parameters named like types, an anonymous namespace's member defined out of the class, block-scope `using namespace`, `using a::C;` and namespace aliases, a file-scope namespace alias, a lambda's parameter, local classes. No mismatch |
| `cpp3` | 10 | 1 | includes: another directory's type of the name (`one/util.h`, not included: `::Util`), a chain of includes, `"../sub/deep.h"`, a declaration `struct Fwd;` of a type whose file is not included (the name is that type), a header with no include of its own, an include below a use |
| `cpp4` | 47 | 4 | macros (a string `STR(Money::Zero)`, `ID(...)`, `DECL(Money, d)`, `NEWOF(Money)`, `SIZE(Money)`), the vexing parse with a field, an enumerator of the namespace and a type (`Lock l2(Paid)`, `Lock l3(Money)`), `sizeof` and `typeid` of an enumerator, a function of a type's name beside the global type, aliases (`FeedPtr`, `Cash`, `Chan` through an alias template, `Channel::Ptr`), an inline namespace, `::Tag`, types of `#if` branches taken and not taken, casts, a lambda, a pointer to member, `decltype`, `static_assert`, `alignof`, `offsetof`, `noexcept`, a friend, default arguments and member initializers |
| `cpp5` | 23 | 16 | the second review, each rule with a rival type: bases of a base (`Leaf : ViaPtr<int>`, `ViaPtr<T> : TBase<T*>`) and dependent ones of several forms, namespace aliases beside a namespace and a class of the name, a header included at the end of the one that defines its types, template and enum forward declarations, a class's forward declaration, an include a macro makes, an `#if` condition over two lines, a macro defined after the include, a function of an `#if` branch, enumerators of a class, a base, a namespace and the global one beside types |
| `cpp6` | 19 | 11 | the second review's rules again, with rivals of other forms: bases of a dependent base's own base (`Mid<T> : TBase<T>`), dependent bases of a class around, a member template, a rooted alias `::fs::D` and `fs::D::Sub`, forward declarations with an export macro and a default template argument, a friend declaration, a function of an `#if` branch beside a static method, enumerators of a class around, of an enclosing namespace and of a nested one beside types and a thrown `Error("x")` |
| `cpp7` | 15 | 4 | a namespace's using declaration (`namespace app { using lib::Money; }`) in the header and in files including it, an alias of the namespace (`using Thing = lib::Item;`), `typedef struct Node0 {...} Node0;`, an enum in a member's body, an anonymous namespace's type in a `.cc` file beside a global one, `try`/`catch` and a range `for`, a type of the `#if` branch not taken beside the global one |
| `cpp8` | 14 | 0 | using declarations through two includes, of a template, an alias, a function and a variable, beside a nearer namespace's type of the name, in another namespace and in a file not including them, of the file's scope, with a file not included declaring a type of the id; a member's named, unnamed and scoped enums |
| `cpp9` | 0 | 32 | declared relations (issue #7), each form beside a rival type: an alias template's own parameter (`Hash`), a qualified name whose head is the class's own alias (`Mutex::ScopedLock`), another program's type of the name (`a/util.h`'s `Utility` beside `gen::Utility` through `using namespace`), a type of an `#if` branch not taken beside the system's `timeval`, a dependent base (`Vec : TBase<T>`) beside `Fixed : TBase<int>`, `::D`, a namespace alias of the file beside a nearer namespace of the name, a header's using declaration where it is included, a nearer namespace's type beside an outer one's using declaration, an alias of `std::vector<Item>::const_iterator`, `typename std::pair<K, Var>`, a class's own nested type it only declares. No body names: it checks declared relations only (32 names of the key, no mismatch; the extractor of 0.9.0 has 20 mismatches and 3 misses on it) |
| `cpp10` | 1 | 71 | declared relations, a review's (77 names of the key; 12 mismatches and 3 misses before C++ declarations were looked up as bodies are): a header's using declarations of a type and of a base where it is included, and in another namespace, `#if` branches (a type of the branch not taken beside the global one, a type used outside its branch), a class's own nested type and a namespace's type it only declares, a header with no include of its own naming a type its includer sees, a namespace alias `la::Money`, `la::Box<Item>`, `la::Base::Inner`, a nearer namespace's type before a using declaration, anonymous namespaces' types of two `.cc` files beside a global one, a method of the type's name (`int Thing() const;`), a parameter of the type's name (`Item Item`), the class's own type in a nested class, `::Money`, a base's member type, a template parameter `Money`, member aliases, a base's using declaration, standard templates' arguments |
| `cpp11` | 5 | 11 | the base a relation is drawn to is the one names are looked up in (Resolver.supertypes), in declarations and bodies: a base through a namespace alias (`la::Base`), `::Base` beside a namespace's own `Base`, a nearer namespace's `Base` before a using declaration of an outer one, a header's using declaration of the base where it is included, another program's type of the base's name (`Root`, not included) beside `gen::Root` through `using namespace` |
| `cpp12` | 5 | 20 | a review's third round: a base of the `#if` branch not taken and of every branch of an `#if` chain (`PlatBase`, `#ifdef _WIN32 ... #else`), whose member type `Handle` comes before the global one; a base through a base (`B2 : A : la::Base`), a base written as a typedef (`D : LB`), an enum of a base (`Kind`, `Paid`), a base `Crtp<N>` naming the class; a forward declaration beside definitions in both branches (`fw::Impl`), `::Sel` declared beside a definition no unit compiles (counted apart as not compiled); a header with no include of its own whose base its includer brings in (`inc/d.h`). Declared: 21 names of the key, no mismatch |
| `cpp13` | 5 | 24 | a review's fourth round: bases written as an alias of an alias, an alias template, a class's own typedef and an alias of an outside class (`typedef std::vector<int> IntVec;`, std's `value_type` beside a global one), a dependent base through an alias template; `#if` chains of three branches, nested chains, one whose `#else` is an `#error` and one with a forward declaration in a branch; a base of an `#ifndef` branch whose members are not known, beside another base, the class's own type and a nested class. Declared: 32 names of the key, no mismatch |
| `cpp14` | 0 | 14 | a base's template arguments (#9, case 24): `std::vector<Node>` beside another namespace's `Node`, a template parameter `T` beside a struct `T`, nested arguments (`std::map<int, std::vector<Item>>`, `Base<std::vector<T>>`); member aliases named like containers (`typedef std::vector<Item> Vector;`, `using Map = ...`, case 25). Before the fix: 6 agreed, 6 misses |

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
- `cpp8/app/use.cc:6:13` a using declaration relative to its namespace (`namespace app {
  using detail::Impl; }`, `app::detail::Impl`)
- `cpp8/app/use.cc:35:13` a header's `using namespace` (`namespace far { using namespace
  lib; }`) in a file that includes it (`Coin` is `lib::Coin`)
- `cpp12/fw/api.h:8:13` a type every branch of an `#if` chain defines and the file
  declares outside them (`class Impl;`): a body's `#if` rule stands (declared relations
  draw it)
- `cpp12/inc/d.h:4:13` a member type of a base the header sees only through its includer
  (`inc/b.h`, included by `use.cc` before `d.h`): what the file sees is not known
- `cpp12/plat.h:12:13` a member type of a base every branch of an `#if` chain declares
  (`PlatBase::Handle`): a body's `#if` rule stands (declared relations draw it)
- `cpp13/opaque.h:20:13`, `:20:38` names in the body of a class whose base is not known
  (`PB`, under `#ifndef DOC`): `Handle` and the namespace's `Path` may be its members

Declared names Clang finds that are not drawn (misses, no failure):

- `cpp2/shop/model.h:37:12` a conversion operator's type (`operator Money() const;`): not
  read (#9)
- `cpp10/cond/cond.h:17:3` a type of an `#if` branch used outside it (`Narrow`, declared in
  the `#else` of `#ifdef WIDE`): unresolved, as in a body (#18's rule; no declaration of
  the id stands outside the branches)
- `cpp10/shop/hide.h:11:3` a type named like a method the class declares below
  (`Thing t_;` beside `int Thing() const;`): unresolved, as in a body, where a name of the
  class's members may be the method
- `cpp13/chain.h:23:3` a type of an `#if` chain whose `#else` is an `#error`: every branch a
  build compiles declares it, but the chain is not read as every branch (#9)
- `cpp13/chain.h:43:3` a type of a chain one branch of which only declares it
  (`struct Fwd;`) (#9)
- `cpp13/opaque.h:8:12`, `:24:3` a base declared only under `#ifndef DOC`, used outside it
  (#18's rule), and so, a base whose members are not known: `:10:3`, `:13:3`, `:17:5` names
  found past it, and `:15:8` `lib::Base`, a qualified name it hides too (#9)

Known limits of declared relations (mismatches that stay):

- none
