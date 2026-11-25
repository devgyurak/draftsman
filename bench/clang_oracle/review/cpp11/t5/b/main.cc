#include "g.h"
#include "t5/b/gen.h"
using namespace gen;
struct M : Root {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
