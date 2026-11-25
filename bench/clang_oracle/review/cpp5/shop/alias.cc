#include "g.h"
namespace a { namespace inner { struct D {}; struct E {}; } }
namespace fs = a::inner;
namespace gs = a::inner;
namespace shop {
namespace fs { struct D {}; }
namespace al = a::inner;
struct X {
  struct gs { struct D {}; };
  int f() { fs::D d; return sizeof(d); }
  int g() { gs::D d; return sizeof(d); }
};
struct Y {
  int f() { gs::E e; return sizeof(e); }
  int g() { al::E e; return sizeof(e); }
};
}
