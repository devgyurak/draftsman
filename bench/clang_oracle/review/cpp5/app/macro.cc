#include "g.h"
#define APP_UTIL "app/util.h"
#include APP_UTIL
namespace app {
struct M {
  int f() { Util u; return sizeof(u); }
};
}
