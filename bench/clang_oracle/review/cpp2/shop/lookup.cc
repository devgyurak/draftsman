#include "shop/model.h"

namespace fs = a::inner;

namespace shop {

namespace { struct Hidden { int h; int run(); int tag(); }; }

int Hidden::run() {
  Money m{1};
  return m.v + h;
}

int Order::names() const {
  {
    using namespace a::inner;
    D d{1};                 // shop::D: a::inner's names count as the global namespace's here, shop's own is nearer
    (void)d.s;
  }
  {
    using a::C;
    C c{1};                 // a::C: a using-declaration in the block hides shop::C
    (void)c.a;
  }
  {
    namespace al = a::inner;
    al::B b{1};             // a::inner::B
    fs::D d{2};             // a::inner::D
    (void)b.i, (void)d.i;
  }
  {
    using namespace lib;
    Sib s{1};               // shop::Sib
    Base::In in{2};         // lib::Base::In (Base is the class's base, too)
    (void)s.s, (void)in.n;
  }
  auto f = [](Money Tag) { Helper h{Tag.v}; return h.s; };   // Tag: the lambda's parameter
  struct Local { Money m; int get() { Sib s{m.v}; return s.s; } };
  struct Helper { int local; };
  Helper lh{5};             // the local struct
  return f(Money(1)) + Local{Money(2)}.get() + lh.local;
}

int Hidden::tag() {
  struct Tag {};            // a local type
  Tag t;
  (void)t;
  try { throw Money(1); } catch (const Money& Sib) { return Sib.v; }
}

}  // namespace shop

namespace other {
using namespace shop;
struct Sib { int o; };
struct User {
  int run() { Money m{1}; D d{2}; Sib s{3}; return m.v + d.s + s.o; }   // shop::Money, shop::D through the directive; other::Sib, its own
};
}
