#include "t4/types.h"
namespace t4 {
struct User : Base {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
}
