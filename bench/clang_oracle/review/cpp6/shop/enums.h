#pragma once
#include "g.h"
namespace shop {
enum Lvl { Level, Mark };
struct Outer {
  enum { Tag };
  struct In {
    struct Tag {};
    int f() { return sizeof(Tag); }
  };
  struct Mark {};
  int g() { return sizeof(Mark); }
  int h() { return sizeof(Level); }
};
namespace deep {
struct Level {};
struct Z {
  int f() { return sizeof(Level) + sizeof(Mark); }
};
}
}
namespace app {
enum Sev { Debug, Error };
namespace net {
struct Error { Error(const char*) {} };
struct Conn {
  void f() { throw Error("x"); }
  Error make() { return Error("y"); }
};
}
struct Log {
  int f() { return sizeof(Error); }
};
}
