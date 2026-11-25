#pragma once
#include "lib/lib.h"
namespace t3 {
using lib::Base;
namespace in {
struct Base {};
struct W : Base {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
}
}
