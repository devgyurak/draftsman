#include "g.h"
#include "app/fwd.h"
namespace app {
struct F {
  int f(Fwd2* b, Fwd3<int>* c) { Fwd2* d = b; Fwd3<int>* e = c; return d != nullptr && e != nullptr; }
};
inline int Friendly::f() { Util u; return sizeof(u); }
}
