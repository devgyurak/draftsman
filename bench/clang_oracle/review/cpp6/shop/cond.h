#pragma once
#include "g.h"
#define EARLY 1
namespace shop {
struct K {
#ifdef EARLY
  static int Rate(int);
#endif
  int f() { return Rate(1); }
};
}
