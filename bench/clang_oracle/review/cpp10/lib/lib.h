#pragma once
#include "g.h"
namespace lib {
struct Money {};
struct Base { struct Inner {}; Base() {} explicit Base(int) {} };
struct Item {};
template <class T> struct Box {};
}
