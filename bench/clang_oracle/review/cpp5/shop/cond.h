#pragma once
#include "g.h"
#define EARLY 1
#define API
namespace shop {
#if defined(FEAT_A) && \
    defined(FEAT_B)
struct Gate2 {};
#endif
#ifdef LATE
struct Opt2 {};
#endif
#ifdef EARLY
int Rate(int);
#endif
API int Fee(int);
}
