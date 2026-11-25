#pragma once
#include "g.h"
namespace lib {
struct Base { struct Inner {}; };
struct Other { struct Mode {}; };
template <class T> struct Holder { struct Inner {}; };
}
