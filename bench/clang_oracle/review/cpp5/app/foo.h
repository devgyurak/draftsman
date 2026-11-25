#pragma once
namespace app {
struct Helper {};
struct Foo { int run(); template <class T> int go(T); };
}
#include "app/foo_inl.h"
