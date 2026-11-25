#include "app/cond.h"
namespace app {
struct C {
#ifdef WIDE
  int a() { return 0; }
#else
  int b() { Sel s; Narrow n; return sizeof(s) + sizeof(n); }
#endif
};
}
