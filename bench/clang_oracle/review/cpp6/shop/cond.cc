#include "shop/cond.h"
namespace shop {
#ifdef EARLY
int Toll(int);
#endif
struct C {
  int c() { return Toll(2); }
};
}
