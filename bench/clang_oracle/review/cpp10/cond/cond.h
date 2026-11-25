#pragma once
#include "g.h"
namespace cond {
#ifdef WIDE
struct Sel { long v; };
struct UsesSel {
  Sel s_;
};
#else
struct Narrow { int v; };
struct UsesNarrow {
  Narrow n_;
  Tag t_;
};
#endif
struct Out {
  Narrow n_;
};
}
