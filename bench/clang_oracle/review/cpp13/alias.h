#pragma once
#include <vector>
#include "lib/lib.h"
namespace al {
using LB = lib::Base;
typedef LB LB2;
struct D1 : LB2 {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
template <class T> using Vec = lib::Holder<T>;
struct D2 : Vec<int> {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
template <class T> struct D3 : Vec<T> {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
typedef std::vector<int> IntVec;
struct D4 : IntVec {
  value_type v_;
  value_type get(const value_type& x);
  int f() { value_type y = 0; return y; }
};
struct O {
  typedef lib::Base B;
  struct D5 : B {
    Inner i_;
  };
};
typedef lib::Holder<int> HI;
struct D6 : HI {
  Inner i_;
};
}
