#pragma once
#include "lib/lib.h"
namespace shop {
struct Money { Money() {} Money(int) {} };
struct Outer {
  Outer() {}
  struct In {
    Outer* parent_;
    Outer* owner(Outer& o);
    Money m_;
  };
  In in_;
  ::Money g_;
  lib::Money l_;
};
struct D : lib::Base {
  Inner i_;
  Base* b_;
  D(const Base& b);
  Inner make(Inner x);
};
struct HasInner { struct Inner {}; struct Tag {}; };
struct Wrap : HasInner {
  struct E : Inner {
    Tag t_;
  };
  struct F : Tag {};
};
template <class Money> struct Gen {
  Money m_;
  void f(const Money& x);
  Item i_;
};
struct T2 {
  typedef Money Cash;
  Cash c_;
  using Ptr = Outer*;
  Ptr p_;
  Cash pay(Ptr p);
};
struct U : lib::Base {
  using lib::Base::Inner;
  Inner i_;
};
}
