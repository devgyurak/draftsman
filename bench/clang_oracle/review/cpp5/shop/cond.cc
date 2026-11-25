#define FEAT_A 1
#define FEAT_C 1
#include "shop/cond.h"
#define LATE 1
namespace shop {
struct C {
#if defined(FEAT_A) && \
    defined(FEAT_C)
  int a() { Gate2 g; return sizeof(g); }
#endif
#ifdef LATE
  int b() { Opt2 o; return sizeof(o); }
#endif
  int c() { return Rate(1) + Fee(2); }
};
}
