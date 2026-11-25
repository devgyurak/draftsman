#include "g.h"
#include "app/fwd.h"
namespace app {
struct F {
  int f(Box<int>* b, Mode m) { Box<int>* c = b; Mode n = m; return c != nullptr && n == m; }
};
inline int Pim::f() { Impl* q = p; return q != nullptr; }
}
