#pragma once
#include "g.h"
namespace t2 {
struct Base {};
struct G : ::Base {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
}
