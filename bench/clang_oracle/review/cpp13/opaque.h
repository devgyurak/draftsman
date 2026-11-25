#pragma once
#include "lib/lib.h"
namespace op {
struct Path {};
#ifndef DOC
struct PB { struct Handle { int fd; }; };
#endif
struct F : PB, lib::Other {
  struct Own {};
  Handle h_;
  Own o_;
  Mode m_;
  Path p_;
  ::Handle g_;
  lib::Base b_;
  struct In {
    Handle h_;
    Own o_;
  };
  int f() { Handle x; Own y; Mode z; Path w; return sizeof(x) + sizeof(y) + sizeof(z) + sizeof(w); }
};
struct Plain {
  Path p_;
  PB b_;
};
}
