// Item 13: does `using namespace`, `using a::B;`, a namespace alias or argument-dependent
// lookup change what a type's name in a body is? The comment after each line says what
// C++ says; type-uses -all records what Clang says.
struct B { B(int = 0) {} };                       // ::B
namespace a {
  struct B { B(int = 0) {} };                     // a::B
  struct C {};
  namespace inner { struct B {}; struct D {}; }
  struct S {};
  void Make(S) {}
  void Tag(S) {}
}
namespace n {
  struct B {};                                    // n::B
  using namespace a;
  void h1() { B b; }                              // n::B: n's own B; a's names count as declared in :: here
  void h2() { C c; }                              // a::C through the using-directive
}
void g1() { using namespace a; C c; ::B b; }      // a::C, ::B
void g2() { using a::C; C c; }                    // a::C through a using-declaration
void g3() { using a::B; B b; }                    // a::B: the using-declaration hides ::B in this block
namespace fs = a::inner;
void g4() { fs::B b; fs::D d; }                   // a::inner::B, a::inner::D
struct Make { Make() {} Make(a::S) {} };          // ::Make
void g5() { a::S s; auto m = Make(s); }           // ::Make: ordinary lookup finds a type, so no ADL
void g5b() { a::S s; { Make(s); } }               // ::Make, but a declaration: a variable s of type Make (vexing parse)
namespace m { struct Tag { Tag(a::S) {} }; }
void g6() { a::S s; Tag(s); }                     // a::Tag (function) by ADL: m::Tag is not visible
namespace p {
  using a::inner::D;
  void h3() { D d; }                              // a::inner::D
}
namespace q {
  struct B {};
  void h4() { using namespace a::inner; B b; }    // q::B: a::inner's names count as declared in ::, q's own B is nearer
}
void g7() { using namespace a; using namespace a::inner; D d; }  // a::inner::D
