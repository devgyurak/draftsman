#include "g.h"
namespace a { namespace inner { struct D { struct Sub {}; }; struct E {}; } }
namespace fs = a::inner;
namespace gs = a::inner;
namespace shop {
struct X {
  int f() { fs::D d; ::fs::D e; fs::D::Sub s; return sizeof(d) + sizeof(e) + sizeof(s); }
  int g() { gs::E e; return sizeof(e); }
};
}
