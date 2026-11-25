#pragma once
#include "g.h"
namespace app {
#ifdef WIDE
struct Sel {};
#else
struct Narrow {};
#endif
}
