#include "g.h"
#include "util.h"                 // app/util.h, this directory's: one/util.h is not included
#include <app/chain1.h>
#include "../sub/deep.h"
namespace app {
struct Fwd;                       // declared here, defined in app/fwd.h, which is not included
struct K {
  int f() {
    Util u{1};                    // ::Util: app::Util (one/util.h) is not included
    Other o{2};                   // app::Other
    Chained c{3};                 // app::Chained, through chain1.h
    Shallow s{4};                 // app::Shallow
    Deep d{5};                    // ::Deep: one/sub/deep.h is not included
    return u.g + o.o + c.c + s.s + d.g;
  }
  int g(Fwd* p) {
    Fwd* q = p;                   // app::Fwd, the declaration above (not ::Fwd)
    return q != nullptr;
  }
  int h() { Late l{1}; return l.g; }   // ::Late: app/late.h comes below
};
}
#include "app/late.h"
#include "app/impl.h"
namespace app {
struct K2 { int h() { Late l{1}; return l.a; } };   // app::Late now
}
