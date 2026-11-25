#include "shop/top.h"
namespace shop2 {
struct T {
  int a() { Money m; Stamp s; return sizeof(m) + sizeof(s); }
};
}
namespace shop3 {
struct T {
  int a() { Money m; Stamp s; return sizeof(m) + sizeof(s); }
};
}
