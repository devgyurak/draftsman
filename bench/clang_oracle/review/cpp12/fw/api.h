#pragma once
#include "g.h"
namespace fw {
class Impl;
struct Api {
  Impl* p_;
  Impl* get();
  int f() { Impl* x = nullptr; return sizeof(x); }
};
}
namespace n {
struct Sel {};
struct U {
  Sel* s_;
  ::Sel* g_;
};
}
