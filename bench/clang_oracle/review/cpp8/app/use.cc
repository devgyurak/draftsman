#include "app/mid.h"
namespace app {
struct U {
  int a() { Money m; Thing t; Box<int> b; return sizeof(m) + sizeof(t) + sizeof(b); }
  int b() { return Make(1) + sizeof(Limit); }
  int c() { Impl i; return sizeof(i); }
  int d() {
    enum Kind { Paid, Unpaid };
    enum { Open, Closed } state = Open;
    return sizeof(Paid) + sizeof(Open) + state;
  }
  int e() {
    enum class Tone { Stamp };
    return sizeof(Stamp);
  }
};
namespace in {
struct W {
  int a() { Money m; return sizeof(m); }
};
}
}
namespace shop {
struct S {
  int a() { Money m = Money(1); return sizeof(m); }
};
}
namespace other {
struct O {
  int a() { Money m; Impl i; return sizeof(m) + sizeof(i); }
};
}
namespace far {
struct F {
  int a() { Coin c; return sizeof(c); }
};
}
