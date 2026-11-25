#pragma once
#include "g.h"
namespace plat {
#ifdef _WIN32
struct PlatBase { struct Handle { void* h; }; };
#else
struct PlatBase { struct Handle { int fd; }; };
#endif
struct File : PlatBase {
  Handle h_;
  Handle open(const Handle& x);
  int f() { Handle x; return sizeof(x); }
};
struct Uses {
  PlatBase b_;
};
}
