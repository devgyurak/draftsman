#include "app/types.h"
namespace app {
struct User {
  int f() { Local l; return sizeof(l); }
  int g() { Money m; Money n = Money(3); return sizeof(m) + sizeof(n); }
};
}
