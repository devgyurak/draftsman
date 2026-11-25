#pragma once
#include "lib/lib.h"
namespace la = lib;
namespace chain {
struct A : la::Base {};
struct B2 : A {
  Inner i_;
  Base* b_;
  int f() { Inner x; Base* y = nullptr; return sizeof(x) + sizeof(y); }
};
typedef lib::Base LB;
struct D : LB {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
struct E2 : la::EBase {
  Kind k_;
  int f() { return sizeof(Paid) + sizeof(Kind); }
};
template <class T> struct Crtp { struct Inner {}; };
struct N : Crtp<N> {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
}
