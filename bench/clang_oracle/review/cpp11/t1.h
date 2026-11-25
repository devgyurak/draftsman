#pragma once
#include "lib/lib.h"
namespace la = lib;
namespace t1 {
struct C : la::Base {
  Inner i_;
  Deep d_;
  int f() { Inner x; return sizeof(x); }
};
}
