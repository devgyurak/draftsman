#include "g.h"
namespace app {
inline int Foo::run() { Helper h; return sizeof(h); }
template <class T> int Foo::go(T) { Helper h; return sizeof(h); }
}
